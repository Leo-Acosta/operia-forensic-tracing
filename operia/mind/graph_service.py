from typing import Any

from sqlalchemy import or_
from sqlalchemy.orm import Session

from operia.identity.dependencies import CurrentUser
from operia.mind.models import MindGraphEdge, MindGraphNode
from operia.mind.service import create_edge, upsert_node, write_mind_audit


NODE_TYPES = [
    "case",
    "evidence",
    "person",
    "entity",
    "ip",
    "url",
    "wallet",
    "transaction",
    "iot_device",
    "media",
    "finding",
    "hypothesis",
    "legal_norm",
    "legal_mapping",
    "report",
    "tool",
    "note",
    "presentation",
]

RELATION_TYPES = [
    "pertenece_a",
    "vinculado_con",
    "sostiene",
    "limita",
    "contradice",
    "deriva_de",
    "analizado_por",
    "citado_en",
    "exportado_en",
    "requiere_revision",
    "tiene_fuente_legal",
    "tiene_hash",
]


def graph_node_key(
    node_type: str,
    label: str,
    case_id: int | None = None,
    source_entity_type: str = "",
    source_entity_id: str = "",
) -> str:
    clean_label = "-".join(label.strip().lower().split())[:80] or "sin-etiqueta"
    entity = source_entity_id or clean_label
    entity_type = source_entity_type or "manual"
    scope = case_id if case_id is not None else "global"
    return f"{node_type}:{scope}:{entity_type}:{entity}"


class GraphService:
    def __init__(self, db: Session, current_user: CurrentUser):
        self.db = db
        self.current_user = current_user

    def create_node(
        self,
        node_type: str,
        label: str,
        case_id: int | None = None,
        source_module: str = "mind",
        source_entity_type: str = "",
        source_entity_id: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> MindGraphNode:
        node_key = graph_node_key(node_type, label, case_id, source_entity_type, source_entity_id)
        node = upsert_node(
            self.db,
            node_key=node_key,
            node_type=node_type,
            label=label,
            case_id=case_id,
            current_user=self.current_user,
            source_module=source_module,
            source_entity_type=source_entity_type,
            source_entity_id=source_entity_id,
            metadata=metadata or {},
        )
        write_mind_audit(
            self.db,
            "create_graph_node",
            self.current_user,
            case_id,
            "mind_graph_node",
            str(node.id),
            details=f"{node_type}: {label}",
        )
        return node

    def create_relation(
        self,
        source_node_key: str,
        target_node_key: str,
        relation_type: str,
        case_id: int | None = None,
        label: str = "",
        confidence: str = "medio",
        evidence_id: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> MindGraphEdge:
        edge = create_edge(
            self.db,
            source_node_key,
            target_node_key,
            relation_type,
            case_id,
            self.current_user,
            label,
            confidence,
            evidence_id,
            metadata or {},
        )
        write_mind_audit(
            self.db,
            "create_graph_edge",
            self.current_user,
            case_id,
            "mind_graph_edge",
            str(edge.id),
            details=f"{source_node_key} {relation_type} {target_node_key}",
        )
        return edge

    def list_graph(self, case_id: int | None = None) -> dict[str, object]:
        node_query = self.db.query(MindGraphNode)
        edge_query = self.db.query(MindGraphEdge)
        if case_id is not None:
            node_query = node_query.filter(MindGraphNode.case_id == case_id)
            edge_query = edge_query.filter(MindGraphEdge.case_id == case_id)
        if self.current_user.organization_id:
            node_query = node_query.filter(
                or_(
                    MindGraphNode.organization_id == self.current_user.organization_id,
                    MindGraphNode.organization_id.is_(None),
                )
            )
            edge_query = edge_query.filter(
                or_(
                    MindGraphEdge.organization_id == self.current_user.organization_id,
                    MindGraphEdge.organization_id.is_(None),
                )
            )
        nodes = node_query.order_by(MindGraphNode.node_type, MindGraphNode.label).limit(500).all()
        edges = edge_query.order_by(MindGraphEdge.relation_type, MindGraphEdge.id).limit(1000).all()
        return {
            "case_id": case_id,
            "nodes": nodes,
            "edges": edges,
            "node_types": NODE_TYPES,
            "relation_types": RELATION_TYPES,
        }
