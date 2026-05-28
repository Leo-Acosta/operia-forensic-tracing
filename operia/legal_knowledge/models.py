from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from operia.core.database import Base
from operia.shared.models import TimestampMixin


class LegalSource(Base, TimestampMixin):
    __tablename__ = "legal_sources"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    organization_id: Mapped[int | None] = mapped_column(ForeignKey("organizations.id"), nullable=True)
    title: Mapped[str] = mapped_column(String(255))
    source_type: Mapped[str] = mapped_column(String(100), default="norma")
    citation: Mapped[str] = mapped_column(String(255), default="Fuente pendiente de verificacion")
    url: Mapped[str] = mapped_column(String(500), default="")
    content: Mapped[str] = mapped_column(Text, default="")
    verified: Mapped[bool] = mapped_column(Boolean, default=False)


class LegalArticle(Base, TimestampMixin):
    __tablename__ = "legal_articles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    organization_id: Mapped[int | None] = mapped_column(ForeignKey("organizations.id"), nullable=True)
    source_id: Mapped[int | None] = mapped_column(ForeignKey("legal_sources.id"), nullable=True)
    code: Mapped[str] = mapped_column(String(80), index=True)
    title: Mapped[str] = mapped_column(String(255), default="")
    article_number: Mapped[str] = mapped_column(String(80), default="")
    subsection: Mapped[str] = mapped_column(String(80), default="")
    text: Mapped[str] = mapped_column(Text, default="")
    objective_elements: Mapped[str] = mapped_column(Text, default="")
    subjective_elements: Mapped[str] = mapped_column(Text, default="")
    evidentiary_requirements: Mapped[str] = mapped_column(Text, default="")
    official_url: Mapped[str] = mapped_column(String(500), default="")
    version_label: Mapped[str] = mapped_column(String(120), default="")
    last_checked_at: Mapped[str] = mapped_column(String(80), default="")
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class LegalMapping(Base, TimestampMixin):
    __tablename__ = "legal_mappings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    organization_id: Mapped[int | None] = mapped_column(ForeignKey("organizations.id"), nullable=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("cases.id"))
    finding_id: Mapped[int | None] = mapped_column(ForeignKey("findings.id"))
    hypothesis_id: Mapped[int | None] = mapped_column(ForeignKey("hypotheses.id"))
    legal_area: Mapped[str] = mapped_column(String(160))
    norm_reference: Mapped[str] = mapped_column(String(255))
    source_id: Mapped[int | None] = mapped_column(ForeignKey("legal_sources.id"))
    article_id: Mapped[int | None] = mapped_column(ForeignKey("legal_articles.id"), nullable=True)
    analysis: Mapped[str] = mapped_column(Text)
    verification_status: Mapped[str] = mapped_column(String(120), default="Fuente pendiente de verificacion")
    confidence_level: Mapped[str] = mapped_column(String(40), default="medio")
    requires_human_review: Mapped[bool] = mapped_column(Boolean, default=True)

    case: Mapped["Case"] = relationship(back_populates="legal_mappings")


class LegalCitation(Base, TimestampMixin):
    __tablename__ = "legal_citations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    organization_id: Mapped[int | None] = mapped_column(ForeignKey("organizations.id"), nullable=True)
    source_id: Mapped[int | None] = mapped_column(ForeignKey("legal_sources.id"), nullable=True)
    article_id: Mapped[int | None] = mapped_column(ForeignKey("legal_articles.id"), nullable=True)
    case_id: Mapped[int | None] = mapped_column(ForeignKey("cases.id"), nullable=True)
    report_id: Mapped[int | None] = mapped_column(ForeignKey("reports.id"), nullable=True)
    citation_text: Mapped[str] = mapped_column(Text)
    source_url: Mapped[str] = mapped_column(String(500), default="")
    verified: Mapped[bool] = mapped_column(Boolean, default=False)


class LegalEvaluation(Base, TimestampMixin):
    __tablename__ = "legal_evaluations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    organization_id: Mapped[int | None] = mapped_column(ForeignKey("organizations.id"), nullable=True)
    case_id: Mapped[int | None] = mapped_column(ForeignKey("cases.id"), nullable=True)
    report_id: Mapped[int | None] = mapped_column(ForeignKey("reports.id"), nullable=True)
    evaluator: Mapped[str] = mapped_column(String(160), default="OPERIA")
    score: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(120), default="requiere revision humana")
    rubric: Mapped[str] = mapped_column(Text, default="")
    strengths: Mapped[str] = mapped_column(Text, default="")
    weaknesses: Mapped[str] = mapped_column(Text, default="")
    conclusion: Mapped[str] = mapped_column(Text, default="")


class LegalPrecedent(Base, TimestampMixin):
    __tablename__ = "legal_precedents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    organization_id: Mapped[int | None] = mapped_column(ForeignKey("organizations.id"), nullable=True)
    article_id: Mapped[int | None] = mapped_column(ForeignKey("legal_articles.id"), nullable=True)
    title: Mapped[str] = mapped_column(String(255))
    court_or_authority: Mapped[str] = mapped_column(String(255), default="")
    decision_date: Mapped[str] = mapped_column(String(80), default="")
    source: Mapped[str] = mapped_column(String(255), default="")
    url: Mapped[str] = mapped_column(String(500), default="")
    summary: Mapped[str] = mapped_column(Text, default="")
    applicable_criterion: Mapped[str] = mapped_column(Text, default="")
    related_crime_type: Mapped[str] = mapped_column(String(160), default="")
    verified: Mapped[bool] = mapped_column(Boolean, default=False)


class LegalDoctrine(Base, TimestampMixin):
    __tablename__ = "legal_doctrine"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    organization_id: Mapped[int | None] = mapped_column(ForeignKey("organizations.id"), nullable=True)
    article_id: Mapped[int | None] = mapped_column(ForeignKey("legal_articles.id"), nullable=True)
    title: Mapped[str] = mapped_column(String(255))
    author: Mapped[str] = mapped_column(String(255), default="")
    publication_date: Mapped[str] = mapped_column(String(80), default="")
    source: Mapped[str] = mapped_column(String(255), default="")
    url: Mapped[str] = mapped_column(String(500), default="")
    summary: Mapped[str] = mapped_column(Text, default="")
    applicable_criterion: Mapped[str] = mapped_column(Text, default="")
    related_crime_type: Mapped[str] = mapped_column(String(160), default="")
    verified: Mapped[bool] = mapped_column(Boolean, default=False)
