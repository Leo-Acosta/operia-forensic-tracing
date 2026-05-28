from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from operia.ai_assistant.prompts import build_forensic_prompt
from operia.ai_assistant.service import case_context_for_prompt, legal_context_for_prompt
from operia.ai_assistant.models import AIInteraction
from operia.ai_assistant.ollama_client import OllamaUnavailable, generate_with_ollama
from operia.cases.models import Case
from operia.core.database import get_db

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
