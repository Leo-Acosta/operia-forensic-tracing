from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from operia.core.database import Base
from operia.shared.models import TimestampMixin


class RubricEvaluation(Base, TimestampMixin):
    __tablename__ = "rubric_evaluations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    organization_id: Mapped[int | None] = mapped_column(ForeignKey("organizations.id"), nullable=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("cases.id"), index=True)
    rubric_key: Mapped[str] = mapped_column(String(120), default="written_legal_evidence_report_2026", index=True)
    rubric_title: Mapped[str] = mapped_column(String(255), default="Written Legal Evidence Report 2026")
    total_score: Mapped[int] = mapped_column(Integer, default=0)
    max_score: Mapped[int] = mapped_column(Integer, default=20)
    percentage: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(80), default="incompleto")
    sections_json: Mapped[str] = mapped_column(Text, default="[]")
    missing_json: Mapped[str] = mapped_column(Text, default="[]")
    recommendations_json: Mapped[str] = mapped_column(Text, default="[]")
    summary: Mapped[str] = mapped_column(Text, default="")
    evaluated_by: Mapped[str] = mapped_column(String(160), default="OPERIA")

    case: Mapped["Case"] = relationship(back_populates="rubric_evaluations")
