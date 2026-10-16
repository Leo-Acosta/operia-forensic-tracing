from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from operia.audit.models import AuditLog
from operia.core.config import settings
from operia.core.database import get_db
from operia.identity.dependencies import CurrentUser, get_optional_user, require_permission, require_user
from operia.identity.models import AuthToken, Membership, Organization, Role, User
from operia.identity.permissions import ROLE_PERMISSIONS
from operia.identity.security import create_access_token, hash_password, hash_token, verify_password

router = APIRouter()

PROFILE_FIELDS = {"name", "title", "agency", "registration_id", "phone", "signature", "profile_notes"}
ADMIN_USER_FIELDS = PROFILE_FIELDS | {"email", "role", "status", "organization_id"}
VALID_ROLES = set(ROLE_PERMISSIONS)
VALID_STATUSES = {"active", "inactive", "suspended"}


def as_dict(obj) -> dict:
    data = {column.name: getattr(obj, column.name) for column in obj.__table__.columns}
    data.pop("password_hash", None)
    data.pop("token_hash", None)
    return data


def apply_user_updates(user: User, payload: dict, allowed_fields: set[str]) -> list[str]:
    changed: list[str] = []
    for field in allowed_fields:
        if field not in payload:
            continue
        value = payload.get(field)
        if field == "email":
            value = str(value or "").lower().strip()
        elif field == "organization_id":
            value = int(value) if value not in (None, "") else None
        else:
            value = str(value or "").strip()
        if field == "role" and value not in VALID_ROLES:
            raise HTTPException(status_code=422, detail="Rol no permitido")
        if field == "status" and value not in VALID_STATUSES:
            raise HTTPException(status_code=422, detail="Estado de usuario no permitido")
        if getattr(user, field) != value:
            setattr(user, field, value)
            changed.append(field)
    return changed


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


def is_local_recovery_request(request: Request) -> bool:
    host = request.client.host if request.client else ""
    return settings.local_recovery_enabled and settings.env == "local" and host in {"127.0.0.1", "::1", "localhost", "testclient"}


def issue_token(user: User, request: Request, db: Session) -> tuple[str, str]:
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
    return token, expires_at


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
    host = request.client.host if request.client else ""
    if settings.env != "local" or host not in {"127.0.0.1", "::1", "localhost", "testclient"}:
        raise HTTPException(403, "Inicializacion de identidad solo desde el host local")
    password = str(payload.get("password") or "")
    if not 10 <= len(password) <= 1024:
        raise HTTPException(422, "Se requiere clave explicita de 10 a 1024 caracteres")
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
        password_hash=hash_password(password),
        status="active",
    )
    db.add(user)
    db.flush()
    db.add(Membership(organization_id=organization.id, user_id=user.id, status="active"))
    token, expires_at = issue_token(user, request, db)
    audit(db, "bootstrap_admin", "identity", details=f"Admin inicial creado: {user.email}")
    db.commit()
    return {"access_token": token, "token_type": "bearer", "expires_at": expires_at, "user": as_dict(user)}


@router.post("/local-admin-recovery")
def local_admin_recovery(payload: dict, request: Request, db: Session = Depends(get_db)):
    if not is_local_recovery_request(request):
        raise HTTPException(status_code=403, detail="Recuperación local no disponible en este entorno.")

    email = str(payload.get("email") or "admin@operia.local").lower().strip()
    password = str(payload.get("password") or "")
    if not 10 <= len(password) <= 1024:
        raise HTTPException(422, "Se requiere una clave explicita de 10 a 1024 caracteres")
    name = str(payload.get("name") or "OPERIA Admin").strip() or "OPERIA Admin"

    organization = (
        db.query(Organization).filter_by(slug=str(payload.get("organization_slug") or "operia-local")).first()
        or db.query(Organization).order_by(Organization.id.asc()).first()
    )
    if not organization:
        organization = Organization(
            name=str(payload.get("organization_name") or "OPERIA Local"),
            slug=str(payload.get("organization_slug") or "operia-local"),
            status="active",
        )
        db.add(organization)
        db.flush()

    user = db.query(User).filter_by(email=email).first()
    if not user:
        user = db.query(User).filter_by(role="admin").order_by(User.id.asc()).first()
    if not user:
        user = db.query(User).order_by(User.id.asc()).first()

    if user:
        existing_email_owner = db.query(User).filter_by(email=email).first()
        if not existing_email_owner or existing_email_owner.id == user.id:
            user.email = email
        user.name = name
        user.organization_id = organization.id
        user.role = "admin"
        user.status = "active"
        user.failed_login_attempts = 0
        user.password_hash = hash_password(password)
    else:
        user = User(
            organization_id=organization.id,
            name=name,
            email=email,
            role="admin",
            password_hash=hash_password(password),
            status="active",
        )
        db.add(user)
        db.flush()

    membership = db.query(Membership).filter_by(organization_id=organization.id, user_id=user.id).first()
    if not membership:
        db.add(Membership(organization_id=organization.id, user_id=user.id, status="active"))

    token, expires_at = issue_token(user, request, db)
    audit(db, "local_admin_recovery", "identity", details=f"Acceso local recuperado: {user.email}")
    db.commit()
    db.refresh(user)
    return {"access_token": token, "token_type": "bearer", "expires_at": expires_at, "user": as_dict(user)}


@router.post("/login")
def login(payload: dict, request: Request, db: Session = Depends(get_db)):
    email = str(payload.get("email") or "").lower().strip()
    password = str(payload.get("password") or "")
    user = db.query(User).filter_by(email=email).first()
    if not user or not user.password_hash or not verify_password(password, user.password_hash):
        if user:
            user.failed_login_attempts += 1
            audit(
                db,
                "failed_login",
                "identity",
                CurrentUser(user.id, user.organization_id, user.name, user.email, user.role),
                details=f"Intento fallido #{user.failed_login_attempts}",
            )
            db.commit()
        raise HTTPException(status_code=401, detail="Credenciales inválidas")
    if user.password_hash.count("$") == 2:
        user.password_hash = hash_password(password)
    if user.status != "active":
        raise HTTPException(status_code=403, detail="Usuario inactivo")
    user.failed_login_attempts = 0
    user.last_login_at = datetime.now(timezone.utc).isoformat()
    token, expires_at = issue_token(user, request, db)
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


@router.put("/me/profile")
def update_my_profile(
    payload: dict,
    current_user: CurrentUser = Depends(require_user),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter_by(id=current_user.id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    changed = apply_user_updates(user, payload, PROFILE_FIELDS)
    audit(db, "update_profile", "identity", current_user, details=", ".join(changed) or "sin cambios")
    db.commit()
    db.refresh(user)
    return as_dict(user)


@router.get("/permissions")
def permissions():
    return {role: sorted(values) for role, values in ROLE_PERMISSIONS.items()}


@router.get("/organizations")
def list_organizations(
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("identity:read")),
):
    query = db.query(Organization)
    if not current_user.organization_id:
        raise HTTPException(403, "Organizacion requerida")
    query = query.filter_by(id=current_user.organization_id)
    return [as_dict(row) for row in query.order_by(Organization.name).all()]


@router.post("/organizations")
def create_organization(
    payload: dict,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("identity:write")),
):
    raise HTTPException(403, "Creacion de organizaciones reservada al operador de plataforma")


@router.get("/users")
def list_users(
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("identity:read")),
):
    query = db.query(User)
    if current_user.organization_id:
        query = query.filter_by(organization_id=current_user.organization_id)
    return [as_dict(row) for row in query.order_by(User.name).all()]


@router.post("/users")
def create_user(
    payload: dict,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("identity:write")),
):
    organization_id = current_user.organization_id
    if not organization_id or payload.get("organization_id", organization_id) != organization_id:
        raise HTTPException(403, "No se pueden administrar usuarios de otra organizacion")
    password = str(payload.get("password") or "")
    if not 10 <= len(password) <= 1024 or payload.get("role", "analista") not in VALID_ROLES or payload.get("status", "active") not in VALID_STATUSES:
        raise HTTPException(422, "Clave, rol o estado de usuario invalido")
    row = User(
        organization_id=organization_id,
        name=str(payload.get("name") or ""),
        email=str(payload.get("email") or "").lower(),
        role=str(payload.get("role") or "analista"),
        status=str(payload.get("status") or "active"),
        title=str(payload.get("title") or ""),
        agency=str(payload.get("agency") or ""),
        registration_id=str(payload.get("registration_id") or ""),
        phone=str(payload.get("phone") or ""),
        signature=str(payload.get("signature") or ""),
        profile_notes=str(payload.get("profile_notes") or ""),
        password_hash=hash_password(password),
    )
    db.add(row)
    db.flush()
    if organization_id:
        db.add(Membership(organization_id=organization_id, user_id=row.id, status="active"))
    audit(db, "create_user", "identity", current_user, details=row.email or row.name)
    db.commit()
    db.refresh(row)
    return as_dict(row)


@router.put("/users/{user_id}")
def update_user(
    user_id: int,
    payload: dict,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("identity:write")),
):
    row = db.query(User).filter_by(id=user_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    if current_user.organization_id and row.organization_id != current_user.organization_id:
        raise HTTPException(status_code=403, detail="Usuario fuera de la organizacion")
    existing_email = str(payload.get("email") or "").lower().strip()
    if existing_email:
        owner = db.query(User).filter(User.email == existing_email, User.id != user_id).first()
        if owner:
            raise HTTPException(status_code=409, detail="El email ya esta asignado a otro usuario")
    if not current_user.organization_id or payload.get("organization_id", current_user.organization_id) != current_user.organization_id:
        raise HTTPException(403, "No se permite trasladar usuarios entre organizaciones")
    changed = apply_user_updates(row, payload, ADMIN_USER_FIELDS)
    if set(changed) & {"role", "status", "organization_id"}:
        db.query(AuthToken).filter_by(user_id=row.id).update({"revoked": True})
    if row.id == current_user.id and row.status != "active":
        raise HTTPException(status_code=422, detail="No podes desactivar tu propio usuario activo")
    audit(db, "update_user", "identity", current_user, details=f"{row.email or row.id}: {', '.join(changed) or 'sin cambios'}")
    db.commit()
    db.refresh(row)
    return as_dict(row)


@router.post("/users/{user_id}/reset-password")
def reset_user_password(
    user_id: int,
    payload: dict,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("identity:write")),
):
    password = str(payload.get("password") or "")
    if not 10 <= len(password) <= 1024:
        raise HTTPException(status_code=422, detail="La nueva clave debe tener entre 10 y 1024 caracteres")
    row = db.query(User).filter_by(id=user_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    if current_user.organization_id and row.organization_id != current_user.organization_id:
        raise HTTPException(status_code=403, detail="Usuario fuera de la organizacion")
    row.password_hash = hash_password(password)
    row.failed_login_attempts = 0
    db.query(AuthToken).filter_by(user_id=user_id).update({"revoked": True})
    audit(db, "reset_user_password", "identity", current_user, details=row.email or str(row.id))
    db.commit()
    return {"ok": True, "message": "Clave actualizada y sesiones anteriores revocadas"}


@router.get("/roles")
def list_roles(
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("identity:read")),
):
    db_roles = [as_dict(row) for row in db.query(Role).filter(Role.organization_id == current_user.organization_id).order_by(Role.name).all()]
    configured = [{"name": role, "permissions": sorted(perms)} for role, perms in ROLE_PERMISSIONS.items()]
    return {"configured": configured, "database": db_roles}


@router.get("/memberships")
def list_memberships(
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("identity:read")),
):
    query = db.query(Membership)
    if current_user.organization_id:
        query = query.filter_by(organization_id=current_user.organization_id)
    return [as_dict(row) for row in query.order_by(Membership.id.desc()).all()]
