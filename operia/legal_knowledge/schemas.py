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
    legal_area: str
    norm_reference: str
    source_id: int | None = None
    analysis: str
    verification_status: str = "Fuente pendiente de verificacion"


class LegalMappingRead(LegalMappingCreate, ORMModel):
    id: int
    created_at: datetime
