from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from operia.core.database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class LocationReference(Base, TimestampMixin):
    __tablename__ = "geo_proximity_location_references"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), unique=True)
    category: Mapped[str] = mapped_column(String(120), default="reference")
    lat: Mapped[float] = mapped_column(Float)
    lon: Mapped[float] = mapped_column(Float)
    source: Mapped[str] = mapped_column(String(160), default="geo-apple-demo")


class GeoProximityQuery(Base, TimestampMixin):
    __tablename__ = "geo_proximity_queries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    case_id: Mapped[int | None] = mapped_column(ForeignKey("cases.id"), nullable=True)
    lat: Mapped[float] = mapped_column(Float)
    lon: Mapped[float] = mapped_column(Float)
    nearest_location_id: Mapped[int | None] = mapped_column(ForeignKey("geo_proximity_location_references.id"), nullable=True)
    nearest_name: Mapped[str] = mapped_column(String(255), default="")
    distance_km: Mapped[float] = mapped_column(Float, default=0)
    status: Mapped[str] = mapped_column(String(80), default="completed")

