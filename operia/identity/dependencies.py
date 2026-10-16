from dataclasses import dataclass
from datetime import datetime, timezone

from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session

from operia.core.database import get_db
from operia.identity.models import AuthToken, User, Organization
from operia.identity.permissions import has_permission
from operia.identity.security import hash_token, verify_access_token


@dataclass
class CurrentUser:
    id: int
    organization_id: int | None
    name: str
    email: str | None
    role: str
    title: str = ""
    agency: str = ""
    registration_id: str = ""
    phone: str = ""
    signature: str = ""
    profile_notes: str = ""


def _parse_datetime(value: str) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(value)
    except (TypeError, ValueError):
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def get_optional_user(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> CurrentUser | None:
    if not authorization or not authorization.lower().startswith("bearer "):
        return None
    token = authorization.split(" ", 1)[1].strip()
    payload = verify_access_token(token)
    if not payload:
        return None
    token_row = db.query(AuthToken).filter_by(token_hash=hash_token(token), revoked=False).first()
    if not token_row:
        return None
    try:
        payload_user_id = int(payload["user_id"])
    except (KeyError, TypeError, ValueError):
        return None
    if token_row.user_id != payload_user_id:
        return None
    expires_at = _parse_datetime(str(token_row.expires_at))
    if not expires_at or expires_at < datetime.now(timezone.utc):
        return None
    payload_organization_id = payload.get("organization_id")
    if payload_organization_id is not None:
        try:
            organization_id = int(payload_organization_id)
        except (TypeError, ValueError):
            return None
        if token_row.organization_id != organization_id:
            return None
    user = db.get(User, payload_user_id)
    if not user or user.status != "active" or not user.organization_id:
        return None
    if user.organization_id != token_row.organization_id or user.organization_id != payload_organization_id or payload.get("role") != user.role:
        return None
    organization = db.get(Organization, user.organization_id)
    if not organization or organization.status != "active":
        return None
    return CurrentUser(
        id=user.id,
        organization_id=user.organization_id,
        name=user.name,
        email=user.email,
        role=user.role,
        title=user.title,
        agency=user.agency,
        registration_id=user.registration_id,
        phone=user.phone,
        signature=user.signature,
        profile_notes=user.profile_notes,
    )


def require_user(current_user: CurrentUser | None = Depends(get_optional_user)) -> CurrentUser:
    if not current_user:
        raise HTTPException(status_code=401, detail="Sesión requerida o vencida. Inicia sesión en Usuarios.")
    return current_user


def require_permission(permission: str):
    def dependency(current_user: CurrentUser = Depends(require_user)) -> CurrentUser:
        if not has_permission(current_user.role, permission):
            raise HTTPException(status_code=403, detail="Permiso insuficiente para ejecutar esta acción.")
        return current_user

    return dependency


def same_organization(current_user: CurrentUser | None, organization_id: int | None) -> bool:
    if current_user is None or current_user.organization_id is None or organization_id is None:
        return False
    return current_user.organization_id == organization_id
