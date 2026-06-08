from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import or_
from sqlalchemy.orm import Session

from operia.cases.models import Case
from operia.core.database import get_db
from operia.identity.dependencies import CurrentUser, require_permission
from operia.mind.models import MindAgent, MindAuditLog, MindGraphEdge, MindGraphNode, MindNote, MindPrompt
from operia.mind.schemas import (
    MindAgentRead,
    MindAuditCreate,
    MindAuditRead,
    MindCaseBrief,
    MindGraphEdgeCreate,
    MindGraphNodeCreate,
    MindNoteCreate,
    MindNoteRead,
    MindPromptRead,
    MindSearchResult,
    MindSnapshotRead,
)
from operia.mind.service import (
    create_case_snapshot,
    create_edge,
    create_note,
    create_presentation_snapshot,
    create_report_snapshot,
    build_case_brief,
    note_search_score,
    text_excerpt,
    upsert_node,
    write_mind_audit,
)
from operia.mind.vault import ensure_vault, vault_root
from operia.reports.models import Presentation, Report

router = APIRouter()


def as_dict(obj) -> dict:
    return {column.name: getattr(obj, column.name) for column in obj.__table__.columns}


@router.get("/")
def status() -> dict[str, object]:
    ensure_vault()
    return {
        "module": "OPERIA Mind",
        "status": "active",
        "description": "Forensic memory vault, Markdown notes, prompts, agents, graph, and audit trail.",
        "vault_path": str(vault_root()),
    }


@router.post("/notes", response_model=MindNoteRead)
def create_mind_note(
    payload: MindNoteCreate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("cases:write")),
):
    if payload.case_id and not db.get(Case, payload.case_id):
        raise HTTPException(status_code=404, detail="Caso no encontrado.")
    note = create_note(db, payload, current_user)
    db.commit()
    db.refresh(note)
    return note


@router.get("/notes", response_model=list[MindNoteRead])
def list_mind_notes(
    case_id: int | None = None,
    note_type: str | None = None,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("cases:read")),
):
    query = db.query(MindNote)
    if current_user.organization_id:
        query = query.filter(or_(MindNote.organization_id == current_user.organization_id, MindNote.organization_id.is_(None)))
    if case_id is not None:
        query = query.filter(MindNote.case_id == case_id)
    if note_type:
        query = query.filter(MindNote.note_type == note_type)
    return query.order_by(MindNote.updated_at.desc()).limit(200).all()


@router.get("/search", response_model=list[MindSearchResult])
def search_mind(
    q: str,
    case_id: int | None = None,
    limit: int = 20,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("cases:read")),
):
    query_text = q.strip()
    if len(query_text) < 2:
        return []
    query = db.query(MindNote)
    if current_user.organization_id:
        query = query.filter(or_(MindNote.organization_id == current_user.organization_id, MindNote.organization_id.is_(None)))
    if case_id is not None:
        query = query.filter(MindNote.case_id == case_id)
    candidates = query.order_by(MindNote.updated_at.desc()).limit(500).all()
    ranked = []
    for note in candidates:
        score, matches = note_search_score(note, query_text)
        if score:
            ranked.append((score, note, matches))
    ranked.sort(key=lambda item: (item[0], item[1].updated_at), reverse=True)
    return [
        MindSearchResult(
            id=note.id,
            case_id=note.case_id,
            note_type=note.note_type,
            title=note.title,
            summary=note.summary,
            content_excerpt=text_excerpt(note.content or note.summary, query_text),
            vault_path=note.vault_path,
            confidence=note.confidence,
            review_status=note.review_status,
            score=score,
            matches=matches,
        )
        for score, note, matches in ranked[: max(1, min(limit, 50))]
    ]


@router.get("/notes/{note_id}", response_model=MindNoteRead)
def read_mind_note(
    note_id: int,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("cases:read")),
):
    note = db.get(MindNote, note_id)
    if not note:
        raise HTTPException(status_code=404, detail="Nota no encontrada.")
    if current_user.organization_id and note.organization_id not in (None, current_user.organization_id):
        raise HTTPException(status_code=403, detail="No tenés permisos para esta nota.")
    return note


@router.post("/cases/{case_id}/snapshot", response_model=MindSnapshotRead)
def snapshot_case(
    case_id: int,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("cases:write")),
):
    case = db.get(Case, case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Caso no encontrado.")
    db.expire(
        case,
        [
            "participants",
            "evidence",
            "actions",
            "findings",
            "hypotheses",
            "legal_mappings",
            "reports",
        ],
    )
    note, nodes, edges = create_case_snapshot(db, case, current_user)
    db.commit()
    db.refresh(note)
    return MindSnapshotRead(
        case_id=case_id,
        note_id=note.id,
        graph_nodes=nodes,
        graph_edges=edges,
        vault_path=note.vault_path,
        message="Snapshot del caso guardado en memoria forense.",
    )


@router.post("/reports/{report_id}/snapshot", response_model=MindSnapshotRead)
def snapshot_report(
    report_id: int,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("reports:write")),
):
    report = db.get(Report, report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Informe no encontrado.")
    if current_user.organization_id and report.organization_id not in (None, current_user.organization_id):
        raise HTTPException(status_code=403, detail="No tenés permisos para este informe.")
    db.expire(report, ["case", "sections"])
    note, nodes, edges = create_report_snapshot(db, report, current_user)
    db.commit()
    db.refresh(note)
    return MindSnapshotRead(
        case_id=report.case_id,
        note_id=note.id,
        graph_nodes=nodes,
        graph_edges=edges,
        vault_path=note.vault_path,
        message="Informe guardado en memoria forense.",
    )


@router.post("/presentations/{presentation_id}/snapshot", response_model=MindSnapshotRead)
def snapshot_presentation(
    presentation_id: int,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("reports:write")),
):
    presentation = db.get(Presentation, presentation_id)
    if not presentation:
        raise HTTPException(status_code=404, detail="Exposicion no encontrada.")
    if current_user.organization_id and presentation.organization_id not in (None, current_user.organization_id):
        raise HTTPException(status_code=403, detail="No tenes permisos para esta exposicion.")
    db.expire(presentation, ["case", "slides"])
    note, nodes, edges = create_presentation_snapshot(db, presentation, current_user)
    db.commit()
    db.refresh(note)
    return MindSnapshotRead(
        case_id=presentation.case_id,
        note_id=note.id,
        graph_nodes=nodes,
        graph_edges=edges,
        vault_path=note.vault_path,
        message="Exposicion guardada en memoria forense.",
    )


@router.get("/cases/{case_id}/notes", response_model=list[MindNoteRead])
def case_notes(
    case_id: int,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("cases:read")),
):
    return list_mind_notes(case_id=case_id, db=db, current_user=current_user)


@router.post("/graph/nodes")
def create_graph_node(
    payload: MindGraphNodeCreate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("cases:write")),
):
    node_key = f"{payload.node_type}:{payload.case_id or 'global'}:{payload.source_entity_type or payload.label}:{payload.source_entity_id or payload.label}"
    node = upsert_node(
        db,
        node_key=node_key,
        node_type=payload.node_type,
        label=payload.label,
        case_id=payload.case_id,
        current_user=current_user,
        source_module=payload.source_module,
        source_entity_type=payload.source_entity_type,
        source_entity_id=payload.source_entity_id,
        metadata=payload.metadata,
    )
    write_mind_audit(db, "create_graph_node", current_user, payload.case_id, "mind_graph_node", str(node.id), details=node.label)
    db.commit()
    db.refresh(node)
    return as_dict(node)


@router.post("/graph/edges")
def create_graph_edge(
    payload: MindGraphEdgeCreate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("cases:write")),
):
    edge = create_edge(
        db,
        payload.source_node_key,
        payload.target_node_key,
        payload.relation_type,
        payload.case_id,
        current_user,
        payload.label,
        payload.confidence,
        payload.evidence_id,
        payload.metadata,
    )
    write_mind_audit(db, "create_graph_edge", current_user, payload.case_id, "mind_graph_edge", str(edge.id), details=payload.relation_type)
    db.commit()
    db.refresh(edge)
    return as_dict(edge)


@router.get("/cases/{case_id}/graph")
def case_graph(
    case_id: int,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("cases:read")),
):
    node_query = db.query(MindGraphNode).filter(MindGraphNode.case_id == case_id)
    edge_query = db.query(MindGraphEdge).filter(MindGraphEdge.case_id == case_id)
    if current_user.organization_id:
        node_query = node_query.filter(or_(MindGraphNode.organization_id == current_user.organization_id, MindGraphNode.organization_id.is_(None)))
        edge_query = edge_query.filter(or_(MindGraphEdge.organization_id == current_user.organization_id, MindGraphEdge.organization_id.is_(None)))
    return {
        "case_id": case_id,
        "nodes": [as_dict(row) for row in node_query.order_by(MindGraphNode.node_type, MindGraphNode.label).all()],
        "edges": [as_dict(row) for row in edge_query.order_by(MindGraphEdge.relation_type).all()],
    }


@router.get("/cases/{case_id}/brief", response_model=MindCaseBrief)
def case_brief(
    case_id: int,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("cases:read")),
):
    case = db.get(Case, case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Caso no encontrado.")
    if current_user.organization_id and case.organization_id not in (None, current_user.organization_id):
        raise HTTPException(status_code=403, detail="No tenes permisos para este caso.")
    db.expire(
        case,
        [
            "evidence",
            "actions",
            "findings",
            "hypotheses",
            "legal_mappings",
            "reports",
            "presentations",
            "damage_items",
            "deepfake_analyses",
            "blockchain_transactions",
            "iot_devices",
        ],
    )
    return build_case_brief(db, case, current_user)


@router.get("/prompts", response_model=list[MindPromptRead])
def list_prompts(
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("cases:read")),
):
    query = db.query(MindPrompt)
    if current_user.organization_id:
        query = query.filter(or_(MindPrompt.organization_id == current_user.organization_id, MindPrompt.organization_id.is_(None)))
    return query.order_by(MindPrompt.title).all()


@router.get("/agents", response_model=list[MindAgentRead])
def list_agents(
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("cases:read")),
):
    query = db.query(MindAgent)
    if current_user.organization_id:
        query = query.filter(or_(MindAgent.organization_id == current_user.organization_id, MindAgent.organization_id.is_(None)))
    return query.order_by(MindAgent.name).all()


@router.post("/audit")
def create_mind_audit(
    payload: MindAuditCreate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("audit:read")),
):
    row = write_mind_audit(
        db,
        payload.action,
        current_user,
        payload.case_id,
        payload.entity_type,
        payload.entity_id,
        payload.severity,
        payload.details,
    )
    db.commit()
    db.refresh(row)
    return as_dict(row)


@router.get("/audit", response_model=list[MindAuditRead])
def list_mind_audit(
    case_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("audit:read")),
):
    query = db.query(MindAuditLog)
    if current_user.organization_id:
        query = query.filter(or_(MindAuditLog.organization_id == current_user.organization_id, MindAuditLog.organization_id.is_(None)))
    if case_id is not None:
        query = query.filter(MindAuditLog.case_id == case_id)
    return [as_dict(row) for row in query.order_by(MindAuditLog.created_at.desc()).limit(100).all()]
