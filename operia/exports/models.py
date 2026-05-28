from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from operia.core.database import Base
from operia.shared.models import TimestampMixin


class ExportManifest(Base, TimestampMixin):
    __tablename__ = "export_manifests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    organization_id: Mapped[int | None] = mapped_column(ForeignKey("organizations.id"), nullable=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    case_id: Mapped[int | None] = mapped_column(ForeignKey("cases.id"), nullable=True)
    report_id: Mapped[int | None] = mapped_column(ForeignKey("reports.id"), nullable=True)
    export_type: Mapped[str] = mapped_column(String(80))
    filename: Mapped[str] = mapped_column(String(255))
    file_path: Mapped[str] = mapped_column(String(500))
    sha256_hash: Mapped[str] = mapped_column(String(128), default="")
    md5_hash: Mapped[str] = mapped_column(String(64), default="")
    manifest_path: Mapped[str] = mapped_column(String(500), default="")
    status: Mapped[str] = mapped_column(String(80), default="generated")
    generated_by: Mapped[str] = mapped_column(String(160), default="")
    metadata_json: Mapped[str] = mapped_column(Text, default="{}")

