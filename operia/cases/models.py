from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from operia.core.database import Base
from operia.shared.models import TimestampMixin
from operia.shared.time import utcnow


class Case(Base, TimestampMixin):
    __tablename__ = "cases"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    organization_id: Mapped[int | None] = mapped_column(ForeignKey("organizations.id"), nullable=True)
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
    participants: Mapped[list["CaseParticipant"]] = relationship(back_populates="case", cascade="all, delete-orphan")
    damage_items: Mapped[list["DamageItem"]] = relationship(back_populates="case", cascade="all, delete-orphan")
    reports: Mapped[list["Report"]] = relationship(back_populates="case", cascade="all, delete-orphan")
    presentations: Mapped[list["Presentation"]] = relationship(back_populates="case", cascade="all, delete-orphan")
    rubric_evaluations: Mapped[list["RubricEvaluation"]] = relationship(back_populates="case", cascade="all, delete-orphan")
    deepfake_analyses: Mapped[list["DeepfakeAnalysis"]] = relationship(back_populates="case", cascade="all, delete-orphan")
    blockchain_transactions: Mapped[list["BlockchainTransaction"]] = relationship(back_populates="case", cascade="all, delete-orphan")


class CaseParticipant(Base, TimestampMixin):
    __tablename__ = "case_participants"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    organization_id: Mapped[int | None] = mapped_column(ForeignKey("organizations.id"), nullable=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("cases.id"))
    participant_type: Mapped[str] = mapped_column(String(120), default="tercero_relevante")
    person_type: Mapped[str] = mapped_column(String(80), default="persona_fisica")
    display_name: Mapped[str] = mapped_column(String(255))
    document_type: Mapped[str] = mapped_column(String(80), default="")
    document_number: Mapped[str] = mapped_column(String(120), default="")
    tax_id: Mapped[str] = mapped_column(String(120), default="")
    email: Mapped[str] = mapped_column(String(255), default="")
    phone: Mapped[str] = mapped_column(String(120), default="")
    address: Mapped[str] = mapped_column(String(500), default="")
    role_description: Mapped[str] = mapped_column(Text, default="")
    relationship_to_case: Mapped[str] = mapped_column(Text, default="")
    notes: Mapped[str] = mapped_column(Text, default="")
    sensitivity_level: Mapped[str] = mapped_column(String(80), default="reservado")

    case: Mapped[Case] = relationship(back_populates="participants")


class TechnicalData(Base, TimestampMixin):
    __tablename__ = "technical_data"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    organization_id: Mapped[int | None] = mapped_column(ForeignKey("organizations.id"), nullable=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("cases.id"))
    data_type: Mapped[str] = mapped_column(String(120))
    description: Mapped[str] = mapped_column(Text)
    source: Mapped[str] = mapped_column(String(255), default="")
    obtained_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    loaded_by: Mapped[str] = mapped_column(String(160), default="")
    associated_file: Mapped[str | None] = mapped_column(String(500))
    value: Mapped[str] = mapped_column(Text, default="")
    observations: Mapped[str] = mapped_column(Text, default="")
    initial_relevance: Mapped[str] = mapped_column(String(40), default="medio")
    status: Mapped[str] = mapped_column(String(80), default="pendiente")

    case: Mapped[Case] = relationship(back_populates="technical_data")
    evidence_items: Mapped[list["Evidence"]] = relationship(back_populates="technical_data")


class Finding(Base, TimestampMixin):
    __tablename__ = "findings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    organization_id: Mapped[int | None] = mapped_column(ForeignKey("organizations.id"), nullable=True)
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
    organization_id: Mapped[int | None] = mapped_column(ForeignKey("organizations.id"), nullable=True)
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


class DamageItem(Base, TimestampMixin):
    __tablename__ = "damage_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    organization_id: Mapped[int | None] = mapped_column(ForeignKey("organizations.id"), nullable=True)
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
    organization_id: Mapped[int | None] = mapped_column(ForeignKey("organizations.id"), nullable=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("cases.id"))
    methodology: Mapped[str] = mapped_column(String(160))
    total_amount: Mapped[float] = mapped_column(Float, default=0)
    currency: Mapped[str] = mapped_column(String(20), default="ARS")
    formula_summary: Mapped[str] = mapped_column(Text, default="")
    certainty_level: Mapped[str] = mapped_column(String(40), default="medio")
