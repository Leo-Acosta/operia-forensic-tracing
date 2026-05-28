from dataclasses import dataclass

from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session

from operia.core.database import get_db
from operia.identity.models import AuthToken, User
from operia.identity.permissions import has_permission
from operia.identity.security import hash_token, verify_access_token


@dataclass
class CurrentUser:
    id: int
    organization_id: int | None
    name: str
    email: str | None
    role: str


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
    user = db.get(User, int(payload["user_id"]))
    if not user or user.status != "active":
        return None
    return CurrentUser(
        id=user.id,
        organization_id=user.organization_id,
        name=user.name,
        email=user.email,
        role=user.role,
    )


def require_user(current_user: CurrentUser | None = Depends(get_optional_user)) -> CurrentUser:
    if not current_user:
        raise HTTPException(status_code=401, detail="Autenticacion requerida")
    return current_user


def require_permission(permission: str):
    def dependency(current_user: CurrentUser = Depends(require_user)) -> CurrentUser:
        if not has_permission(current_user.role, permission):
            raise HTTPException(status_code=403, detail="Permiso insuficiente")
        return current_user

    return dependency


def same_organization(current_user: CurrentUser | None, organization_id: int | None) -> bool:
    if current_user is None or current_user.organization_id is None or organization_id is None:
        return True
    return current_user.organization_id == organization_id

