"""Append-only custody, legacy-safe ledger and SQLite enforcement."""
import json
from datetime import timezone

from fastapi import HTTPException
from sqlalchemy import event, text, desc
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError, OperationalError

from operia.evidence.models import ChainOfCustodyAction, CustodyLedgerEntry


def install_sqlite_protection(connection):
    if connection.dialect.name != "sqlite":
        raise RuntimeError("custody_database_backend_not_validated")
    for table in ("chain_of_custody_actions", "custody_ledger_entries"):
        for operation in ("UPDATE", "DELETE"):
            connection.execute(text(f"CREATE TRIGGER IF NOT EXISTS {table}_no_{operation.lower()} "
                f"BEFORE {operation} ON {table} BEGIN SELECT RAISE(ABORT, 'custody_append_only'); END"))
    connection.execute(text("CREATE TRIGGER IF NOT EXISTS cases_preserve_custody BEFORE DELETE ON cases "
        "WHEN EXISTS (SELECT 1 FROM chain_of_custody_actions WHERE case_id=OLD.id) "
        "BEGIN SELECT RAISE(ABORT, 'custody_parent_preserved'); END"))
    connection.execute(text("CREATE TRIGGER IF NOT EXISTS evidence_preserve_custody BEFORE DELETE ON evidence "
        "WHEN EXISTS (SELECT 1 FROM chain_of_custody_actions WHERE evidence_id=OLD.id) "
        "BEGIN SELECT RAISE(ABORT, 'custody_parent_preserved'); END"))


@event.listens_for(Session, "before_flush")
def guard_custody(db, context, instances):
    from operia.cases.models import Case
    from operia.evidence.models import Evidence
    for item in list(db.dirty) + list(db.deleted):
        if isinstance(item, (ChainOfCustodyAction, CustodyLedgerEntry)):
            if item in db.deleted or db.is_modified(item, include_collections=False):
                raise HTTPException(409, "custody_append_only: registrar una rectificación")
    for item in list(db.deleted):
        if isinstance(item, (Case, Evidence)):
            column = ChainOfCustodyAction.case_id if isinstance(item, Case) else ChainOfCustodyAction.evidence_id
            if db.query(ChainOfCustodyAction.id).filter(column == item.id).first():
                raise HTTPException(409, "custody_parent_preserved")
    pending = db.info.setdefault("new_custody_events", [])
    for item in list(db.new):
        if not isinstance(item, ChainOfCustodyAction):
            continue
        actor = db.info.get("request_actor") or db.info.get("authenticated_actor")
        if actor:
            item.user_responsible = actor.name
            item.user_role = actor.role
            item.organization_id = actor.organization_id
        pending.append((item, actor, getattr(item, "_custody_revision", None)))


@event.listens_for(Session, "after_flush_postexec")
def register_custody(db, context):
    for item, actor, revision in db.info.pop("new_custody_events", []):
        revision = revision or {}
        occurred = revision.get("occurred_at")
        db.add(CustodyLedgerEntry(organization_id=item.organization_id, case_id=item.case_id,
            action_id=item.id, root_action_id=revision.get("root", item.id),
            previous_action_id=revision.get("previous"), version=revision.get("version", 0),
            kind="rectification" if revision else "event", actor_user_id=actor.id if actor else None,
            actor_name=actor.name if actor else "Proceso interno sin actor de solicitud",
            actor_role=actor.role if actor else "system",
            occurred_at=occurred.astimezone(timezone.utc) if occurred else None,
            occurred_at_original=occurred.isoformat() if occurred else None,
            reason=revision.get("reason", ""), changes_json=json.dumps(revision.get("changes", {}), ensure_ascii=False)))


@event.listens_for(Session, "after_rollback")
def clear_custody_pending(db):
    db.info.pop("new_custody_events", None)


def rectify(db, target, payload):
    ledger = db.query(CustodyLedgerEntry).filter_by(action_id=target.id).first()
    root = ledger.root_action_id if ledger else target.id
    latest = db.query(CustodyLedgerEntry).filter_by(root_action_id=root).order_by(desc(CustodyLedgerEntry.version)).first()
    if (latest.action_id if latest else root) != target.id:
        raise HTTPException(409, "custody_revision_conflict: recargá la cadena")
    from operia.evidence.schemas import CustodyActionCreate
    values = {key: getattr(target, key) for key in CustodyActionCreate.model_fields}
    values.update(payload.changes)
    values["action_type"] = "rectificacion"
    values["detailed_description"] = (f"Rectificación de evento #{target.id}. Motivo: {payload.reason}. "
        + str(payload.changes.get("detailed_description", "Se agrega constancia sin sustituir el original.")))
    item = ChainOfCustodyAction(**values, organization_id=target.organization_id)
    item._custody_revision = {"root": root, "previous": target.id,
        "version": (latest.version if latest else 0) + 1, "reason": payload.reason,
        "occurred_at": payload.occurred_at, "changes": payload.changes}
    db.add(item)
    try:
        db.flush()
        db.flush()  # Persist the version reservation added by after_flush_postexec.
    except (IntegrityError, OperationalError):
        db.rollback()
        raise HTTPException(409, "custody_revision_conflict: recargá la cadena") from None
    return item
