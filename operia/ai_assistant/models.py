from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from operia.core.database import Base
from operia.shared.models import TimestampMixin


class AIInteraction(Base, TimestampMixin):
    __tablename__ = "ai_interactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    organization_id: Mapped[int | None] = mapped_column(ForeignKey("organizations.id"), nullable=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    case_id: Mapped[int | None] = mapped_column(ForeignKey("cases.id"), nullable=True)
    provider: Mapped[str] = mapped_column(String(80), default="ollama")
    model_name: Mapped[str] = mapped_column(String(120), default="mistral")
    task_type: Mapped[str] = mapped_column(String(120), default="forensic_assistance")
    prompt: Mapped[str] = mapped_column(Text)
    response: Mapped[str] = mapped_column(Text, default="")
    sources_used: Mapped[str] = mapped_column(Text, default="[]")
    status: Mapped[str] = mapped_column(String(80), default="completed")
    requires_human_review: Mapped[bool] = mapped_column(Boolean, default=True)
    safety_notes: Mapped[str] = mapped_column(Text, default="")

