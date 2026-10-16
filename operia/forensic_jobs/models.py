from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, LargeBinary, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from operia.core.database import Base
from operia.shared.time import utcnow


class Acquisition(Base):
    __tablename__ = "native_mobile_acquisitions"
    __table_args__ = (UniqueConstraint("device_id", "sha256", "format", name="uq_native_acquisition"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), index=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("cases.id"), index=True)
    device_id: Mapped[int] = mapped_column(ForeignKey("mobile_devices.id"))
    operator_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    filename: Mapped[str] = mapped_column(String(120))
    platform: Mapped[str] = mapped_column(String(20))
    format: Mapped[str] = mapped_column(String(80))
    metadata_json: Mapped[str] = mapped_column(Text)
    sha256: Mapped[str] = mapped_column(String(64))
    original_bytes: Mapped[bytes] = mapped_column(LargeBinary)


class IndicatorSet(Base):
    __tablename__ = "native_mobile_indicator_sets"
    __table_args__ = (UniqueConstraint("case_id", "sha256", name="uq_native_indicator_set"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), index=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("cases.id"), index=True)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    sha256: Mapped[str] = mapped_column(String(64))
    original_bytes: Mapped[bytes] = mapped_column(LargeBinary)
    version: Mapped[str] = mapped_column(String(160))
    source: Mapped[str] = mapped_column(Text)
    terms: Mapped[str] = mapped_column(Text)


class ExaminationJob(Base):
    __tablename__ = "native_mobile_jobs"
    __table_args__ = (UniqueConstraint("acquisition_id", "configuration_sha256", name="uq_native_job_configuration"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), index=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("cases.id"), index=True)
    acquisition_id: Mapped[int] = mapped_column(ForeignKey("native_mobile_acquisitions.id"))
    indicator_set_id: Mapped[int | None] = mapped_column(ForeignKey("native_mobile_indicator_sets.id"), nullable=True)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    state: Mapped[str] = mapped_column(String(50), default="pendiente", index=True)
    configuration_json: Mapped[str] = mapped_column(Text)
    configuration_sha256: Mapped[str] = mapped_column(String(64))
    cancel_requested: Mapped[bool] = mapped_column(Boolean, default=False)
    claim_token: Mapped[str] = mapped_column(String(64), default="")
    heartbeat_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_code: Mapped[str] = mapped_column(String(160), default="")
    result_bytes: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    result_sha256: Mapped[str] = mapped_column(String(64), default="")


class JobEvent(Base):
    __tablename__ = "native_mobile_job_events"
    id: Mapped[int] = mapped_column(primary_key=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("native_mobile_jobs.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    state: Mapped[str] = mapped_column(String(50))
    reason: Mapped[str] = mapped_column(String(160), default="")


class ReviewRevision(Base):
    __tablename__ = "native_mobile_reviews"
    id: Mapped[int] = mapped_column(primary_key=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("native_mobile_jobs.id"), index=True)
    reviewer_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    reviewer_name: Mapped[str] = mapped_column(String(160))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    result_sha256: Mapped[str] = mapped_column(String(64))
    content_json: Mapped[str] = mapped_column(Text)


class ExportRecord(Base):
    __tablename__ = "native_mobile_exports"
    id: Mapped[int] = mapped_column(primary_key=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("native_mobile_jobs.id"), index=True)
    review_id: Mapped[int | None] = mapped_column(ForeignKey("native_mobile_reviews.id"), nullable=True)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    format: Mapped[str] = mapped_column(String(20))
    content: Mapped[bytes] = mapped_column(LargeBinary)
    sha256: Mapped[str] = mapped_column(String(64))


class EvidenceIntegration(Base):
    __tablename__ = "native_mobile_evidence_integrations"
    __table_args__ = (UniqueConstraint("review_id", name="uq_native_integration_review"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"))
    case_id: Mapped[int] = mapped_column(ForeignKey("cases.id"))
    job_id: Mapped[int] = mapped_column(ForeignKey("native_mobile_jobs.id"))
    review_id: Mapped[int] = mapped_column(ForeignKey("native_mobile_reviews.id"))
    evidence_id: Mapped[int] = mapped_column(ForeignKey("evidence.id"))
    custody_id: Mapped[int] = mapped_column(ForeignKey("chain_of_custody_actions.id"))
    report_id: Mapped[int] = mapped_column(ForeignKey("reports.id"))
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    snapshot_bytes: Mapped[bytes] = mapped_column(LargeBinary)
    snapshot_sha256: Mapped[str] = mapped_column(String(64))


class AnalysisProjection(Base):
    __tablename__ = "native_mobile_projections"
    __table_args__ = (UniqueConstraint("integration_id", "request_sha256", name="uq_native_projection_request"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), index=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("cases.id"), index=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("native_mobile_jobs.id"))
    integration_id: Mapped[int] = mapped_column(ForeignKey("native_mobile_evidence_integrations.id"))
    finding_id: Mapped[int] = mapped_column(ForeignKey("findings.id"))
    hypothesis_id: Mapped[int] = mapped_column(ForeignKey("hypotheses.id"))
    geo_analysis_id: Mapped[int | None] = mapped_column(ForeignKey("geo_trace_analyses.id"), nullable=True)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    request_sha256: Mapped[str] = mapped_column(String(64))
    snapshot_bytes: Mapped[bytes] = mapped_column(LargeBinary)
    snapshot_sha256: Mapped[str] = mapped_column(String(64))
