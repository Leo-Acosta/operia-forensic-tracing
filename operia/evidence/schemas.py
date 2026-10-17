from datetime import datetime, timezone

from pydantic import BaseModel, Field, ConfigDict, field_validator, field_serializer

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


class CustodyLedgerRead(ORMModel):
    root_action_id: int
    previous_action_id: int | None
    version: int
    kind: str
    actor_user_id: int | None
    actor_name: str
    actor_role: str
    recorded_at: datetime
    occurred_at: datetime | None
    occurred_at_original: str | None
    reason: str
    changes_json: str

    @field_serializer("recorded_at", "occurred_at")
    def utc_times(self, value):
        if value is None: return None
        return (value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)).isoformat()


class CustodyRectification(BaseModel):
    model_config = ConfigDict(extra="forbid")
    reason: str = Field(min_length=1, max_length=2000)
    changes: dict[str, str] = Field(default_factory=dict)
    occurred_at: datetime | None = None

    @field_validator("reason")
    @classmethod
    def reason_required(cls, value):
        if not value.strip(): raise ValueError("Motivo requerido")
        return value.strip()

    @field_validator("changes")
    @classmethod
    def allowed_changes(cls, value):
        allowed = {"detailed_description", "tool_used", "command_or_procedure", "result_obtained",
            "hash_before", "hash_after", "validated_by", "legal_observations", "status"}
        if not set(value) <= allowed or any(len(item) > 16000 for item in value.values()) or sum(len(item.encode()) for item in value.values()) > 32768:
            raise ValueError("Campos de rectificación no permitidos")
        return value

    @field_validator("occurred_at")
    @classmethod
    def explicit_timezone(cls, value):
        if value is not None and value.utcoffset() is None:
            raise ValueError("Zona horaria requerida")
        return value


class CustodyActionRead(CustodyActionCreate, ORMModel):
    id: int
    action_at: datetime
    created_at: datetime
    ledger_entry: CustodyLedgerRead | None = None
