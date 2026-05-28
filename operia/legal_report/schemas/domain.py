from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class CaseCreate(BaseModel):
    case_code: str
    title: str
    description: str = ""
    responsible: str = ""
    client_or_victim: str = ""
    incident_type: str = "incidente mixto"
    status: str = "abierto"
    jurisdiction: str = "Argentina"
    general_observations: str = ""


class CaseRead(CaseCreate, ORMModel):
    id: int
    created_at: datetime
    updated_at: datetime


class TechnicalDataCreate(BaseModel):
    case_id: int
    data_type: str
    description: str
    source: str = ""
    loaded_by: str = ""
    associated_file: str | None = None
    value: str = ""
    observations: str = ""
    initial_relevance: str = "medio"
    status: str = "pendiente"


class TechnicalDataRead(TechnicalDataCreate, ORMModel):
    id: int
    obtained_at: datetime
    created_at: datetime
    updated_at: datetime


class EvidenceCreate(BaseModel):
    case_id: int
    technical_data_id: int | None = None
    evidence_type: str = "documento digital"
    description: str
    source: str = ""
    responsible: str = ""
    custodian: str = ""
    sha256_hash: str = ""
    md5_hash: str | None = None
    file_location: str | None = None
    preservation_method: str = ""
    tool_used: str = ""
    evidence_nature: str = "copia forense"
    was_altered: bool = False
    alteration_justification: str = ""
    custody_observations: str = ""
    integrity_status: str = "pendiente de validacion"
    confidence_level: str = "medio"


class EvidenceRead(EvidenceCreate, ORMModel):
    id: int
    acquired_at: datetime
    created_at: datetime
    updated_at: datetime


class CustodyActionCreate(BaseModel):
    case_id: int
    evidence_id: int | None = None
    user_responsible: str = ""
    user_role: str = ""
    action_type: str = "carga"
    detailed_description: str
    tool_used: str = ""
    command_or_procedure: str = ""
    result_obtained: str = ""
    altered_evidence: bool = False
    hash_before: str = ""
    hash_after: str = ""
    validated_by: str = ""
    legal_observations: str = ""
    status: str = "registrada"


class CustodyActionRead(CustodyActionCreate, ORMModel):
    id: int
    action_at: datetime
    created_at: datetime


class FindingCreate(BaseModel):
    case_id: int
    technical_data_id: int | None = None
    evidence_id: int | None = None
    title: str
    technical_finding: str
    explanation: str = ""
    confidence_level: str = "medio"
    weaknesses_or_limitations: str = ""
    tools_used: str = ""
    supporting_evidence: str = ""
    preliminary_legal_relevance: str = ""
    status: str = "borrador"


class FindingRead(FindingCreate, ORMModel):
    id: int
    created_at: datetime
    updated_at: datetime


class HypothesisCreate(BaseModel):
    case_id: int
    title: str
    description: str
    finding_ids: str = ""
    evidence_ids: str = ""
    support_degree: str = "medio"
    alternative_hypotheses: str = ""
    error_risks: str = ""
    facts_to_prove: str = ""
    provisional_conclusion: str = ""
    status: str = "abierta"


class HypothesisRead(HypothesisCreate, ORMModel):
    id: int
    created_at: datetime
    updated_at: datetime


class LegalSourceCreate(BaseModel):
    title: str
    source_type: str = "norma"
    citation: str = "Fuente pendiente de verificacion"
    url: str = ""
    content: str = ""
    verified: bool = False


class LegalSourceRead(LegalSourceCreate, ORMModel):
    id: int
    created_at: datetime


class LegalMappingCreate(BaseModel):
    case_id: int
    finding_id: int | None = None
    hypothesis_id: int | None = None
    legal_area: str
    norm_reference: str
    source_id: int | None = None
    analysis: str
    verification_status: str = "Fuente pendiente de verificacion"


class LegalMappingRead(LegalMappingCreate, ORMModel):
    id: int
    created_at: datetime


class DamageItemCreate(BaseModel):
    case_id: int
    concept: str
    amount: float = 0
    currency: str = "ARS"
    base_date: str = ""
    value_source: str = ""
    formula_used: str = ""
    supporting_evidence: str = ""
    certainty_level: str = "medio"
    observations: str = ""


class DamageItemRead(DamageItemCreate, ORMModel):
    id: int
    created_at: datetime
    updated_at: datetime


class ReportRead(ORMModel):
    id: int
    case_id: int
    title: str
    version: str
    author: str
    status: str
    template_used: str
    observations: str
    markdown_content: str
    review_score: int
    created_at: datetime
    updated_at: datetime


class ReportUpdate(BaseModel):
    title: str | None = None
    markdown_content: str | None = None
    status: str | None = None
    observations: str | None = None
    author: str | None = None


class ReviewResult(BaseModel):
    score: int
    status: str
    critical_errors: list[str]
    warnings: list[str]
    suggestions: list[str]
    incomplete_sections: list[str]
    unused_evidence: list[str] = []
    unsupported_conclusions: list[str] = []
    drafting_recommendations: list[str] = []


class CaseEvaluationResult(BaseModel):
    overall_score: int
    status: str
    evidence_score: int
    finding_score: int
    hypothesis_score: int
    legal_score: int
    economic_score: int
    custody_score: int
    report_score: int
    case_theory: str
    legal_justification: str
    dogmatic_assessment: str
    procedural_assessment: str
    evidentiary_assessment: str
    economic_assessment: str
    strengths: list[str]
    weaknesses: list[str]
    next_steps: list[str]
    defensible_conclusion: str
    legal_classification: list[str]
    competence: list[str]


class PresentationRead(ORMModel):
    id: int
    case_id: int
    source_report_id: int | None
    title: str
    presentation_type: str
    version: str
    status: str
    author: str
    selected_fragments: str
    review_score: int
    exported_file: str
    created_at: datetime
    updated_at: datetime


class PresentationSlideRead(ORMModel):
    id: int
    presentation_id: int
    slide_number: int
    title: str
    content_type: str
    text: str
    speaker_notes: str
    confidentiality_level: str


class PresentationSlideUpdate(BaseModel):
    slide_number: int | None = None
    title: str | None = None
    content_type: str | None = None
    text: str | None = None
    speaker_notes: str | None = None
    confidentiality_level: str | None = None


class PresentationReviewResult(BaseModel):
    score: int
    status: str = ""
    clarity: int
    evidentiary_strength: int
    narrative_coherence: int
    legal_solidity: int
    visual_quality: int
    critical_errors: list[str] = []
    warnings: list[str] = []
    oral_exposure_risks: list[str]
    recommendations: list[str]
    page_recommendations: list[str] = []


class DashboardRead(BaseModel):
    metrics: dict[str, Any]
    recent_cases: list[CaseRead]
    recent_actions: list[CustodyActionRead]

