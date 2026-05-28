from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from operia.audit.service import write_audit
from operia.core.database import get_db
from operia.identity.dependencies import CurrentUser, get_optional_user
from operia.evidence.models import Evidence
from operia.legal_knowledge.models import LegalArticle, LegalDoctrine, LegalMapping, LegalMappingEvidence, LegalPrecedent, LegalSource
from operia.legal_knowledge.service import (
    article_context,
    build_legal_probatory_matrix,
    ensure_legal_articles,
    get_attack_profile,
    legal_article_checklist,
    legal_quality_control,
    list_attack_profiles,
    recommend_legal_profile,
    search_articles,
    verify_registered_sources,
    verify_source_url,
)
from operia.legal_knowledge.schemas import (
    LegalDoctrineCreate,
    LegalDoctrineRead,
    LegalMappingCreate,
    LegalMappingDecisionCreate,
    LegalMappingEvidenceCreate,
    LegalMappingEvidenceRead,
    LegalMappingRead,
    LegalPrecedentCreate,
    LegalPrecedentRead,
    LegalSourceCreate,
    LegalSourceRead,
)
from operia.legal_report.services.legal_knowledge_base import sync_official_sources
from operia.shared.time import utcnow
from operia.shared.crud import get_or_404, update_from_payload

router = APIRouter()


@router.get("/")
def status() -> dict[str, object]:
    return {
        "module": "Legal Knowledge",
        "status": "canonical",
        "description": "Versioned Argentine legal sources, articles, citations, and legal mappings.",
    }


@router.post("/sources", response_model=LegalSourceRead)
def create_legal_source(payload: LegalSourceCreate, db: Session = Depends(get_db)):
    item = LegalSource(**payload.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.get("/sources", response_model=list[LegalSourceRead])
def list_legal_sources(db: Session = Depends(get_db)):
    return db.query(LegalSource).order_by(LegalSource.title).all()


@router.post("/sources/sync-official")
def sync_legal_sources(db: Session = Depends(get_db)):
    updated = sync_official_sources(db)
    db.commit()
    return {"updated": updated, "message": "Fuentes oficiales sincronizadas y marcadas segun verificacion disponible."}


@router.post("/sources/verify")
def verify_sources(persist: bool = False, db: Session = Depends(get_db)):
    results = verify_registered_sources(db, persist=persist)
    if persist:
        db.commit()
    return {"checked": len(results), "results": results}


@router.post("/sources/verify-url")
def verify_url(payload: dict):
    return verify_source_url(str(payload.get("url") or ""))


@router.put("/sources/{source_id}", response_model=LegalSourceRead)
def update_legal_source(source_id: int, payload: LegalSourceCreate, db: Session = Depends(get_db)):
    item = update_from_payload(get_or_404(db, LegalSource, source_id), payload)
    db.commit()
    db.refresh(item)
    return item


@router.get("/articles")
def list_articles(source_id: int | None = None, q: str | None = None, db: Session = Depends(get_db)):
    if q:
        return search_articles(db, q)
    query = db.query(LegalArticle)
    if source_id:
        query = query.filter_by(source_id=source_id)
    return query.order_by(LegalArticle.code, LegalArticle.article_number).all()


@router.get("/articles/{article_id}/context")
def get_article_context(article_id: int, crime_type: str = "", db: Session = Depends(get_db)):
    article = get_or_404(db, LegalArticle, article_id)
    return {"article": article, "context": article_context(db, article, crime_type=crime_type)}


@router.get("/articles/{article_id}/checklist")
def get_article_checklist(article_id: int, db: Session = Depends(get_db)):
    article = get_or_404(db, LegalArticle, article_id)
    return legal_article_checklist(article)


@router.post("/articles/seed")
def seed_articles(db: Session = Depends(get_db)):
    created = ensure_legal_articles(db)
    db.commit()
    return {"created": created, "message": "Biblioteca legal inicial verificada."}


@router.post("/articles/recommend")
def recommend_articles(payload: dict, db: Session = Depends(get_db)):
    incident_text = str(payload.get("incident_text") or payload.get("query") or "")
    result = recommend_legal_profile(db, incident_text)
    result["disclaimer"] = "Recomendacion preliminar basada solo en biblioteca legal registrada. Requiere revision profesional."
    return result


@router.get("/attack-types")
def attack_types() -> list[dict[str, object]]:
    return list_attack_profiles()


@router.get("/attack-types/{attack_type}")
def attack_type_profile(attack_type: str):
    profile = get_attack_profile(attack_type)
    return {
        "value": profile.key,
        "label": profile.label,
        "query": profile.query,
        "legal_theory": profile.legal_theory,
        "required_evidence": list(profile.required_evidence),
        "recommended_measures": list(profile.recommended_measures),
        "article_refs": [
            {
                "code": ref.code,
                "article_number": ref.article_number,
                "subsection": ref.subsection,
                "role": ref.role,
                "applicability": ref.applicability,
                "limits": ref.limits,
                "confidence": ref.confidence,
            }
            for ref in profile.article_refs
        ],
    }


@router.post("/mappings", response_model=LegalMappingRead)
def create_legal_mapping(payload: LegalMappingCreate, db: Session = Depends(get_db)):
    item = LegalMapping(**payload.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.post("/mappings/decision", response_model=LegalMappingRead)
def decide_legal_mapping(
    payload: LegalMappingDecisionCreate,
    db: Session = Depends(get_db),
    current_user: CurrentUser | None = Depends(get_optional_user),
):
    decision = payload.decision_status.lower().strip()
    if decision not in {"aprobado", "descartado"}:
        decision = "aprobado" if decision in {"approve", "approved"} else "descartado"

    article = get_or_404(db, LegalArticle, payload.article_id)
    source_id = article.source_id
    norm_reference = f"{article.code} art. {article.article_number}{' inc. ' + article.subsection if article.subsection else ''}"
    existing = (
        db.query(LegalMapping)
        .filter_by(case_id=payload.case_id, article_id=article.id)
        .order_by(LegalMapping.created_at.desc())
        .first()
    )
    analysis_parts = [
        payload.applicability_to_case or article.objective_elements,
        payload.probatory_limits,
        payload.analyst_rationale,
    ]
    analysis = "\n".join(part for part in analysis_parts if part).strip() or article.objective_elements
    item = existing or LegalMapping(
        case_id=payload.case_id,
        article_id=article.id,
        legal_area="Encuadre legal argentino",
        norm_reference=norm_reference,
        source_id=source_id,
        analysis=analysis,
    )
    item.legal_area = "Encuadre legal argentino"
    item.norm_reference = norm_reference
    item.source_id = source_id
    item.analysis = analysis
    item.verification_status = "aprobado_por_analista" if decision == "aprobado" else "descartado_por_analista"
    item.confidence_level = payload.confidence_level
    item.requires_human_review = decision != "aprobado"
    item.decision_status = decision
    item.analyst_name = payload.analyst_name or (current_user.name if current_user else "")
    item.analyst_rationale = payload.analyst_rationale
    item.legal_role = payload.legal_role
    item.applicability_to_case = payload.applicability_to_case
    item.probatory_limits = payload.probatory_limits
    item.decided_at = utcnow().isoformat()
    if not existing:
        db.add(item)
        db.flush()
    write_audit(
        db,
        "approve_legal_mapping" if decision == "aprobado" else "reject_legal_mapping",
        "legal_knowledge",
        current_user,
        case_id=payload.case_id,
        entity_type="legal_mapping",
        entity_id=str(item.id),
        details=f"{norm_reference}: {decision}",
    )
    db.commit()
    db.refresh(item)
    return item


@router.get("/case/{case_id}/mappings", response_model=list[LegalMappingRead])
def list_case_mappings(case_id: int, db: Session = Depends(get_db)):
    return db.query(LegalMapping).filter_by(case_id=case_id).order_by(LegalMapping.created_at.desc()).all()


@router.post("/mappings/evidence", response_model=LegalMappingEvidenceRead)
def link_mapping_evidence(
    payload: LegalMappingEvidenceCreate,
    db: Session = Depends(get_db),
    current_user: CurrentUser | None = Depends(get_optional_user),
):
    mapping = get_or_404(db, LegalMapping, payload.legal_mapping_id)
    evidence = get_or_404(db, Evidence, payload.evidence_id)
    if mapping.case_id != payload.case_id or evidence.case_id != payload.case_id:
        raise HTTPException(status_code=400, detail="La evidencia y el mapeo legal deben pertenecer al mismo caso")
    existing = (
        db.query(LegalMappingEvidence)
        .filter_by(legal_mapping_id=mapping.id, evidence_id=evidence.id)
        .first()
    )
    item = existing or LegalMappingEvidence(
        case_id=payload.case_id,
        legal_mapping_id=mapping.id,
        evidence_id=evidence.id,
    )
    item.linked_by = payload.linked_by or (current_user.name if current_user else "")
    item.link_rationale = payload.link_rationale
    item.legal_element = payload.legal_element
    item.probatory_strength = payload.probatory_strength
    item.element_status = payload.element_status
    item.missing_evidence = payload.missing_evidence
    item.contradiction_risk = payload.contradiction_risk
    item.recommended_measure = payload.recommended_measure
    if not existing:
        db.add(item)
        db.flush()
    write_audit(
        db,
        "link_legal_mapping_evidence",
        "legal_knowledge",
        current_user,
        case_id=payload.case_id,
        entity_type="legal_mapping_evidence",
        entity_id=str(item.id),
        details=f"{mapping.norm_reference} <- evidencia #{evidence.id}",
    )
    db.commit()
    db.refresh(item)
    return item


@router.get("/case/{case_id}/mapping-evidence", response_model=list[LegalMappingEvidenceRead])
def list_case_mapping_evidence(case_id: int, db: Session = Depends(get_db)):
    return db.query(LegalMappingEvidence).filter_by(case_id=case_id).order_by(LegalMappingEvidence.created_at.desc()).all()


@router.get("/case/{case_id}/probatory-matrix")
def case_probatory_matrix(case_id: int, db: Session = Depends(get_db)):
    return build_legal_probatory_matrix(db, case_id)


@router.get("/case/{case_id}/quality-control")
def case_legal_quality_control(case_id: int, db: Session = Depends(get_db)):
    return legal_quality_control(db, case_id)


@router.delete("/mappings/evidence/{link_id}")
def unlink_mapping_evidence(
    link_id: int,
    db: Session = Depends(get_db),
    current_user: CurrentUser | None = Depends(get_optional_user),
):
    item = get_or_404(db, LegalMappingEvidence, link_id)
    case_id = item.case_id
    db.delete(item)
    write_audit(
        db,
        "unlink_legal_mapping_evidence",
        "legal_knowledge",
        current_user,
        case_id=case_id,
        entity_type="legal_mapping_evidence",
        entity_id=str(link_id),
    )
    db.commit()
    return {"deleted": True, "id": link_id}


@router.post("/precedents", response_model=LegalPrecedentRead)
def create_precedent(payload: LegalPrecedentCreate, db: Session = Depends(get_db)):
    item = LegalPrecedent(**payload.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.get("/precedents", response_model=list[LegalPrecedentRead])
def list_precedents(article_id: int | None = None, crime_type: str | None = None, db: Session = Depends(get_db)):
    query = db.query(LegalPrecedent).filter_by(verified=True)
    if article_id is not None:
        query = query.filter_by(article_id=article_id)
    if crime_type:
        query = query.filter(LegalPrecedent.related_crime_type.ilike(f"%{crime_type}%"))
    return query.order_by(LegalPrecedent.created_at.desc()).all()


@router.post("/doctrine", response_model=LegalDoctrineRead)
def create_doctrine(payload: LegalDoctrineCreate, db: Session = Depends(get_db)):
    item = LegalDoctrine(**payload.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.get("/doctrine", response_model=list[LegalDoctrineRead])
def list_doctrine(article_id: int | None = None, crime_type: str | None = None, db: Session = Depends(get_db)):
    query = db.query(LegalDoctrine).filter_by(verified=True)
    if article_id is not None:
        query = query.filter_by(article_id=article_id)
    if crime_type:
        query = query.filter(LegalDoctrine.related_crime_type.ilike(f"%{crime_type}%"))
    return query.order_by(LegalDoctrine.created_at.desc()).all()
