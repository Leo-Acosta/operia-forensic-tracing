from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from operia.core.database import Base
from operia.shared.models import TimestampMixin


class MindNote(Base, TimestampMixin):
    __tablename__ = "mind_notes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    organization_id: Mapped[int | None] = mapped_column(ForeignKey("organizations.id"), nullable=True)
    case_id: Mapped[int | None] = mapped_column(ForeignKey("cases.id"), nullable=True)
    source_module: Mapped[str] = mapped_column(String(120), default="mind")
    source_entity_type: Mapped[str] = mapped_column(String(120), default="")
    source_entity_id: Mapped[str] = mapped_column(String(80), default="")
    note_type: Mapped[str] = mapped_column(String(80), default="nota")
    title: Mapped[str] = mapped_column(String(255))
    slug: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    vault_path: Mapped[str] = mapped_column(String(500), default="")
    tags: Mapped[str] = mapped_column(Text, default="[]")
    linked_evidence: Mapped[str] = mapped_column(Text, default="[]")
    linked_reports: Mapped[str] = mapped_column(Text, default="[]")
    linked_legal_sources: Mapped[str] = mapped_column(Text, default="[]")
    confidence: Mapped[str] = mapped_column(String(40), default="medio")
    review_status: Mapped[str] = mapped_column(String(80), default="borrador")
    summary: Mapped[str] = mapped_column(Text, default="")
    content: Mapped[str] = mapped_column(Text, default="")
    frontmatter_json: Mapped[str] = mapped_column(Text, default="{}")
    sensitive: Mapped[bool] = mapped_column(Boolean, default=False)


class MindGraphNode(Base, TimestampMixin):
    __tablename__ = "mind_graph_nodes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    organization_id: Mapped[int | None] = mapped_column(ForeignKey("organizations.id"), nullable=True)
    case_id: Mapped[int | None] = mapped_column(ForeignKey("cases.id"), nullable=True)
    node_key: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    node_type: Mapped[str] = mapped_column(String(80))
    label: Mapped[str] = mapped_column(String(255))
    source_module: Mapped[str] = mapped_column(String(120), default="")
    source_entity_type: Mapped[str] = mapped_column(String(120), default="")
    source_entity_id: Mapped[str] = mapped_column(String(80), default="")
    metadata_json: Mapped[str] = mapped_column(Text, default="{}")


class MindGraphEdge(Base, TimestampMixin):
    __tablename__ = "mind_graph_edges"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    organization_id: Mapped[int | None] = mapped_column(ForeignKey("organizations.id"), nullable=True)
    case_id: Mapped[int | None] = mapped_column(ForeignKey("cases.id"), nullable=True)
    source_node_key: Mapped[str] = mapped_column(String(255), index=True)
    target_node_key: Mapped[str] = mapped_column(String(255), index=True)
    relation_type: Mapped[str] = mapped_column(String(120))
    label: Mapped[str] = mapped_column(String(255), default="")
    confidence: Mapped[str] = mapped_column(String(40), default="medio")
    evidence_id: Mapped[int | None] = mapped_column(ForeignKey("evidence.id"), nullable=True)
    metadata_json: Mapped[str] = mapped_column(Text, default="{}")


class MindPrompt(Base, TimestampMixin):
    __tablename__ = "mind_prompts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    organization_id: Mapped[int | None] = mapped_column(ForeignKey("organizations.id"), nullable=True)
    key: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(255))
    purpose: Mapped[str] = mapped_column(Text, default="")
    prompt_text: Mapped[str] = mapped_column(Text)
    output_format: Mapped[str] = mapped_column(String(120), default="markdown")
    requires_review: Mapped[bool] = mapped_column(Boolean, default=True)
    vault_path: Mapped[str] = mapped_column(String(500), default="")


class MindAgent(Base, TimestampMixin):
    __tablename__ = "mind_agents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    organization_id: Mapped[int | None] = mapped_column(ForeignKey("organizations.id"), nullable=True)
    key: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(255))
    scope: Mapped[str] = mapped_column(Text, default="")
    allowed_modules: Mapped[str] = mapped_column(Text, default="[]")
    restrictions: Mapped[str] = mapped_column(Text, default="")
    base_prompt_key: Mapped[str] = mapped_column(String(120), default="")
    output_format: Mapped[str] = mapped_column(String(120), default="markdown")
    risk_level: Mapped[str] = mapped_column(String(40), default="medio")
    requires_human_review: Mapped[bool] = mapped_column(Boolean, default=True)
    vault_path: Mapped[str] = mapped_column(String(500), default="")


class MindAuditLog(Base, TimestampMixin):
    __tablename__ = "mind_audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    organization_id: Mapped[int | None] = mapped_column(ForeignKey("organizations.id"), nullable=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    case_id: Mapped[int | None] = mapped_column(ForeignKey("cases.id"), nullable=True)
    action: Mapped[str] = mapped_column(String(160))
    entity_type: Mapped[str] = mapped_column(String(120), default="")
    entity_id: Mapped[str] = mapped_column(String(80), default="")
    severity: Mapped[str] = mapped_column(String(40), default="info")
    details: Mapped[str] = mapped_column(Text, default="")
