from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from operia.audit.models import AuditLog
from operia.core.database import get_db
from operia.identity.dependencies import CurrentUser, get_optional_user, require_permission, require_user
from operia.identity.models import AuthToken, Membership, Organization, Role, User
from operia.identity.permissions import ROLE_PERMISSIONS
from operia.identity.security import create_access_token, hash_password, hash_token, verify_password

router = APIRouter()


def as_dict(obj) -> dict:
    data = {column.name: getattr(obj, column.name) for column in obj.__table__.columns}
    data.pop("password_hash", None)
    data.pop("token_hash", None)
    return data


def audit(db: Session, action: str, module: str, current_user: CurrentUser | None = None, details: str = "") -> None:
    db.add(
        AuditLog(
            organization_id=current_user.organization_id if current_user else None,
            user_id=current_user.id if current_user else None,
            action=action,
            module=module,
            severity="info",
            details=details,
        )
    )


@router.get("/")
def status() -> dict[str, object]:
    return {
        "module": "Identity",
        "status": "canonical",
        "description": "Organizations, users, roles, memberships, auth tokens, and SaaS identity boundaries.",
        "roles": sorted(ROLE_PERMISSIONS.keys()),
    }


@router.post("/bootstrap-admin")
def bootstrap_admin(payload: dict, request: Request, db: Session = Depends(get_db)):
    if db.query(User).count() > 0:
        raise HTTPException(status_code=409, detail="Ya existen usuarios. Use un administrador autenticado.")
    organization = Organization(
        name=str(payload.get("organization_name") or "OPERIA Local"),
        slug=str(payload.get("organization_slug") or "operia-local"),
        status="active",
    )
    db.add(organization)
    db.flush()
    user = User(
        organization_id=organization.id,
        name=str(payload.get("name") or "OPERIA Admin"),
        email=str(payload.get("email") or "admin@operia.local").lower(),
        role="admin",
        password_hash=hash_password(str(payload.get("password") or "operia-admin-change-me")),
        status="active",
    )
    db.add(user)
    db.flush()
    db.add(Membership(organization_id=organization.id, user_id=user.id, status="active"))
    token, expires_at = create_access_token(user.id, user.organization_id, user.role)
    db.add(
        AuthToken(
            organization_id=user.organization_id,
            user_id=user.id,
            token_hash=hash_token(token),
            expires_at=expires_at,
            user_agent=request.headers.get("user-agent", ""),
            ip_address=request.client.host if request.client else "",
        )
    )
    audit(db, "bootstrap_admin", "identity", details=f"Admin inicial creado: {user.email}")
    db.commit()
    return {"access_token": token, "token_type": "bearer", "expires_at": expires_at, "user": as_dict(user)}


@router.post("/login")
def login(payload: dict, request: Request, db: Session = Depends(get_db)):
    email = str(payload.get("email") or "").lower().strip()
    password = str(payload.get("password") or "")
    user = db.query(User).filter_by(email=email).first()
    if not user or not user.password_hash or not verify_password(password, user.password_hash):
        if user:
            user.failed_login_attempts += 1
            db.commit()
        raise HTTPException(status_code=401, detail="Credenciales invalidas")
    if user.status != "active":
        raise HTTPException(status_code=403, detail="Usuario inactivo")
    user.failed_login_attempts = 0
    user.last_login_at = datetime.now(timezone.utc).isoformat()
    token, expires_at = create_access_token(user.id, user.organization_id, user.role)
    db.add(
        AuthToken(
            organization_id=user.organization_id,
            user_id=user.id,
            token_hash=hash_token(token),
            expires_at=expires_at,
            user_agent=request.headers.get("user-agent", ""),
            ip_address=request.client.host if request.client else "",
        )
    )
    audit(db, "login", "identity", CurrentUser(user.id, user.organization_id, user.name, user.email, user.role))
    db.commit()
    return {"access_token": token, "token_type": "bearer", "expires_at": expires_at, "user": as_dict(user)}


@router.post("/logout")
def logout(payload: dict, current_user: CurrentUser = Depends(require_user), db: Session = Depends(get_db)):
    token = str(payload.get("token") or "")
    if token:
        row = db.query(AuthToken).filter_by(token_hash=hash_token(token), user_id=current_user.id).first()
        if row:
            row.revoked = True
    audit(db, "logout", "identity", current_user)
    db.commit()
    return {"ok": True}


@router.get("/me")
def me(current_user: CurrentUser | None = Depends(get_optional_user)):
    return {"authenticated": bool(current_user), "user": current_user.__dict__ if current_user else None}


@router.get("/permissions")
def permissions():
    return {role: sorted(values) for role, values in ROLE_PERMISSIONS.items()}


@router.get("/organizations")
def list_organizations(
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("audit:read")),
):
    query = db.query(Organization)
    if current_user.organization_id:
        query = query.filter_by(id=current_user.organization_id)
    return [as_dict(row) for row in query.order_by(Organization.name).all()]


@router.post("/organizations")
def create_organization(
    payload: dict,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("audit:read")),
):
    row = Organization(**payload)
    db.add(row)
    audit(db, "create_organization", "identity", current_user, details=str(payload.get("name") or ""))
    db.commit()
    db.refresh(row)
    return as_dict(row)


@router.get("/users")
def list_users(
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("audit:read")),
):
    query = db.query(User)
    if current_user.organization_id:
        query = query.filter_by(organization_id=current_user.organization_id)
    return [as_dict(row) for row in query.order_by(User.name).all()]


@router.post("/users")
def create_user(
    payload: dict,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("audit:read")),
):
    organization_id = payload.get("organization_id") or current_user.organization_id
    row = User(
        organization_id=organization_id,
        name=str(payload.get("name") or ""),
        email=str(payload.get("email") or "").lower(),
        role=str(payload.get("role") or "analista"),
        status=str(payload.get("status") or "active"),
        password_hash=hash_password(str(payload.get("password") or "operia-change-me")),
    )
    db.add(row)
    db.flush()
    if organization_id:
        db.add(Membership(organization_id=organization_id, user_id=row.id, status="active"))
    audit(db, "create_user", "identity", current_user, details=row.email or row.name)
    db.commit()
    db.refresh(row)
    return as_dict(row)


@router.get("/roles")
def list_roles(db: Session = Depends(get_db)):
    db_roles = [as_dict(row) for row in db.query(Role).order_by(Role.name).all()]
    configured = [{"name": role, "permissions": sorted(perms)} for role, perms in ROLE_PERMISSIONS.items()]
    return {"configured": configured, "database": db_roles}


@router.get("/memberships")
def list_memberships(
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("audit:read")),
):
    query = db.query(Membership)
    if current_user.organization_id:
        query = query.filter_by(organization_id=current_user.organization_id)
    return [as_dict(row) for row in query.order_by(Membership.id.desc()).all()]

