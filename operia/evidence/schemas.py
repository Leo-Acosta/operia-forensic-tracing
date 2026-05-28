from datetime import datetime

from pydantic import BaseModel

from operia.shared.schemas import ORMModel


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
