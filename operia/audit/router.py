from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from operia.audit.models import AuditLog
from operia.core.database import get_db
from operia.identity.dependencies import CurrentUser, require_permission

router = APIRouter()


def as_dict(obj) -> dict:
    return {column.name: getattr(obj, column.name) for column in obj.__table__.columns}


@router.get("/")
def status() -> dict[str, object]:
    return {
        "module": "Audit",
        "status": "canonical",
        "description": "Platform audit logs for cases, evidence, reports, exports, AI, and security evaluations.",
    }


@router.get("/logs")
def list_logs(
    case_id: int | None = None,
    module: str | None = None,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("audit:read")),
):
    query = db.query(AuditLog)
    if current_user and current_user.organization_id:
        query = query.filter(AuditLog.organization_id.in_([current_user.organization_id, None]))
    if case_id is not None:
        query = query.filter(AuditLog.case_id == case_id)
    if module:
        query = query.filter(AuditLog.module == module)
    return [as_dict(row) for row in query.order_by(AuditLog.created_at.desc()).limit(200).all()]


@router.post("/logs")
def create_log(
    payload: dict,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("audit:read")),
):
    row = AuditLog(**payload)
    row.organization_id = current_user.organization_id or payload.get("organization_id")
    row.user_id = current_user.id
    db.add(row)
    db.commit()
    db.refresh(row)
    return as_dict(row)
