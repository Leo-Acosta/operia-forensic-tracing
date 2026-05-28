from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from operia.core.database import Base
from operia.shared.models import TimestampMixin


class AIModelEvaluation(Base, TimestampMixin):
    __tablename__ = "ai_model_evaluations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    organization_id: Mapped[int | None] = mapped_column(ForeignKey("organizations.id"), nullable=True)
    provider: Mapped[str] = mapped_column(String(80), default="ollama")
    model_name: Mapped[str] = mapped_column(String(120), default="mistral")
    model_identifier: Mapped[str] = mapped_column(String(255), default="")
    environment: Mapped[str] = mapped_column(String(160), default="local")
    network_blocked: Mapped[bool] = mapped_column(Boolean, default=True)
    tools_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    overall_score: Mapped[int] = mapped_column(Integer, default=0)
    risk_level: Mapped[str] = mapped_column(String(40), default="medio")
    conclusion: Mapped[str] = mapped_column(Text, default="")
    recommendation: Mapped[str] = mapped_column(String(120), default="restricted")


class AIModelTestRun(Base, TimestampMixin):
    __tablename__ = "ai_model_test_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    organization_id: Mapped[int | None] = mapped_column(ForeignKey("organizations.id"), nullable=True)
    evaluation_id: Mapped[int] = mapped_column(ForeignKey("ai_model_evaluations.id"))
    test_code: Mapped[str] = mapped_column(String(120))
    test_name: Mapped[str] = mapped_column(String(255))
    category: Mapped[str] = mapped_column(String(120))
    prompt: Mapped[str] = mapped_column(Text)
    response: Mapped[str] = mapped_column(Text, default="")
    observed_behavior: Mapped[str] = mapped_column(Text, default="")
    severity: Mapped[str] = mapped_column(String(40), default="medio")
    passed: Mapped[bool] = mapped_column(Boolean, default=False)
    score: Mapped[int] = mapped_column(Integer, default=0)
    notes: Mapped[str] = mapped_column(Text, default="")

