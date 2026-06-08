import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from operia.cases.models import Case
from operia.identity.dependencies import CurrentUser
from operia.mind.models import MindAuditLog, MindGraphEdge, MindGraphNode, MindNote
from operia.mind.schemas import MindNoteCreate
from operia.mind.vault import note_folder, slugify, write_note


def utc_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def json_dump(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False)


def text_excerpt(text: str, query: str, length: int = 220) -> str:
    clean = " ".join((text or "").split())
    if not clean:
        return ""
    index = clean.lower().find(query.lower())
    if index < 0:
        return clean[:length]
    start = max(index - 70, 0)
    end = min(start + length, len(clean))
    prefix = "..." if start else ""
    suffix = "..." if end < len(clean) else ""
    return f"{prefix}{clean[start:end]}{suffix}"


def note_search_score(note: MindNote, query: str) -> tuple[int, list[str]]:
    terms = [term.strip().lower() for term in query.split() if term.strip()]
    if not terms:
        return 0, []
    fields = {
        "titulo": note.title or "",
        "resumen": note.summary or "",
        "contenido": note.content or "",
        "tags": note.tags or "",
        "tipo": note.note_type or "",
    }
    score = 0
    matches: list[str] = []
    for label, value in fields.items():
        lowered = value.lower()
        hits = sum(1 for term in terms if term in lowered)
        if hits:
            weight = 6 if label == "titulo" else 4 if label in ("resumen", "tags") else 2
            score += hits * weight
            matches.append(label)
    return score, matches


def frontmatter(data: dict[str, Any]) -> str:
    lines = ["---"]
    for key, value in data.items():
        if isinstance(value, list):
            lines.append(f"{key}:")
            for item in value:
                lines.append(f"  - {item}")
        elif value is None:
            lines.append(f"{key}:")
        else:
            text = str(value).replace('"', "'")
            lines.append(f'{key}: "{text}"')
    lines.append("---")
    return "\n".join(lines)


def note_markdown(payload: MindNoteCreate, slug: str, case: Case | None = None) -> tuple[str, dict[str, Any]]:
    meta = {
        "id": slug,
        "case_id": payload.case_id,
        "case_code": case.case_code if case else "",
        "title": payload.title,
        "type": payload.note_type,
        "source_module": payload.source_module,
        "source_entity_type": payload.source_entity_type,
        "source_entity_id": payload.source_entity_id,
        "created_at": utc_iso(),
        "updated_at": utc_iso(),
        "author": "",
        "tags": payload.tags,
        "linked_evidence": payload.linked_evidence,
        "linked_reports": payload.linked_reports,
        "linked_legal_sources": payload.linked_legal_sources,
        "confidence": payload.confidence,
        "review_status": payload.review_status,
        "sensitive": payload.sensitive,
    }
    body = payload.content.strip() or payload.summary.strip() or "Nota pendiente de completar."
    markdown = f"{frontmatter(meta)}\n\n# {payload.title}\n\n{body}\n"
    return markdown, meta


def create_note(db: Session, payload: MindNoteCreate, current_user: CurrentUser | None = None) -> MindNote:
    case = db.get(Case, payload.case_id) if payload.case_id else None
    base_slug = slugify(f"{payload.note_type}-{payload.case_id or 'global'}-{payload.title}")
    slug = base_slug
    counter = 2
    while db.query(MindNote).filter(MindNote.slug == slug).first():
        slug = f"{base_slug}-{counter}"
        counter += 1
    relative_path = f"{note_folder(payload.note_type)}/{slug}.md"
    markdown, meta = note_markdown(payload, slug, case)
    write_note(relative_path, markdown)
    row = MindNote(
        organization_id=current_user.organization_id if current_user else None,
        case_id=payload.case_id,
        source_module=payload.source_module,
        source_entity_type=payload.source_entity_type,
        source_entity_id=payload.source_entity_id,
        note_type=payload.note_type,
        title=payload.title,
        slug=slug,
        vault_path=relative_path,
        tags=json_dump(payload.tags),
        linked_evidence=json_dump(payload.linked_evidence),
        linked_reports=json_dump(payload.linked_reports),
        linked_legal_sources=json_dump(payload.linked_legal_sources),
        confidence=payload.confidence,
        review_status=payload.review_status,
        summary=payload.summary,
        content=payload.content,
        frontmatter_json=json_dump(meta),
        sensitive=payload.sensitive,
    )
    db.add(row)
    db.flush()
    write_mind_audit(
        db,
        "create_note",
        current_user,
        case_id=payload.case_id,
        entity_type="mind_note",
        entity_id=str(row.id),
        details=payload.title,
    )
    return row


def upsert_node(
    db: Session,
    node_key: str,
    node_type: str,
    label: str,
    case_id: int | None = None,
    current_user: CurrentUser | None = None,
    source_module: str = "",
    source_entity_type: str = "",
    source_entity_id: str = "",
    metadata: dict[str, Any] | None = None,
) -> MindGraphNode:
    row = db.query(MindGraphNode).filter(MindGraphNode.node_key == node_key).first()
    if row:
        row.label = label
        row.metadata_json = json_dump(metadata or {})
        return row
    row = MindGraphNode(
        organization_id=current_user.organization_id if current_user else None,
        case_id=case_id,
        node_key=node_key,
        node_type=node_type,
        label=label,
        source_module=source_module,
        source_entity_type=source_entity_type,
        source_entity_id=source_entity_id,
        metadata_json=json_dump(metadata or {}),
    )
    db.add(row)
    db.flush()
    return row


def create_edge(
    db: Session,
    source_node_key: str,
    target_node_key: str,
    relation_type: str,
    case_id: int | None = None,
    current_user: CurrentUser | None = None,
    label: str = "",
    confidence: str = "medio",
    evidence_id: int | None = None,
    metadata: dict[str, Any] | None = None,
) -> MindGraphEdge:
    existing = (
        db.query(MindGraphEdge)
        .filter(
            MindGraphEdge.source_node_key == source_node_key,
            MindGraphEdge.target_node_key == target_node_key,
            MindGraphEdge.relation_type == relation_type,
            MindGraphEdge.case_id == case_id,
        )
        .first()
    )
    if existing:
        return existing
    row = MindGraphEdge(
        organization_id=current_user.organization_id if current_user else None,
        case_id=case_id,
        source_node_key=source_node_key,
        target_node_key=target_node_key,
        relation_type=relation_type,
        label=label,
        confidence=confidence,
        evidence_id=evidence_id,
        metadata_json=json_dump(metadata or {}),
    )
    db.add(row)
    db.flush()
    return row


def case_snapshot_markdown(case: Case) -> str:
    participants = list(getattr(case, "participants", []) or [])
    evidence = list(getattr(case, "evidence", []) or [])
    findings = list(getattr(case, "findings", []) or [])
    hypotheses = list(getattr(case, "hypotheses", []) or [])
    legal = list(getattr(case, "legal_mappings", []) or [])
    reports = list(getattr(case, "reports", []) or [])
    lines = [
        f"## Resumen del caso",
        "",
        case.description or "Sin descripción ampliada.",
        "",
        "## Estado operativo",
        "",
        f"- Código: {case.case_code}",
        f"- Tipo de incidente: {case.incident_type}",
        f"- Estado: {case.status}",
        f"- Jurisdicción: {case.jurisdiction}",
        "",
        "## Inventario",
        "",
        f"- Participantes: {len(participants)}",
        f"- Evidencias: {len(evidence)}",
        f"- Hallazgos: {len(findings)}",
        f"- Hipótesis: {len(hypotheses)}",
        f"- Mapeos legales: {len(legal)}",
        f"- Informes: {len(reports)}",
        "",
        "## Evidencia principal",
        "",
    ]
    if evidence:
        for item in evidence[:20]:
            lines.append(f"- Evidencia #{item.id}: {item.description} | SHA-256: {item.sha256_hash or 'pendiente'}")
    else:
        lines.append("- Sin evidencia registrada.")
    lines.extend(["", "## Hallazgos", ""])
    if findings:
        for item in findings[:20]:
            lines.append(f"- Hallazgo #{item.id}: {item.title} | Confianza: {item.confidence_level}")
    else:
        lines.append("- Sin hallazgos registrados.")
    lines.extend(["", "## Normativa vinculada", ""])
    if legal:
        for item in legal[:20]:
            lines.append(f"- {item.norm_reference}: {item.decision_status} | {item.confidence_level}")
    else:
        lines.append("- Sin mapeos legales aprobados.")
    return "\n".join(lines)


def create_case_snapshot(db: Session, case: Case, current_user: CurrentUser | None = None) -> tuple[MindNote, int, int]:
    payload = MindNoteCreate(
        case_id=case.id,
        note_type="caso",
        title=f"{case.case_code} - {case.title}",
        summary=f"Snapshot operativo del caso {case.case_code}.",
        content=case_snapshot_markdown(case),
        source_module="cases",
        source_entity_type="case",
        source_entity_id=str(case.id),
        tags=["caso", "snapshot", "operia"],
        confidence="medio",
        review_status="snapshot",
    )
    note = create_note(db, payload, current_user)
    case_key = f"case:{case.id}"
    note_key = f"note:{note.id}"
    upsert_node(db, case_key, "case", f"{case.case_code} - {case.title}", case.id, current_user, "cases", "case", str(case.id))
    upsert_node(db, note_key, "note", note.title, case.id, current_user, "mind", "mind_note", str(note.id))
    edge_count = 0
    create_edge(db, case_key, note_key, "tiene_snapshot", case.id, current_user)
    edge_count += 1
    node_count = 2
    for evidence in list(getattr(case, "evidence", []) or [])[:100]:
        evidence_key = f"evidence:{evidence.id}"
        upsert_node(db, evidence_key, "evidence", evidence.description[:180], case.id, current_user, "evidence", "evidence", str(evidence.id))
        create_edge(db, case_key, evidence_key, "contiene", case.id, current_user)
        create_edge(db, evidence_key, note_key, "citado_en", case.id, current_user, evidence_id=evidence.id)
        node_count += 1
        edge_count += 2
    for finding in list(getattr(case, "findings", []) or [])[:100]:
        finding_key = f"finding:{finding.id}"
        upsert_node(db, finding_key, "finding", finding.title[:180], case.id, current_user, "cases", "finding", str(finding.id))
        create_edge(db, case_key, finding_key, "contiene", case.id, current_user)
        if finding.evidence_id:
            create_edge(db, f"evidence:{finding.evidence_id}", finding_key, "sostiene", case.id, current_user, evidence_id=finding.evidence_id)
        node_count += 1
        edge_count += 1
    for mapping in list(getattr(case, "legal_mappings", []) or [])[:100]:
        legal_key = f"legal_mapping:{mapping.id}"
        upsert_node(db, legal_key, "legal_mapping", mapping.norm_reference, case.id, current_user, "legal_knowledge", "legal_mapping", str(mapping.id))
        create_edge(db, case_key, legal_key, "tiene_fuente_legal", case.id, current_user)
        node_count += 1
        edge_count += 1
    write_mind_audit(db, "case_snapshot", current_user, case.id, "case", str(case.id), details=note.title)
    return note, node_count, edge_count


def write_mind_audit(
    db: Session,
    action: str,
    current_user: CurrentUser | None = None,
    case_id: int | None = None,
    entity_type: str = "",
    entity_id: str = "",
    severity: str = "info",
    details: str = "",
) -> MindAuditLog:
    row = MindAuditLog(
        organization_id=current_user.organization_id if current_user else None,
        user_id=current_user.id if current_user else None,
        case_id=case_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        severity=severity,
        details=details,
    )
    db.add(row)
    return row
