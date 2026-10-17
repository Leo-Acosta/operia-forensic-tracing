from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from operia.core.database import Base
from operia.shared.models import TimestampMixin
from operia.shared.time import utcnow


class Evidence(Base, TimestampMixin):
    __tablename__ = "evidence"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    organization_id: Mapped[int | None] = mapped_column(ForeignKey("organizations.id"), nullable=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("cases.id"))
    technical_data_id: Mapped[int | None] = mapped_column(ForeignKey("technical_data.id"))
    evidence_type: Mapped[str] = mapped_column(String(120), default="documento digital")
    description: Mapped[str] = mapped_column(Text)
    source: Mapped[str] = mapped_column(String(255), default="")
    acquired_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    responsible: Mapped[str] = mapped_column(String(160), default="")
    custodian: Mapped[str] = mapped_column(String(160), default="")
    sha256_hash: Mapped[str] = mapped_column(String(128), default="")
    md5_hash: Mapped[str | None] = mapped_column(String(64))
    file_location: Mapped[str | None] = mapped_column(String(500))
    preservation_method: Mapped[str] = mapped_column(Text, default="")
    tool_used: Mapped[str] = mapped_column(String(255), default="")
    evidence_nature: Mapped[str] = mapped_column(String(80), default="copia forense")
    was_altered: Mapped[bool] = mapped_column(Boolean, default=False)
    alteration_justification: Mapped[str] = mapped_column(Text, default="")
    custody_observations: Mapped[str] = mapped_column(Text, default="")
    integrity_status: Mapped[str] = mapped_column(String(80), default="pendiente de validacion")
    confidence_level: Mapped[str] = mapped_column(String(40), default="medio")

    case: Mapped["Case"] = relationship(back_populates="evidence")
    technical_data: Mapped["TechnicalData | None"] = relationship(back_populates="evidence_items")
    actions: Mapped[list["ChainOfCustodyAction"]] = relationship(back_populates="evidence")


class ChainOfCustodyAction(Base, TimestampMixin):
    __tablename__ = "chain_of_custody_actions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    organization_id: Mapped[int | None] = mapped_column(ForeignKey("organizations.id"), nullable=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("cases.id"))
    evidence_id: Mapped[int | None] = mapped_column(ForeignKey("evidence.id"))
    action_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    user_responsible: Mapped[str] = mapped_column(String(160), default="")
    user_role: Mapped[str] = mapped_column(String(80), default="")
    action_type: Mapped[str] = mapped_column(String(100), default="carga")
    detailed_description: Mapped[str] = mapped_column(Text)
    tool_used: Mapped[str] = mapped_column(String(255), default="")
    command_or_procedure: Mapped[str] = mapped_column(Text, default="")
    result_obtained: Mapped[str] = mapped_column(Text, default="")
    altered_evidence: Mapped[bool] = mapped_column(Boolean, default=False)
    hash_before: Mapped[str] = mapped_column(String(128), default="")
    hash_after: Mapped[str] = mapped_column(String(128), default="")
    validated_by: Mapped[str] = mapped_column(String(160), default="")
    legal_observations: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(80), default="registrada")

    case: Mapped["Case"] = relationship(back_populates="actions")
    evidence: Mapped[Evidence | None] = relationship(back_populates="actions")
    ledger_entry: Mapped["CustodyLedgerEntry | None"] = relationship(
        foreign_keys="CustodyLedgerEntry.action_id", uselist=False, viewonly=True)


class CustodyLedgerEntry(Base):
    __tablename__ = "custody_ledger_entries"
    __table_args__ = (UniqueConstraint("root_action_id", "version", name="uq_custody_root_version"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    organization_id: Mapped[int | None] = mapped_column(ForeignKey("organizations.id"))
    case_id: Mapped[int] = mapped_column(ForeignKey("cases.id"))
    action_id: Mapped[int] = mapped_column(ForeignKey("chain_of_custody_actions.id"), unique=True)
    root_action_id: Mapped[int] = mapped_column(ForeignKey("chain_of_custody_actions.id"))
    previous_action_id: Mapped[int | None] = mapped_column(ForeignKey("chain_of_custody_actions.id"))
    version: Mapped[int] = mapped_column(Integer)
    kind: Mapped[str] = mapped_column(String(30))
    actor_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    actor_name: Mapped[str] = mapped_column(String(160))
    actor_role: Mapped[str] = mapped_column(String(80))
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    occurred_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    occurred_at_original: Mapped[str | None] = mapped_column(String(80))
    reason: Mapped[str] = mapped_column(Text, default="")
    changes_json: Mapped[str] = mapped_column(Text, default="{}")


class Attachment(Base, TimestampMixin):
    __tablename__ = "attachments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    organization_id: Mapped[int | None] = mapped_column(ForeignKey("organizations.id"), nullable=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("cases.id"))
    file_name: Mapped[str] = mapped_column(String(255))
    file_path: Mapped[str] = mapped_column(String(500))
    sha256_hash: Mapped[str] = mapped_column(String(128), default="")
    mime_type: Mapped[str] = mapped_column(String(120), default="")


from operia.evidence import custody as _custody  # noqa: E402,F401 - register invariants for every ORM session.

