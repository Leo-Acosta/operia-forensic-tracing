from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from operia.core.database import Base
from operia.shared.models import TimestampMixin


class Report(Base, TimestampMixin):
    __tablename__ = "reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    organization_id: Mapped[int | None] = mapped_column(ForeignKey("organizations.id"), nullable=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("cases.id"))
    title: Mapped[str] = mapped_column(String(255))
    version: Mapped[str] = mapped_column(String(40), default="1.0")
    author: Mapped[str] = mapped_column(String(160), default="")
    status: Mapped[str] = mapped_column(String(80), default="borrador")
    template_used: Mapped[str] = mapped_column(String(160), default="Informe integral forense-juridico")
    observations: Mapped[str] = mapped_column(Text, default="")
    markdown_content: Mapped[str] = mapped_column(Text, default="")
    review_score: Mapped[int] = mapped_column(Integer, default=0)

    case: Mapped["Case"] = relationship(back_populates="reports")
    sections: Mapped[list["ReportSection"]] = relationship(back_populates="report", cascade="all, delete-orphan")
    versions: Mapped[list["ReportVersion"]] = relationship(back_populates="report", cascade="all, delete-orphan")


class ReportSection(Base, TimestampMixin):
    __tablename__ = "report_sections"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    organization_id: Mapped[int | None] = mapped_column(ForeignKey("organizations.id"), nullable=True)
    report_id: Mapped[int] = mapped_column(ForeignKey("reports.id"))
    order_index: Mapped[int] = mapped_column(Integer)
    title: Mapped[str] = mapped_column(String(255))
    content: Mapped[str] = mapped_column(Text, default="")
    section_type: Mapped[str] = mapped_column(String(100), default="texto")

    report: Mapped[Report] = relationship(back_populates="sections")


class ReportVersion(Base, TimestampMixin):
    __tablename__ = "report_versions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    organization_id: Mapped[int | None] = mapped_column(ForeignKey("organizations.id"), nullable=True)
    report_id: Mapped[int] = mapped_column(ForeignKey("reports.id"))
    version_number: Mapped[str] = mapped_column(String(40))
    user: Mapped[str] = mapped_column(String(160), default="")
    change_summary: Mapped[str] = mapped_column(Text, default="")
    review_score: Mapped[int] = mapped_column(Integer, default=0)
    observations: Mapped[str] = mapped_column(Text, default="")
    markdown_snapshot: Mapped[str] = mapped_column(Text, default="")

    report: Mapped[Report] = relationship(back_populates="versions")


class ReportReview(Base, TimestampMixin):
    __tablename__ = "report_reviews"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    organization_id: Mapped[int | None] = mapped_column(ForeignKey("organizations.id"), nullable=True)
    report_id: Mapped[int] = mapped_column(ForeignKey("reports.id"))
    score: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(120))
    critical_errors: Mapped[str] = mapped_column(Text, default="")
    warnings: Mapped[str] = mapped_column(Text, default="")
    suggestions: Mapped[str] = mapped_column(Text, default="")
    incomplete_sections: Mapped[str] = mapped_column(Text, default="")
    unsupported_conclusions: Mapped[str] = mapped_column(Text, default="")


class Template(Base, TimestampMixin):
    __tablename__ = "templates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    organization_id: Mapped[int | None] = mapped_column(ForeignKey("organizations.id"), nullable=True)
    name: Mapped[str] = mapped_column(String(255), unique=True)
    template_type: Mapped[str] = mapped_column(String(100), default="informe")
    content: Mapped[str] = mapped_column(Text, default="")
    editable: Mapped[bool] = mapped_column(Boolean, default=True)


class Presentation(Base, TimestampMixin):
    __tablename__ = "presentations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    organization_id: Mapped[int | None] = mapped_column(ForeignKey("organizations.id"), nullable=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("cases.id"))
    source_report_id: Mapped[int | None] = mapped_column(ForeignKey("reports.id"))
    title: Mapped[str] = mapped_column(String(255))
    presentation_type: Mapped[str] = mapped_column(String(160), default="Presentacion ejecutiva breve")
    version: Mapped[str] = mapped_column(String(40), default="1.0")
    status: Mapped[str] = mapped_column(String(80), default="borrador")
    author: Mapped[str] = mapped_column(String(160), default="")
    selected_fragments: Mapped[str] = mapped_column(Text, default="")
    review_score: Mapped[int] = mapped_column(Integer, default=0)
    exported_file: Mapped[str] = mapped_column(String(500), default="")

    case: Mapped["Case"] = relationship(back_populates="presentations")
    slides: Mapped[list["PresentationSlide"]] = relationship(back_populates="presentation", cascade="all, delete-orphan")


class PresentationSlide(Base, TimestampMixin):
    __tablename__ = "presentation_slides"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    organization_id: Mapped[int | None] = mapped_column(ForeignKey("organizations.id"), nullable=True)
    presentation_id: Mapped[int] = mapped_column(ForeignKey("presentations.id"))
    slide_number: Mapped[int] = mapped_column(Integer)
    title: Mapped[str] = mapped_column(String(255))
    content_type: Mapped[str] = mapped_column(String(100), default="texto")
    text: Mapped[str] = mapped_column(Text, default="")
    evidence_id: Mapped[int | None] = mapped_column(ForeignKey("evidence.id"))
    finding_id: Mapped[int | None] = mapped_column(ForeignKey("findings.id"))
    chart_or_table: Mapped[str] = mapped_column(Text, default="")
    speaker_notes: Mapped[str] = mapped_column(Text, default="")
    confidentiality_level: Mapped[str] = mapped_column(String(80), default="interno")

    presentation: Mapped[Presentation] = relationship(back_populates="slides")


class PresentationVersion(Base, TimestampMixin):
    __tablename__ = "presentation_versions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    organization_id: Mapped[int | None] = mapped_column(ForeignKey("organizations.id"), nullable=True)
    presentation_id: Mapped[int] = mapped_column(ForeignKey("presentations.id"))
    version_number: Mapped[str] = mapped_column(String(40))
    user: Mapped[str] = mapped_column(String(160), default="")
    change_summary: Mapped[str] = mapped_column(Text, default="")
    score: Mapped[int] = mapped_column(Integer, default=0)


class PresentationReview(Base, TimestampMixin):
    __tablename__ = "presentation_reviews"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    organization_id: Mapped[int | None] = mapped_column(ForeignKey("organizations.id"), nullable=True)
    presentation_id: Mapped[int] = mapped_column(ForeignKey("presentations.id"))
    score: Mapped[int] = mapped_column(Integer, default=0)
    clarity: Mapped[int] = mapped_column(Integer, default=0)
    evidentiary_strength: Mapped[int] = mapped_column(Integer, default=0)
    narrative_coherence: Mapped[int] = mapped_column(Integer, default=0)
    legal_solidity: Mapped[int] = mapped_column(Integer, default=0)
    visual_quality: Mapped[int] = mapped_column(Integer, default=0)
    oral_exposure_risks: Mapped[str] = mapped_column(Text, default="")
    recommendations: Mapped[str] = mapped_column(Text, default="")


class PresentationFragment(Base, TimestampMixin):
    __tablename__ = "presentation_fragments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    organization_id: Mapped[int | None] = mapped_column(ForeignKey("organizations.id"), nullable=True)
    presentation_id: Mapped[int] = mapped_column(ForeignKey("presentations.id"))
    source_report_section: Mapped[str] = mapped_column(String(255), default="")
    fragment_text: Mapped[str] = mapped_column(Text)
    accepted: Mapped[bool] = mapped_column(Boolean, default=True)
    sensitive: Mapped[bool] = mapped_column(Boolean, default=False)
    public_version_text: Mapped[str] = mapped_column(Text, default="")

