from datetime import datetime

from pydantic import BaseModel

from operia.shared.schemas import ORMModel


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


class CaseParticipantCreate(BaseModel):
    participant_type: str = "tercero_relevante"
    person_type: str = "persona_fisica"
    display_name: str
    document_type: str = ""
    document_number: str = ""
    tax_id: str = ""
    email: str = ""
    phone: str = ""
    address: str = ""
    role_description: str = ""
    relationship_to_case: str = ""
    notes: str = ""
    sensitivity_level: str = "reservado"


class CaseParticipantRead(CaseParticipantCreate, ORMModel):
    id: int
    case_id: int
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
