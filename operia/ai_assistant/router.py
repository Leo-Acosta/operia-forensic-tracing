from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from operia.ai_assistant.prompts import build_forensic_prompt
from operia.ai_assistant.service import case_context_for_prompt, legal_context_for_prompt
from operia.ai_assistant.models import AIInteraction
from operia.ai_assistant.ollama_client import OllamaUnavailable, generate_with_ollama
from operia.cases.models import Case
from operia.core.database import get_db
from operia.identity.dependencies import CurrentUser, require_permission
from operia.legal_knowledge.models import LegalMapping
from operia.legal_knowledge.service import ensure_legal_articles, recommend_legal_profile

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
    from operia.core.config import settings
    from operia.security.context import connector_scope
    from operia.security.sandbox_runtime import status as sandbox_status
    scope = connector_scope.get()
    authorized = bool(scope and scope.local_ai and model_name in scope.local_ai_models)
    ready = authorized and settings.local_ai_enabled and settings.local_ai_gateway_enabled and model_name in settings.local_ai_allowed_models and sandbox_status()["runtime_verified"]
    return {
        "provider": "ollama",
        "model": model_name,
        "available": False,
        "gateway_ready": bool(ready),
        "provider_probed": False,
        "mode": "gateway_ready" if ready else "offline_degraded",
        "external_api_used": False,
    }


@router.post("/assist")
def assist(
    payload: dict,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("ai:use")),
):
    prompt = str(payload.get("prompt") or "")
    model_name = str(payload.get("model_name") or "mistral")
    case = db.get(Case, payload.get("case_id")) if payload.get("case_id") else None
    from operia.security.context import connector_scope
    scope = connector_scope.get()
    if scope and scope.case_id is not None and (case is None or case.id != scope.case_id):
        raise HTTPException(422, "El caso debe estar declarado en la solicitud de IA")
    include_context = payload.get("include_case_context", False)
    if type(include_context) is not bool:
        raise HTTPException(422, "include_case_context debe ser booleano")
    if include_context and case is None:
        raise HTTPException(422, "Se requiere caso para incluir contexto")
    if len(prompt.encode()) > 32 * 1024:
        raise HTTPException(422, "Prompt demasiado extenso")
    legal_context = legal_context_for_prompt(db, prompt)
    case_context = case_context_for_prompt(case, db) if include_context else ""
    guarded_prompt = build_forensic_prompt(prompt, legal_context=legal_context, case_context=case_context)
    if len(guarded_prompt.encode()) > 64 * 1024:
        raise HTTPException(422, "El contexto excede el limite de la pasarela")
    interaction = AIInteraction(
        organization_id=current_user.organization_id,
        user_id=current_user.id,
        case_id=payload.get("case_id"),
        provider="ollama",
        model_name=model_name,
        task_type=str(payload.get("task_type") or "forensic_assistance"),
        prompt=guarded_prompt,
        status="pending",
        requires_human_review=True,
        safety_notes="Pasarela local sin herramientas ni memoria conversacional. Contexto del caso incluido: " + str(include_context) + ". Requiere revision humana.",
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
def case_recommendations(
    case_id: int,
    payload: dict | None = None,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("ai:use")),
):
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


@router.post("/case/{case_id}/legal-typification")
def legal_typification(
    case_id: int,
    payload: dict | None = None,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("ai:use")),
):
    case = db.get(Case, case_id)
    if not case:
        return {"case_id": case_id, "error": "Caso no encontrado"}
    payload = payload or {}
    ensure_legal_articles(db)
    focus = str(payload.get("focus") or "")
    incident_text = " ".join([case.incident_type or "", case.title or "", case.description or "", focus]).strip()
    profile_result = recommend_legal_profile(db, incident_text)
    recommendations = profile_result.get("recommendations", [])
    principal = next((item for item in recommendations if item.get("legal_role") == "principal"), recommendations[0] if recommendations else None)
    connected = [item for item in recommendations if not principal or item.get("article_id") != principal.get("article_id")]
    evidence_count = len(case.evidence)
    custody_count = len(case.actions)
    approved_mappings = [item for item in case.legal_mappings if item.decision_status == "aprobado"]
    suggested_mappings = []

    readiness_score = 25
    readiness_score += 20 if principal else 0
    readiness_score += min(evidence_count, 3) * 10
    readiness_score += 15 if custody_count else 0
    readiness_score += 10 if approved_mappings else 0
    readiness_score = min(readiness_score, 100)
    confidence = "alto" if readiness_score >= 75 else "medio" if readiness_score >= 50 else "bajo"
    decision_level = "tipificacion asistida con base legal registrada"
    if not evidence_count:
        decision_level = "tipificacion preliminar sin soporte probatorio suficiente"
    elif not approved_mappings:
        decision_level = "tipificacion sugerida pendiente de aprobacion del analista"

    if payload.get("create_suggestions"):
        for item in recommendations[:5]:
            exists = (
                db.query(LegalMapping)
                .filter_by(case_id=case.id, article_id=item.get("article_id"))
                .order_by(LegalMapping.created_at.desc())
                .first()
            )
            if exists:
                suggested_mappings.append(exists.id)
                continue
            mapping = LegalMapping(
                case_id=case.id,
                article_id=item.get("article_id"),
                legal_area="Tipificacion penal argentina asistida",
                norm_reference=item.get("reference", ""),
                source_id=None,
                analysis=item.get("applicability_to_case") or item.get("why") or "",
                verification_status="sugerido_por_motor_ia_local",
                confidence_level=item.get("confidence", "medio"),
                requires_human_review=True,
                decision_status="sugerido",
                analyst_name=str(payload.get("analyst_name") or ""),
                analyst_rationale="Sugerencia generada por motor de tipificacion asistida contra biblioteca legal registrada.",
                legal_role=item.get("legal_role", ""),
                applicability_to_case=item.get("applicability_to_case", ""),
                probatory_limits=item.get("probatory_limits", ""),
            )
            db.add(mapping)
            db.flush()
            suggested_mappings.append(mapping.id)
        db.commit()

    return {
        "case_id": case.id,
        "case_code": case.case_code,
        "incident_text": incident_text,
        "profile": profile_result.get("profile"),
        "principal_typification": principal,
        "connected_typifications": connected[:6],
        "confidence": confidence,
        "readiness_score": readiness_score,
        "decision_level": decision_level,
        "evidence_snapshot": {
            "evidence_count": evidence_count,
            "custody_actions": custody_count,
            "approved_legal_mappings": len(approved_mappings),
        },
        "missing_for_stronger_typification": [
            item
            for item in [
                "Cargar evidencia digital preservada." if not evidence_count else "",
                "Registrar cadena de custodia." if not custody_count else "",
                "Aprobar el mapeo legal sugerido desde biblioteca registrada." if not approved_mappings else "",
                "Vincular evidencia concreta a cada elemento del tipo penal." if not approved_mappings else "",
            ]
            if item
        ],
        "recommended_measures": (profile_result.get("profile") or {}).get("recommended_measures", []),
        "suggested_mapping_ids": suggested_mappings,
        "registered_sources_only": True,
        "human_review_required": True,
        "external_api_used": False,
    }
