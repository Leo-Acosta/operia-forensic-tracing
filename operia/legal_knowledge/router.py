from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from operia.core.database import get_db
from operia.legal_knowledge.models import LegalArticle, LegalMapping, LegalSource
from operia.legal_knowledge.service import (
    ensure_legal_articles,
    recommend_articles_for_incident,
    search_articles,
    verify_registered_sources,
    verify_source_url,
)
from operia.legal_knowledge.schemas import LegalMappingCreate, LegalMappingRead, LegalSourceCreate, LegalSourceRead
from operia.legal_report.services.legal_knowledge_base import sync_official_sources
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


@router.post("/articles/seed")
def seed_articles(db: Session = Depends(get_db)):
    created = ensure_legal_articles(db)
    db.commit()
    return {"created": created, "message": "Biblioteca legal inicial verificada."}


@router.post("/articles/recommend")
def recommend_articles(payload: dict, db: Session = Depends(get_db)):
    incident_text = str(payload.get("incident_text") or payload.get("query") or "")
    return {
        "incident_text": incident_text,
        "recommendations": recommend_articles_for_incident(db, incident_text),
        "disclaimer": "Recomendacion automatizada preliminar. Requiere revision humana y verificacion de fuente oficial.",
    }


@router.post("/mappings", response_model=LegalMappingRead)
def create_legal_mapping(payload: LegalMappingCreate, db: Session = Depends(get_db)):
    item = LegalMapping(**payload.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.get("/case/{case_id}/mappings", response_model=list[LegalMappingRead])
def list_case_mappings(case_id: int, db: Session = Depends(get_db)):
    return db.query(LegalMapping).filter_by(case_id=case_id).order_by(LegalMapping.created_at.desc()).all()
