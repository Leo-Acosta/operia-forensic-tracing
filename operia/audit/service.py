from sqlalchemy.orm import Session

from operia.audit.models import AuditLog
from operia.identity.dependencies import CurrentUser


def write_audit(
    db: Session,
    action: str,
    module: str,
    current_user: CurrentUser | None = None,
    case_id: int | None = None,
    entity_type: str = "",
    entity_id: str = "",
    severity: str = "info",
    details: str = "",
) -> None:
    db.add(
        AuditLog(
            organization_id=current_user.organization_id if current_user else None,
            user_id=current_user.id if current_user else None,
            case_id=case_id,
            action=action,
            module=module,
            entity_type=entity_type,
            entity_id=entity_id,
            severity=severity,
            details=details,
        )
    )

