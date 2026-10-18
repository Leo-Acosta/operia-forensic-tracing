"""Explicit case access. Roles remain an independent upper bound."""
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import Integer, String, ForeignKey, DateTime, Text, select, func, event, text, Index, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column, Session
from operia.core.database import Base, get_db
from operia.identity.dependencies import require_user
from operia.shared.time import utcnow


CAPABILITIES = ("read", "write", "evidence", "analysis", "review", "participants", "reports", "approve", "export")


class CaseAccessEvent(Base):
    __tablename__ = "case_access_events"
    __table_args__ = (
        Index("ix_case_access_lookup", "organization_id", "user_id", "permission", "case_id", "id"),
        CheckConstraint("access IN ('granted', 'revoked')", name="ck_case_access_state"),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), index=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("cases.id"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    actor_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    permission: Mapped[str] = mapped_column(String(24), index=True)
    access: Mapped[str] = mapped_column(String(20))
    reason: Mapped[str] = mapped_column(Text)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


def allowed_ids(user, access="read"):
    from operia.cases.models import Case
    cases = select(Case.__table__.c.id).where(Case.__table__.c.organization_id == user.organization_id)
    if user.role == "admin":
        return cases
    if access != "read":
        cases = cases.where(Case.__table__.c.id.in_(allowed_ids(user)))
    table = CaseAccessEvent.__table__
    latest = select(func.max(table.c.id)).where(table.c.user_id == user.id,
        table.c.organization_id == user.organization_id, table.c.permission == access).group_by(table.c.case_id)
    return cases.where(Case.__table__.c.id.in_(select(table.c.case_id).where(table.c.id.in_(latest), table.c.access == "granted")))


def permitted(db, user, case_id, access="read"):
    from operia.cases.models import Case
    return bool(user.organization_id and db.execute(
        allowed_ids(user, access).where(Case.__table__.c.id == case_id)).first())


def require_case(db, user, case_id, access="read"):
    if not permitted(db, user, case_id, access):
        raise HTTPException(404, "Expediente no disponible")


def grant_creator(db, case, user):
    for capability in CAPABILITIES:
        db.add(CaseAccessEvent(organization_id=user.organization_id, case_id=case.id,
            user_id=user.id, actor_id=user.id, permission=capability,
            access="granted", reason="Creación del expediente"))
    db.flush()


def install_protection(connection):
    for index in CaseAccessEvent.__table__.indexes:
        index.create(connection, checkfirst=True)
    for operation in ("UPDATE", "DELETE"):
        connection.execute(text(f"CREATE TRIGGER IF NOT EXISTS case_access_no_{operation.lower()} BEFORE {operation} ON case_access_events BEGIN SELECT RAISE(ABORT, 'case_access_append_only'); END"))
    connection.execute(text("""CREATE TRIGGER IF NOT EXISTS case_access_valid_scope
        BEFORE INSERT ON case_access_events WHEN
        NEW.access NOT IN ('granted', 'revoked') OR
        NEW.permission NOT IN ('read', 'write', 'evidence', 'analysis', 'review', 'participants', 'reports', 'approve', 'export') OR
        NOT EXISTS (SELECT 1 FROM cases WHERE id=NEW.case_id AND organization_id=NEW.organization_id)
        OR NOT EXISTS (SELECT 1 FROM users WHERE id=NEW.user_id AND organization_id=NEW.organization_id)
        OR NOT EXISTS (SELECT 1 FROM users WHERE id=NEW.actor_id AND organization_id=NEW.organization_id)
        BEGIN SELECT RAISE(ABORT, 'case_access_invalid_scope'); END"""))


@event.listens_for(Session, "before_flush")
def immutable_access(db, context, instances):
    for item in list(db.dirty) + list(db.deleted):
        if isinstance(item, CaseAccessEvent) and (item in db.deleted or db.is_modified(item)):
            raise HTTPException(409, "Historial de permisos inmutable")


class AccessChange(BaseModel):
    model_config = ConfigDict(extra="forbid")
    user_id: int = Field(gt=0)
    access: str = Field(pattern="^(read|write|revoked)$")
    reason: str = Field(min_length=1, max_length=2000)
    permissions: list[str] | None = Field(default=None, max_length=len(CAPABILITIES))


router = APIRouter()


@router.get("/cases/{case_id}/access/me")
def effective(case_id: int, db: Session = Depends(get_db), user=Depends(require_user)):
    require_case(db, user, case_id)
    return {"case_id": case_id, "organization_admin": user.role == "admin",
            "capabilities": [cap for cap in CAPABILITIES if permitted(db, user, case_id, cap)],
            "access_management": user.role == "admin"}


@router.get("/cases/{case_id}/access")
def history(case_id: int, db: Session = Depends(get_db), user=Depends(require_user)):
    require_case(db, user, case_id)
    if user.role != "admin":
        raise HTTPException(403, "Administración de permisos requerida")
    return db.query(CaseAccessEvent).filter_by(case_id=case_id, organization_id=user.organization_id).order_by(CaseAccessEvent.id).all()


@router.post("/cases/{case_id}/access")
def change(case_id: int, payload: AccessChange, db: Session = Depends(get_db), user=Depends(require_user)):
    from operia.identity.models import User
    from operia.audit.service import write_audit
    from operia.forensic_jobs.storage_limits import begin_write
    if user.role != "admin":
        raise HTTPException(403, "Administración de permisos requerida")
    begin_write(db)
    require_case(db, user, case_id)
    target = db.get(User, payload.user_id)
    if not target or target.organization_id != user.organization_id or (target.status != "active" and payload.access != "revoked"):
        raise HTTPException(404, "Usuario no disponible")
    if target.role == "admin":
        raise HTTPException(409, "El administrador conserva acceso organizacional; cambiar su rol para retirarlo")
    if not payload.reason.strip():
        raise HTTPException(422, "Motivo requerido")
    permissions = payload.permissions if payload.permissions is not None else (list(CAPABILITIES) if payload.access in ("write", "revoked") else ["read"])
    if not permissions or any(permission not in CAPABILITIES for permission in permissions) or len(set(permissions)) != len(permissions):
        raise HTTPException(422, "Capacidades inválidas")
    if payload.access != "revoked" and "read" not in permissions:
        permissions = ["read", *permissions]
    items = []
    for permission in permissions:
        item = CaseAccessEvent(organization_id=user.organization_id, case_id=case_id,
            user_id=target.id, actor_id=user.id, permission=permission,
            access="revoked" if payload.access == "revoked" else "granted", reason=payload.reason.strip())
        db.add(item)
        items.append(item)
    write_audit(db, "revoke_case_access" if payload.access == "revoked" else "grant_case_access",
        "case-access", user, case_id=case_id, entity_type="user", entity_id=str(target.id), details=payload.access + " [" + ",".join(permissions) + "]: " + payload.reason.strip())
    db.commit()
    for item in items:
        db.refresh(item)
    return items


def request_capability(request, module, writing):
    path = request.url.path
    parts = set(path.split("/"))
    if parts & {"export", "download", "original"} or ("exports" in parts and "manifests" not in parts):
        return "export"
    if not writing:
        return "read"
    if "participant" in path:
        return "participants"
    if parts & {"findings", "hypotheses"}:
        return "analysis"
    if any(part in path for part in ("/approve", "/seal", "/finalize")):
        return "approve"
    if any(part in path for part in ("/reviews", "/review", "/rubrics")):
        return "review"
    if "/ai/" in path or path.endswith("/ai-enrich"):
        return "analysis"
    if module == "reports" or (module == "legal-report" and ("/reports" in path or "/report-sections/" in path or "/presentations" in path or "/presentation-slides/" in path)):
        return "reports"
    if module in ("ai", "ai-security", "mind", "geo", "geo-trace", "geo-proximity", "cybercrime", "static-lab"):
        return "analysis"
    if module == "mobile-forensics":
        return "analysis" if "/jobs" in path else "evidence"
    if module == "evidence" or any(part in path for part in ("/custody", "/evidence")):
        return "evidence"
    return "write"
