from datetime import datetime

from pydantic import BaseModel

from operia.shared.schemas import ORMModel


class MindNoteCreate(BaseModel):
    case_id: int | None = None
    note_type: str = "nota"
    title: str
    content: str = ""
    summary: str = ""
    source_module: str = "mind"
    source_entity_type: str = ""
    source_entity_id: str = ""
    tags: list[str] = []
    linked_evidence: list[int] = []
    linked_reports: list[int] = []
    linked_legal_sources: list[int] = []
    confidence: str = "medio"
    review_status: str = "borrador"
    sensitive: bool = False


class MindNoteRead(ORMModel):
    id: int
    organization_id: int | None = None
    case_id: int | None = None
    source_module: str
    source_entity_type: str
    source_entity_id: str
    note_type: str
    title: str
    slug: str
    vault_path: str
    tags: str
    linked_evidence: str
    linked_reports: str
    linked_legal_sources: str
    confidence: str
    review_status: str
    summary: str
    content: str
    frontmatter_json: str
    sensitive: bool
    created_at: datetime
    updated_at: datetime


class MindGraphNodeCreate(BaseModel):
    case_id: int | None = None
    node_type: str
    label: str
    source_module: str = "mind"
    source_entity_type: str = ""
    source_entity_id: str = ""
    metadata: dict = {}


class MindGraphEdgeCreate(BaseModel):
    case_id: int | None = None
    source_node_key: str
    target_node_key: str
    relation_type: str
    label: str = ""
    confidence: str = "medio"
    evidence_id: int | None = None
    metadata: dict = {}


class MindPromptRead(ORMModel):
    id: int
    key: str
    title: str
    purpose: str
    prompt_text: str
    output_format: str
    requires_review: bool
    vault_path: str
    created_at: datetime
    updated_at: datetime


class MindAgentRead(ORMModel):
    id: int
    key: str
    name: str
    role: str
    scope: str
    allowed_modules: str
    restrictions: str
    base_prompt_key: str
    output_format: str
    risk_level: str
    requires_human_review: bool
    vault_path: str
    created_at: datetime
    updated_at: datetime


class MindAuditCreate(BaseModel):
    case_id: int | None = None
    action: str
    entity_type: str = ""
    entity_id: str = ""
    severity: str = "info"
    details: str = ""


class MindSnapshotRead(BaseModel):
    case_id: int
    note_id: int
    graph_nodes: int
    graph_edges: int
    vault_path: str
    message: str
