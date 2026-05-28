from datetime import datetime

from pydantic import BaseModel

from operia.shared.schemas import ORMModel


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
    article_id: int | None = None
    legal_area: str
    norm_reference: str
    source_id: int | None = None
    analysis: str
    verification_status: str = "Fuente pendiente de verificacion"
    confidence_level: str = "medio"
    requires_human_review: bool = True
    decision_status: str = "sugerido"
    analyst_name: str = ""
    analyst_rationale: str = ""
    legal_role: str = ""
    applicability_to_case: str = ""
    probatory_limits: str = ""
    decided_at: str = ""


class LegalMappingRead(LegalMappingCreate, ORMModel):
    id: int
    created_at: datetime


class LegalMappingDecisionCreate(BaseModel):
    case_id: int
    article_id: int
    decision_status: str
    analyst_name: str = ""
    analyst_rationale: str = ""
    legal_role: str = ""
    applicability_to_case: str = ""
    probatory_limits: str = ""
    confidence_level: str = "medio"


class LegalMappingEvidenceCreate(BaseModel):
    case_id: int
    legal_mapping_id: int
    evidence_id: int
    linked_by: str = ""
    link_rationale: str = ""
    legal_element: str = ""
    probatory_strength: str = "medio"
    element_status: str = "pendiente"
    missing_evidence: str = ""
    contradiction_risk: str = "bajo"
    recommended_measure: str = ""


class LegalMappingEvidenceRead(LegalMappingEvidenceCreate, ORMModel):
    id: int
    created_at: datetime


class LegalPrecedentCreate(BaseModel):
    article_id: int | None = None
    title: str
    court_or_authority: str = ""
    decision_date: str = ""
    source: str = ""
    url: str = ""
    summary: str = ""
    applicable_criterion: str = ""
    related_crime_type: str = ""
    verified: bool = False


class LegalPrecedentRead(LegalPrecedentCreate, ORMModel):
    id: int
    created_at: datetime


class LegalDoctrineCreate(BaseModel):
    article_id: int | None = None
    title: str
    author: str = ""
    publication_date: str = ""
    source: str = ""
    url: str = ""
    summary: str = ""
    applicable_criterion: str = ""
    related_crime_type: str = ""
    verified: bool = False


class LegalDoctrineRead(LegalDoctrineCreate, ORMModel):
    id: int
    created_at: datetime
