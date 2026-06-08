import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import or_
from sqlalchemy.orm import Session

from operia.cases.models import Case
from operia.identity.dependencies import CurrentUser
from operia.mind.models import MindAuditLog, MindGraphEdge, MindGraphNode, MindNote
from operia.mind.schemas import MindCaseBrief, MindNoteCreate
from operia.mind.vault import note_folder, slugify, write_note
from operia.reports.models import Presentation, Report


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


def report_snapshot_markdown(report: Report) -> str:
    sections = list(getattr(report, "sections", []) or [])
    lines = [
        "## Identificación del informe",
        "",
        f"- Título: {report.title}",
        f"- Versión: {report.version}",
        f"- Estado: {report.status}",
        f"- Autor: {report.author or 'No consignado'}",
        f"- Puntaje de revisión: {report.review_score}",
        "",
        "## Observaciones",
        "",
        report.observations or "Sin observaciones registradas.",
        "",
        "## Contenido principal",
        "",
        report.markdown_content or "Sin contenido principal cargado.",
    ]
    if sections:
        lines.extend(["", "## Secciones estructuradas", ""])
        for section in sorted(sections, key=lambda item: item.order_index)[:80]:
            lines.extend(
                [
                    f"### {section.order_index}. {section.title}",
                    "",
                    section.content or "Sin contenido.",
                    "",
                ]
            )
    return "\n".join(lines)


def create_report_snapshot(db: Session, report: Report, current_user: CurrentUser | None = None) -> tuple[MindNote, int, int]:
    payload = MindNoteCreate(
        case_id=report.case_id,
        note_type="informe",
        title=f"Informe #{report.id} - {report.title}",
        summary=f"Memoria persistente del informe {report.title} v{report.version}.",
        content=report_snapshot_markdown(report),
        source_module="reports",
        source_entity_type="report",
        source_entity_id=str(report.id),
        tags=["informe", "reporte", "memoria", "operia"],
        linked_reports=[report.id],
        confidence="medio",
        review_status=report.status or "borrador",
    )
    note = create_note(db, payload, current_user)
    case_key = f"case:{report.case_id}"
    report_key = f"report:{report.id}"
    note_key = f"note:{note.id}"
    case_label = f"Caso #{report.case_id}"
    if getattr(report, "case", None):
        case_label = f"{report.case.case_code} - {report.case.title}"
    upsert_node(db, case_key, "case", case_label, report.case_id, current_user, "cases", "case", str(report.case_id))
    upsert_node(db, report_key, "report", report.title, report.case_id, current_user, "reports", "report", str(report.id))
    upsert_node(db, note_key, "note", note.title, report.case_id, current_user, "mind", "mind_note", str(note.id))
    create_edge(db, case_key, report_key, "tiene_informe", report.case_id, current_user)
    create_edge(db, report_key, note_key, "guardado_en_memoria", report.case_id, current_user)
    write_mind_audit(db, "report_snapshot", current_user, report.case_id, "report", str(report.id), details=report.title)
    return note, 3, 2


def presentation_snapshot_markdown(presentation: Presentation) -> str:
    slides = sorted(list(getattr(presentation, "slides", []) or []), key=lambda item: item.slide_number)
    lines = [
        "## Identificacion de la exposicion",
        "",
        f"- Titulo: {presentation.title}",
        f"- Tipo: {presentation.presentation_type}",
        f"- Version: {presentation.version}",
        f"- Estado: {presentation.status}",
        f"- Autor: {presentation.author or 'No consignado'}",
        f"- Informe fuente: {presentation.source_report_id or 'No vinculado'}",
        f"- Puntaje de revision oral: {presentation.review_score}",
        "",
        "## Fragmentos seleccionados",
        "",
        presentation.selected_fragments or "Sin fragmentos seleccionados.",
    ]
    if slides:
        lines.extend(["", "## Guion y diapositivas", ""])
        for slide in slides[:80]:
            lines.extend(
                [
                    f"### {slide.slide_number}. {slide.title}",
                    "",
                    slide.text or "Sin texto visible.",
                    "",
                    f"- Tipo de contenido: {slide.content_type}",
                    f"- Nivel de confidencialidad: {slide.confidentiality_level}",
                    f"- Evidencia vinculada: {slide.evidence_id or 'No vinculada'}",
                    f"- Hallazgo vinculado: {slide.finding_id or 'No vinculado'}",
                    "",
                    "**Notas del expositor**",
                    "",
                    slide.speaker_notes or "Sin notas del expositor.",
                    "",
                ]
            )
    return "\n".join(lines)


def create_presentation_snapshot(
    db: Session,
    presentation: Presentation,
    current_user: CurrentUser | None = None,
) -> tuple[MindNote, int, int]:
    payload = MindNoteCreate(
        case_id=presentation.case_id,
        note_type="exposicion",
        title=f"Exposicion #{presentation.id} - {presentation.title}",
        summary=f"Memoria persistente de la exposicion {presentation.title} v{presentation.version}.",
        content=presentation_snapshot_markdown(presentation),
        source_module="reports",
        source_entity_type="presentation",
        source_entity_id=str(presentation.id),
        tags=["exposicion", "presentacion", "oralidad", "memoria", "operia"],
        linked_reports=[presentation.source_report_id] if presentation.source_report_id else [],
        confidence="medio",
        review_status=presentation.status or "borrador",
    )
    note = create_note(db, payload, current_user)
    case_key = f"case:{presentation.case_id}"
    presentation_key = f"presentation:{presentation.id}"
    note_key = f"note:{note.id}"
    case_label = f"Caso #{presentation.case_id}"
    if getattr(presentation, "case", None):
        case_label = f"{presentation.case.case_code} - {presentation.case.title}"
    upsert_node(db, case_key, "case", case_label, presentation.case_id, current_user, "cases", "case", str(presentation.case_id))
    upsert_node(
        db,
        presentation_key,
        "presentation",
        presentation.title,
        presentation.case_id,
        current_user,
        "reports",
        "presentation",
        str(presentation.id),
        metadata={"presentation_type": presentation.presentation_type, "review_score": presentation.review_score},
    )
    upsert_node(db, note_key, "note", note.title, presentation.case_id, current_user, "mind", "mind_note", str(note.id))
    edge_count = 0
    create_edge(db, case_key, presentation_key, "tiene_exposicion", presentation.case_id, current_user)
    edge_count += 1
    create_edge(db, presentation_key, note_key, "guardado_en_memoria", presentation.case_id, current_user)
    edge_count += 1
    if presentation.source_report_id:
        report_key = f"report:{presentation.source_report_id}"
        upsert_node(
            db,
            report_key,
            "report",
            f"Informe #{presentation.source_report_id}",
            presentation.case_id,
            current_user,
            "reports",
            "report",
            str(presentation.source_report_id),
        )
        create_edge(db, report_key, presentation_key, "deriva_en_exposicion", presentation.case_id, current_user)
        edge_count += 1
        node_count = 4
    else:
        node_count = 3
    write_mind_audit(
        db,
        "presentation_snapshot",
        current_user,
        presentation.case_id,
        "presentation",
        str(presentation.id),
        details=presentation.title,
    )
    return note, node_count, edge_count


def _append_if(items: list[str], condition: bool, text: str) -> None:
    if condition:
        items.append(text)


def build_case_brief(db: Session, case: Case, current_user: CurrentUser | None = None) -> MindCaseBrief:
    evidence = list(getattr(case, "evidence", []) or [])
    custody = list(getattr(case, "actions", []) or [])
    findings = list(getattr(case, "findings", []) or [])
    hypotheses = list(getattr(case, "hypotheses", []) or [])
    legal = list(getattr(case, "legal_mappings", []) or [])
    reports = list(getattr(case, "reports", []) or [])
    presentations = list(getattr(case, "presentations", []) or [])
    damage_items = list(getattr(case, "damage_items", []) or [])
    deepfake = list(getattr(case, "deepfake_analyses", []) or [])
    blockchain = list(getattr(case, "blockchain_transactions", []) or [])
    iot = list(getattr(case, "iot_devices", []) or [])

    note_query = db.query(MindNote).filter(MindNote.case_id == case.id)
    node_query = db.query(MindGraphNode).filter(MindGraphNode.case_id == case.id)
    edge_query = db.query(MindGraphEdge).filter(MindGraphEdge.case_id == case.id)
    if current_user and current_user.organization_id:
        note_query = note_query.filter(or_(MindNote.organization_id == current_user.organization_id, MindNote.organization_id.is_(None)))
        node_query = node_query.filter(or_(MindGraphNode.organization_id == current_user.organization_id, MindGraphNode.organization_id.is_(None)))
        edge_query = edge_query.filter(or_(MindGraphEdge.organization_id == current_user.organization_id, MindGraphEdge.organization_id.is_(None)))
    notes = note_query.order_by(MindNote.updated_at.desc()).limit(12).all()
    nodes = node_query.all()
    edges = edge_query.all()

    hashed_evidence = [item for item in evidence if getattr(item, "sha256_hash", "")]
    approved_legal = [
        item
        for item in legal
        if (getattr(item, "decision_status", "") or "").lower() in {"aprobado", "accepted", "validado"}
    ]
    supported_findings = [item for item in findings if getattr(item, "evidence_id", None) or getattr(item, "supporting_evidence", "")]

    known_facts = [
        f"Caso {case.case_code}: {case.title}.",
        f"Tipo de incidente registrado: {case.incident_type}.",
    ]
    _append_if(known_facts, bool(case.description), f"Narrativa inicial cargada: {case.description[:220]}.")
    _append_if(known_facts, bool(evidence), f"Evidencia registrada: {len(evidence)} item(s), {len(hashed_evidence)} con SHA-256.")
    _append_if(known_facts, bool(custody), f"Cadena de custodia: {len(custody)} accion(es) documentada(s).")
    _append_if(known_facts, bool(findings), f"Hallazgos tecnicos: {len(findings)} item(s), {len(supported_findings)} con soporte directo.")
    _append_if(known_facts, bool(approved_legal), f"Mapeo legal aprobado: {len(approved_legal)} norma(s) o criterio(s).")
    _append_if(known_facts, bool(reports), f"Informes generados: {len(reports)}.")
    _append_if(known_facts, bool(presentations), f"Exposiciones generadas: {len(presentations)}.")
    _append_if(known_facts, bool(damage_items), f"Rubros economicos cargados: {len(damage_items)}.")
    _append_if(known_facts, bool(deepfake), f"Analisis de medios/deepfake: {len(deepfake)} registro(s).")
    _append_if(known_facts, bool(blockchain), f"Transacciones blockchain registradas: {len(blockchain)}.")
    _append_if(known_facts, bool(iot), f"Dispositivos IoT registrados: {len(iot)}.")

    missing = []
    _append_if(missing, not evidence, "Cargar evidencia digital preservada y asociarla al caso.")
    _append_if(missing, bool(evidence) and len(hashed_evidence) < len(evidence), "Completar hashes SHA-256 de toda la evidencia.")
    _append_if(missing, not custody, "Registrar cadena de custodia con responsable, fecha y accion.")
    _append_if(missing, not findings, "Convertir analisis tecnicos relevantes en hallazgos estructurados.")
    _append_if(missing, bool(findings) and len(supported_findings) < len(findings), "Vincular cada hallazgo critico con evidencia concreta.")
    _append_if(missing, not approved_legal, "Aprobar un mapeo legal desde biblioteca registrada.")
    _append_if(missing, not reports, "Generar informe preliminar para control de calidad.")
    _append_if(missing, not presentations, "Generar exposicion del caso si se requiere defensa oral.")
    _append_if(missing, not notes, "Guardar al menos una nota o snapshot en memoria para trazabilidad cognitiva.")

    risks = []
    _append_if(risks, not evidence, "Riesgo alto: conclusiones sin evidencia preservada.")
    _append_if(risks, bool(evidence) and len(hashed_evidence) < len(evidence), "Riesgo de integridad: hay evidencia sin hash completo.")
    _append_if(risks, not custody, "Riesgo probatorio: no hay cadena de custodia documentada.")
    _append_if(risks, not approved_legal, "Riesgo juridico: no hay normas validadas por analista.")
    _append_if(risks, bool(blockchain) and not any(getattr(item, "evidence_id", None) for item in blockchain), "Riesgo blockchain: trazabilidad sin evidencia vinculada.")
    _append_if(risks, case.status == "cerrado" and missing, "Caso cerrado con brechas operativas pendientes de revisar.")

    contradictions = []
    _append_if(contradictions, case.status == "cerrado" and not reports, "El caso figura cerrado pero no tiene informe generado.")
    _append_if(contradictions, bool(approved_legal) and not evidence, "Existe encuadre legal aprobado sin evidencia cargada.")
    _append_if(contradictions, bool(findings) and not evidence, "Existen hallazgos sin inventario de evidencia digital.")
    _append_if(contradictions, bool(presentations) and not reports, "Existe exposicion oral sin informe fuente asociado al caso.")
    _append_if(contradictions, bool(damage_items) and not any(getattr(item, "supporting_evidence", "") for item in damage_items), "Hay rubros de dano sin soporte documental indicado.")

    next_steps = []
    if missing:
        next_steps.extend(missing[:5])
    else:
        next_steps.extend(
            [
                "Revisar consistencia entre hallazgos, normas y conclusion final.",
                "Guardar snapshot actualizado del caso, informe y exposicion.",
                "Preparar exportacion final con manifiesto y anexos.",
            ]
        )
    _append_if(next_steps, bool(notes) and not edges, "Construir grafo del caso para conectar notas, evidencia e informes.")

    memory_highlights = [
        f"{note.note_type}: {note.title}" for note in notes[:8]
    ]
    if not memory_highlights:
        memory_highlights.append("Todavia no hay memoria persistente asociada al caso.")

    readiness_score = 0
    readiness_score += 15 if case.description else 0
    readiness_score += 20 if evidence else 0
    readiness_score += 15 if evidence and len(hashed_evidence) == len(evidence) else 0
    readiness_score += 15 if custody else 0
    readiness_score += 15 if approved_legal else 0
    readiness_score += 10 if reports else 0
    readiness_score += 10 if notes else 0
    if contradictions:
        readiness_score -= min(20, len(contradictions) * 5)
    readiness_score = max(0, min(100, readiness_score))
    readiness = "listo" if readiness_score >= 85 else "parcial" if readiness_score >= 55 else "incompleto"
    confidence = "alta" if readiness_score >= 80 and not contradictions else "media" if readiness_score >= 50 else "baja"

    return MindCaseBrief(
        case_id=case.id,
        case_code=case.case_code,
        title=case.title,
        readiness=f"{readiness} ({readiness_score}/100)",
        confidence=confidence,
        known_facts=known_facts,
        missing_information=missing,
        risks=risks,
        contradictions=contradictions,
        recommended_next_steps=next_steps,
        memory_highlights=memory_highlights,
        graph_summary={
            "nodes": len(nodes),
            "edges": len(edges),
            "notes": len(notes),
            "evidence": len(evidence),
            "findings": len(findings),
            "legal_mappings": len(legal),
        },
    )


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
