import base64
import hashlib
import hmac
import json
import secrets
import os
import stat
from functools import lru_cache
from pathlib import Path
from datetime import datetime, timedelta, timezone

from operia.core.config import settings


PASSWORD_ITERATIONS = 600_000


def hash_password(password: str, salt: str | None = None) -> str:
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), PASSWORD_ITERATIONS)
    return f"pbkdf2_sha256${PASSWORD_ITERATIONS}${salt}${digest.hex()}"


def verify_password(password: str, encoded: str) -> bool:
    try:
        parts = encoded.split("$")
        if parts[0] != "pbkdf2_sha256" or len(password) > 1024:
            return False
        if len(parts) == 3:
            _, salt, expected = parts
            iterations = 120_000  # Verify preserved legacy credentials; upgrade only after valid login.
        elif len(parts) == 4:
            _, raw_iterations, salt, expected = parts
            iterations = int(raw_iterations)
            if not 120_000 <= iterations <= 2_000_000:
                return False
        else:
            return False
        candidate = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), iterations).hex()
        return hmac.compare_digest(candidate, expected)
    except (ValueError, TypeError):
        return False


@lru_cache(maxsize=128)
def _stored_secret(path_string: str) -> bytes:
    from operia.security.private_files import no_links, protect
    path = no_links(path_string)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        pass
    else:
        with os.fdopen(descriptor, "wb") as handle:
            protect(path)  # Apply the private ACL before writing any secret bytes.
            handle.write(secrets.token_bytes(32))
            handle.flush()
            os.fsync(handle.fileno())
    if path.is_symlink() or not stat.S_ISREG(path.stat().st_mode):
        raise RuntimeError("auth_key_file_rejected")
    with path.open("rb") as handle:
        value = handle.read(33)
    if len(value) != 32:
        raise RuntimeError("auth_key_file_invalid")
    return value


def _secret() -> bytes:
    if settings.auth_signing_key_file is not None:
        if settings.auth_signing_key is not None:
            raise RuntimeError("auth_key_sources_conflict")
        from operia.security.private_files import read_key
        return read_key(settings.auth_signing_key_file)
    if settings.env.lower() == "production":
        raise RuntimeError("production_secret_file_required")
    if settings.auth_signing_key is not None:
        value = settings.auth_signing_key.get_secret_value().encode("utf-8")
        if len(value) < 32:
            raise RuntimeError("auth_signing_key_too_short")
        return value
    return _stored_secret(str((settings.storage_dir / ".auth-signing-key").absolute()))


def create_access_token(user_id: int, organization_id: int | None, role: str, expires_minutes: int = 480) -> tuple[str, str]:
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=expires_minutes)
    payload = {
        "user_id": user_id,
        "organization_id": organization_id,
        "role": role,
        "exp": expires_at.isoformat(),
        "nonce": secrets.token_hex(8),
    }
    body = base64.urlsafe_b64encode(json.dumps(payload, separators=(",", ":")).encode("utf-8")).decode("ascii")
    signature = hmac.new(_secret(), body.encode("ascii"), hashlib.sha256).hexdigest()
    return f"{body}.{signature}", expires_at.isoformat()


def verify_access_token(token: str) -> dict | None:
    if len(token) > 8192:
        return None
    try:
        body, signature = token.split(".", 1)
        expected = hmac.new(_secret(), body.encode("ascii"), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(signature, expected):
            return None
        payload = json.loads(base64.urlsafe_b64decode(body.encode("ascii")).decode("utf-8"))
        if datetime.fromisoformat(payload["exp"]) < datetime.now(timezone.utc):
            return None
        return payload
    except Exception:
        return None


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()

