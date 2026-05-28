from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from operia.ai_assistant.prompts import build_forensic_prompt
from operia.ai_assistant.service import case_context_for_prompt, legal_context_for_prompt
from operia.ai_assistant.models import AIInteraction
from operia.ai_assistant.ollama_client import OllamaUnavailable, generate_with_ollama
from operia.cases.models import Case
from operia.core.database import get_db
from operia.legal_knowledge.service import recommend_legal_profile

router = APIRouter()


def as_dict(obj) -> dict:
    return {column.name: getattr(obj, column.name) for column in obj.__table__.columns}


@router.get("/")
def status() -> dict[str, object]:
    return {
        "module": "AI Assistant",
        "status": "canonical",
        "provider": "ollama",
        "default_model": "mistral",
        "description": "Local AI assistance with mandatory human review and source-aware legal analysis.",
    }


@router.get("/health")
def ai_health(model_name: str = "mistral") -> dict[str, object]:
    try:
        response = generate_with_ollama("Responde solo: OK", model=model_name, timeout=2)
        available = bool(response.strip())
    except OllamaUnavailable as exc:
        return {
            "provider": "ollama",
            "model": model_name,
            "available": False,
            "mode": "offline_degraded",
            "message": str(exc),
            "external_api_used": False,
        }
    return {
        "provider": "ollama",
        "model": model_name,
        "available": available,
        "mode": "local",
        "external_api_used": False,
    }


@router.post("/assist")
def assist(payload: dict, db: Session = Depends(get_db)):
    prompt = str(payload.get("prompt") or "")
    model_name = str(payload.get("model_name") or "mistral")
    case = db.get(Case, payload.get("case_id")) if payload.get("case_id") else None
    legal_context = legal_context_for_prompt(db, prompt)
    case_context = case_context_for_prompt(case)
    guarded_prompt = build_forensic_prompt(prompt, legal_context=legal_context, case_context=case_context)
    interaction = AIInteraction(
        organization_id=payload.get("organization_id"),
        user_id=payload.get("user_id"),
        case_id=payload.get("case_id"),
        provider="ollama",
        model_name=model_name,
        task_type=str(payload.get("task_type") or "forensic_assistance"),
        prompt=guarded_prompt,
        status="pending",
        requires_human_review=True,
        safety_notes="Asistencia automatizada. No sustituye revision humana.",
    )
    try:
        interaction.response = generate_with_ollama(guarded_prompt, model=model_name)
        interaction.status = "completed"
    except OllamaUnavailable as exc:
        interaction.response = ""
        interaction.status = "ollama_unavailable"
        interaction.safety_notes = str(exc)
    db.add(interaction)
    db.commit()
    db.refresh(interaction)
    return as_dict(interaction)


@router.post("/case/{case_id}/recommendations")
def case_recommendations(case_id: int, payload: dict | None = None, db: Session = Depends(get_db)):
    case = db.get(Case, case_id)
    if not case:
        return {"case_id": case_id, "error": "Caso no encontrado"}
    payload = payload or {}
    incident_text = " ".join([case.incident_type or "", case.description or "", str(payload.get("focus") or "")])
    legal_profile = recommend_legal_profile(db, incident_text)
    missing = []
    if not case.evidence:
        missing.append("Cargar evidencia digital preservada.")
    if not case.actions:
        missing.append("Registrar cadena de custodia.")
    if not case.legal_mappings:
        missing.append("Aprobar mapeo legal desde biblioteca registrada.")
    return {
        "case_id": case.id,
        "incident_type": case.incident_type,
        "legal_profile": legal_profile.get("profile"),
        "recommended_articles": legal_profile.get("recommendations", []),
        "operational_next_steps": missing
        or [
            "Verificar integridad de evidencia.",
            "Completar matriz legal-probatoria.",
            "Revisar informe antes de exportacion final sellada.",
        ],
        "human_review_required": True,
        "external_api_used": False,
    }
