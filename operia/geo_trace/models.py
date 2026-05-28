from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from operia.core.database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class GeoTraceAnalysis(Base, TimestampMixin):
    __tablename__ = "geo_trace_analyses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    case_id: Mapped[int | None] = mapped_column(ForeignKey("cases.id"), nullable=True)
    title: Mapped[str] = mapped_column(String(255), default="Geo Trace analysis")
    input_text: Mapped[str] = mapped_column(Text, default="")
    summary: Mapped[str] = mapped_column(Text, default="")
    map_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    evidence_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    status: Mapped[str] = mapped_column(String(80), default="completed")


class GeoTarget(Base, TimestampMixin):
    __tablename__ = "geo_trace_targets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    analysis_id: Mapped[int] = mapped_column(ForeignKey("geo_trace_analyses.id"))
    case_id: Mapped[int | None] = mapped_column(ForeignKey("cases.id"), nullable=True)
    origin: Mapped[str] = mapped_column(String(40), default="IP")
    ip: Mapped[str | None] = mapped_column(String(80), nullable=True)
    url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    host: Mapped[str | None] = mapped_column(String(255), nullable=True)
    target_type: Mapped[str] = mapped_column(String(80), default="unknown")
    country: Mapped[str | None] = mapped_column(String(160), nullable=True)
    city: Mapped[str | None] = mapped_column(String(160), nullable=True)
    isp: Mapped[str | None] = mapped_column(String(255), nullable=True)
    org: Mapped[str | None] = mapped_column(String(255), nullable=True)
    asn: Mapped[str | None] = mapped_column(String(255), nullable=True)
    lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    lon: Mapped[float | None] = mapped_column(Float, nullable=True)
    geo_source: Mapped[str | None] = mapped_column(String(80), nullable=True)
    confidence: Mapped[str] = mapped_column(String(40), default="media")
    category: Mapped[str | None] = mapped_column(String(120), nullable=True)
    network_category: Mapped[str | None] = mapped_column(String(120), nullable=True)
    risk: Mapped[str] = mapped_column(String(40), default="bajo")
    score: Mapped[int] = mapped_column(Integer, default=0)
    fraud_probability: Mapped[float] = mapped_column(Float, default=0)
    expected_cost: Mapped[float] = mapped_column(Float, default=0)
    economic_impact: Mapped[float] = mapped_column(Float, default=0)
    indicators: Mapped[str] = mapped_column(Text, default="")
    message: Mapped[str] = mapped_column(Text, default="")

