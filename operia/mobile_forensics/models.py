from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, LargeBinary, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from operia.core.database import Base
from operia.shared.time import utcnow


class MobileDevice(Base):
    __tablename__ = "mobile_devices"
    id: Mapped[int] = mapped_column(primary_key=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), index=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("cases.id"), index=True)
    label: Mapped[str] = mapped_column(String(160))
    platform: Mapped[str] = mapped_column(String(20))
    identifier: Mapped[str] = mapped_column(String(160), default="")
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class MobileExam(Base):
    __tablename__ = "mobile_exams"
    __table_args__ = (UniqueConstraint("device_id", "sha256", name="uq_mobile_device_input"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), index=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("cases.id"), index=True)
    device_id: Mapped[int] = mapped_column(ForeignKey("mobile_devices.id"))
    operator_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    authorization: Mapped[str] = mapped_column(Text)
    data_owner_consent: Mapped[bool] = mapped_column(Boolean)
    scope: Mapped[str] = mapped_column(Text)
    provenance: Mapped[str] = mapped_column(Text)
    acquisition_method: Mapped[str] = mapped_column(String(160))
    acquisition_date: Mapped[str] = mapped_column(String(80))
    retention_policy: Mapped[str] = mapped_column(Text)
    declared_mvt_version: Mapped[str] = mapped_column(String(80))
    declared_run_id: Mapped[str] = mapped_column(String(160))
    indicators_description: Mapped[str] = mapped_column(Text)
    filename: Mapped[str] = mapped_column(String(100))
    sha256: Mapped[str] = mapped_column(String(64))
    original_bytes: Mapped[bytes] = mapped_column(LargeBinary)
    record_count: Mapped[int] = mapped_column(Integer)
    candidate_count: Mapped[int] = mapped_column(Integer)
    coverage: Mapped[str] = mapped_column(String(80))
    limitations: Mapped[str] = mapped_column(Text)


class MobileReview(Base):
    __tablename__ = "mobile_reviews"
    id: Mapped[int] = mapped_column(primary_key=True)
    exam_id: Mapped[int] = mapped_column(ForeignKey("mobile_exams.id"), index=True)
    reviewer_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    reviewer_name: Mapped[str] = mapped_column(String(160))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    conclusion: Mapped[str] = mapped_column(String(100))
    rationale: Mapped[str] = mapped_column(Text)
    alternatives: Mapped[str] = mapped_column(Text)
    limitations: Mapped[str] = mapped_column(Text)
    references_json: Mapped[str] = mapped_column(Text)
    current_activity: Mapped[str] = mapped_column(Text)
    chronology: Mapped[str] = mapped_column(Text)
    attribution: Mapped[str] = mapped_column(Text)


class MobileExport(Base):
    __tablename__ = "mobile_exports"
    id: Mapped[int] = mapped_column(primary_key=True)
    exam_id: Mapped[int] = mapped_column(ForeignKey("mobile_exams.id"), index=True)
    review_id: Mapped[int | None] = mapped_column(ForeignKey("mobile_reviews.id"), nullable=True)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    sha256: Mapped[str] = mapped_column(String(64))
    content: Mapped[bytes] = mapped_column(LargeBinary)
