from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from operia.core.database import Base


def now() -> datetime:
    return datetime.utcnow()


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now, onupdate=now)


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(160))
    email: Mapped[str | None] = mapped_column(String(255), unique=True)
    role: Mapped[str] = mapped_column(String(80), default="analista")


class Case(Base, TimestampMixin):
    __tablename__ = "cases"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    case_code: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text, default="")
    responsible: Mapped[str] = mapped_column(String(160), default="")
    client_or_victim: Mapped[str] = mapped_column(String(160), default="")
    incident_type: Mapped[str] = mapped_column(String(120), default="incidente mixto")
    status: Mapped[str] = mapped_column(String(80), default="abierto")
    jurisdiction: Mapped[str] = mapped_column(String(160), default="Argentina")
    general_observations: Mapped[str] = mapped_column(Text, default="")

    technical_data: Mapped[list["TechnicalData"]] = relationship(back_populates="case", cascade="all, delete-orphan")
    evidence: Mapped[list["Evidence"]] = relationship(back_populates="case", cascade="all, delete-orphan")
    actions: Mapped[list["ChainOfCustodyAction"]] = relationship(back_populates="case", cascade="all, delete-orphan")
    findings: Mapped[list["Finding"]] = relationship(back_populates="case", cascade="all, delete-orphan")
    hypotheses: Mapped[list["Hypothesis"]] = relationship(back_populates="case", cascade="all, delete-orphan")
    legal_mappings: Mapped[list["LegalMapping"]] = relationship(back_populates="case", cascade="all, delete-orphan")
    damage_items: Mapped[list["DamageItem"]] = relationship(back_populates="case", cascade="all, delete-orphan")
    reports: Mapped[list["Report"]] = relationship(back_populates="case", cascade="all, delete-orphan")
    presentations: Mapped[list["Presentation"]] = relationship(back_populates="case", cascade="all, delete-orphan")


class TechnicalData(Base, TimestampMixin):
    __tablename__ = "technical_data"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("cases.id"))
    data_type: Mapped[str] = mapped_column(String(120))
    description: Mapped[str] = mapped_column(Text)
    source: Mapped[str] = mapped_column(String(255), default="")
    obtained_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    loaded_by: Mapped[str] = mapped_column(String(160), default="")
    associated_file: Mapped[str | None] = mapped_column(String(500))
    value: Mapped[str] = mapped_column(Text, default="")
    observations: Mapped[str] = mapped_column(Text, default="")
    initial_relevance: Mapped[str] = mapped_column(String(40), default="medio")
    status: Mapped[str] = mapped_column(String(80), default="pendiente")

    case: Mapped[Case] = relationship(back_populates="technical_data")
    evidence_items: Mapped[list["Evidence"]] = relationship(back_populates="technical_data")


class Evidence(Base, TimestampMixin):
    __tablename__ = "evidence"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("cases.id"))
    technical_data_id: Mapped[int | None] = mapped_column(ForeignKey("technical_data.id"))
    evidence_type: Mapped[str] = mapped_column(String(120), default="documento digital")
    description: Mapped[str] = mapped_column(Text)
    source: Mapped[str] = mapped_column(String(255), default="")
    acquired_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    responsible: Mapped[str] = mapped_column(String(160), default="")
    custodian: Mapped[str] = mapped_column(String(160), default="")
    sha256_hash: Mapped[str] = mapped_column(String(128), default="")
    md5_hash: Mapped[str | None] = mapped_column(String(64))
    file_location: Mapped[str | None] = mapped_column(String(500))
    preservation_method: Mapped[str] = mapped_column(Text, default="")
    tool_used: Mapped[str] = mapped_column(String(255), default="")
    evidence_nature: Mapped[str] = mapped_column(String(80), default="copia forense")
    was_altered: Mapped[bool] = mapped_column(Boolean, default=False)
    alteration_justification: Mapped[str] = mapped_column(Text, default="")
    custody_observations: Mapped[str] = mapped_column(Text, default="")
    integrity_status: Mapped[str] = mapped_column(String(80), default="pendiente de validacion")
    confidence_level: Mapped[str] = mapped_column(String(40), default="medio")

    case: Mapped[Case] = relationship(back_populates="evidence")
    technical_data: Mapped[TechnicalData | None] = relationship(back_populates="evidence_items")
    actions: Mapped[list["ChainOfCustodyAction"]] = relationship(back_populates="evidence")


class ChainOfCustodyAction(Base, TimestampMixin):
    __tablename__ = "chain_of_custody_actions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("cases.id"))
    evidence_id: Mapped[int | None] = mapped_column(ForeignKey("evidence.id"))
    action_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    user_responsible: Mapped[str] = mapped_column(String(160), default="")
    user_role: Mapped[str] = mapped_column(String(80), default="")
    action_type: Mapped[str] = mapped_column(String(100), default="carga")
    detailed_description: Mapped[str] = mapped_column(Text)
    tool_used: Mapped[str] = mapped_column(String(255), default="")
    command_or_procedure: Mapped[str] = mapped_column(Text, default="")
    result_obtained: Mapped[str] = mapped_column(Text, default="")
    altered_evidence: Mapped[bool] = mapped_column(Boolean, default=False)
    hash_before: Mapped[str] = mapped_column(String(128), default="")
    hash_after: Mapped[str] = mapped_column(String(128), default="")
    validated_by: Mapped[str] = mapped_column(String(160), default="")
    legal_observations: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(80), default="registrada")

    case: Mapped[Case] = relationship(back_populates="actions")
    evidence: Mapped[Evidence | None] = relationship(back_populates="actions")


class Finding(Base, TimestampMixin):
    __tablename__ = "findings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("cases.id"))
    technical_data_id: Mapped[int | None] = mapped_column(ForeignKey("technical_data.id"))
    evidence_id: Mapped[int | None] = mapped_column(ForeignKey("evidence.id"))
    title: Mapped[str] = mapped_column(String(255))
    technical_finding: Mapped[str] = mapped_column(Text)
    explanation: Mapped[str] = mapped_column(Text, default="")
    confidence_level: Mapped[str] = mapped_column(String(40), default="medio")
    weaknesses_or_limitations: Mapped[str] = mapped_column(Text, default="")
    tools_used: Mapped[str] = mapped_column(Text, default="")
    supporting_evidence: Mapped[str] = mapped_column(Text, default="")
    preliminary_legal_relevance: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(80), default="borrador")

    case: Mapped[Case] = relationship(back_populates="findings")


class Hypothesis(Base, TimestampMixin):
    __tablename__ = "hypotheses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("cases.id"))
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text)
    finding_ids: Mapped[str] = mapped_column(String(255), default="")
    evidence_ids: Mapped[str] = mapped_column(String(255), default="")
    support_degree: Mapped[str] = mapped_column(String(40), default="medio")
    alternative_hypotheses: Mapped[str] = mapped_column(Text, default="")
    error_risks: Mapped[str] = mapped_column(Text, default="")
    facts_to_prove: Mapped[str] = mapped_column(Text, default="")
    provisional_conclusion: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(80), default="abierta")

    case: Mapped[Case] = relationship(back_populates="hypotheses")


class LegalSource(Base, TimestampMixin):
    __tablename__ = "legal_sources"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(255))
    source_type: Mapped[str] = mapped_column(String(100), default="norma")
    citation: Mapped[str] = mapped_column(String(255), default="Fuente pendiente de verificacion")
    url: Mapped[str] = mapped_column(String(500), default="")
    content: Mapped[str] = mapped_column(Text, default="")
    verified: Mapped[bool] = mapped_column(Boolean, default=False)


class LegalMapping(Base, TimestampMixin):
    __tablename__ = "legal_mappings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("cases.id"))
    finding_id: Mapped[int | None] = mapped_column(ForeignKey("findings.id"))
    hypothesis_id: Mapped[int | None] = mapped_column(ForeignKey("hypotheses.id"))
    legal_area: Mapped[str] = mapped_column(String(160))
    norm_reference: Mapped[str] = mapped_column(String(255))
    source_id: Mapped[int | None] = mapped_column(ForeignKey("legal_sources.id"))
    analysis: Mapped[str] = mapped_column(Text)
    verification_status: Mapped[str] = mapped_column(String(120), default="Fuente pendiente de verificacion")

    case: Mapped[Case] = relationship(back_populates="legal_mappings")


class DamageItem(Base, TimestampMixin):
    __tablename__ = "damage_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("cases.id"))
    concept: Mapped[str] = mapped_column(String(160))
    amount: Mapped[float] = mapped_column(Float, default=0)
    currency: Mapped[str] = mapped_column(String(20), default="ARS")
    base_date: Mapped[str] = mapped_column(String(40), default="")
    value_source: Mapped[str] = mapped_column(String(255), default="")
    formula_used: Mapped[str] = mapped_column(String(255), default="")
    supporting_evidence: Mapped[str] = mapped_column(Text, default="")
    certainty_level: Mapped[str] = mapped_column(String(40), default="medio")
    observations: Mapped[str] = mapped_column(Text, default="")

    case: Mapped[Case] = relationship(back_populates="damage_items")


class DamageCalculation(Base, TimestampMixin):
    __tablename__ = "damage_calculations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("cases.id"))
    methodology: Mapped[str] = mapped_column(String(160))
    total_amount: Mapped[float] = mapped_column(Float, default=0)
    currency: Mapped[str] = mapped_column(String(20), default="ARS")
    formula_summary: Mapped[str] = mapped_column(Text, default="")
    certainty_level: Mapped[str] = mapped_column(String(40), default="medio")


class Report(Base, TimestampMixin):
    __tablename__ = "reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("cases.id"))
    title: Mapped[str] = mapped_column(String(255))
    version: Mapped[str] = mapped_column(String(40), default="1.0")
    author: Mapped[str] = mapped_column(String(160), default="")
    status: Mapped[str] = mapped_column(String(80), default="borrador")
    template_used: Mapped[str] = mapped_column(String(160), default="Informe integral forense-juridico")
    observations: Mapped[str] = mapped_column(Text, default="")
    markdown_content: Mapped[str] = mapped_column(Text, default="")
    review_score: Mapped[int] = mapped_column(Integer, default=0)

    case: Mapped[Case] = relationship(back_populates="reports")
    sections: Mapped[list["ReportSection"]] = relationship(back_populates="report", cascade="all, delete-orphan")
    versions: Mapped[list["ReportVersion"]] = relationship(back_populates="report", cascade="all, delete-orphan")


class ReportSection(Base, TimestampMixin):
    __tablename__ = "report_sections"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    report_id: Mapped[int] = mapped_column(ForeignKey("reports.id"))
    order_index: Mapped[int] = mapped_column(Integer)
    title: Mapped[str] = mapped_column(String(255))
    content: Mapped[str] = mapped_column(Text, default="")
    section_type: Mapped[str] = mapped_column(String(100), default="texto")

    report: Mapped[Report] = relationship(back_populates="sections")


class ReportVersion(Base, TimestampMixin):
    __tablename__ = "report_versions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
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
    name: Mapped[str] = mapped_column(String(255), unique=True)
    template_type: Mapped[str] = mapped_column(String(100), default="informe")
    content: Mapped[str] = mapped_column(Text, default="")
    editable: Mapped[bool] = mapped_column(Boolean, default=True)


class Attachment(Base, TimestampMixin):
    __tablename__ = "attachments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("cases.id"))
    file_name: Mapped[str] = mapped_column(String(255))
    file_path: Mapped[str] = mapped_column(String(500))
    sha256_hash: Mapped[str] = mapped_column(String(128), default="")
    mime_type: Mapped[str] = mapped_column(String(120), default="")


class Presentation(Base, TimestampMixin):
    __tablename__ = "presentations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
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

    case: Mapped[Case] = relationship(back_populates="presentations")
    slides: Mapped[list["PresentationSlide"]] = relationship(back_populates="presentation", cascade="all, delete-orphan")


class PresentationSlide(Base, TimestampMixin):
    __tablename__ = "presentation_slides"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
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
    presentation_id: Mapped[int] = mapped_column(ForeignKey("presentations.id"))
    version_number: Mapped[str] = mapped_column(String(40))
    user: Mapped[str] = mapped_column(String(160), default="")
    change_summary: Mapped[str] = mapped_column(Text, default="")
    score: Mapped[int] = mapped_column(Integer, default=0)


class PresentationReview(Base, TimestampMixin):
    __tablename__ = "presentation_reviews"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
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
    presentation_id: Mapped[int] = mapped_column(ForeignKey("presentations.id"))
    source_report_section: Mapped[str] = mapped_column(String(255), default="")
    fragment_text: Mapped[str] = mapped_column(Text)
    accepted: Mapped[bool] = mapped_column(Boolean, default=True)
    sensitive: Mapped[bool] = mapped_column(Boolean, default=False)
    public_version_text: Mapped[str] = mapped_column(Text, default="")

