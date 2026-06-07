from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from operia.ai_security.models import AIModelEvaluation, AIModelTestRun
from operia.ai_security.reporting import evaluation_markdown
from operia.ai_security.scoring import recommendation_from_risk, risk_level_from_score
from operia.ai_security.service import catalog_entry, default_test_prompt, run_controlled_model_test
from operia.ai_security.tests_catalog import AI_SECURITY_TESTS
from operia.core.database import get_db
from operia.identity.dependencies import CurrentUser, require_permission

router = APIRouter()


def as_dict(obj) -> dict:
    return {column.name: getattr(obj, column.name) for column in obj.__table__.columns}


@router.get("/")
def status() -> dict[str, object]:
    return {
        "module": "AI Security",
        "status": "canonical",
        "description": "Controlled AI model evaluations with logs, reports, and risk scoring.",
        "conclusion_policy": "Bajo estas condiciones locales, aisladas y auditadas, el riesgo observado es bajo/medio/alto.",
    }


@router.get("/tests")
def list_tests() -> list[dict[str, str]]:
    return AI_SECURITY_TESTS


@router.post("/evaluations")
def create_evaluation(
    payload: dict,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("audit:read")),
):
    run_tests = bool(payload.get("run_tests", False))
    requested_tests = payload.get("tests") if isinstance(payload.get("tests"), list) else [item["code"] for item in AI_SECURITY_TESTS]
    model_name = str(payload.get("model_name") or "mistral")
    test_results = []
    if run_tests:
        for test_code in requested_tests:
            response, test_score, severity, passed, notes = run_controlled_model_test(model_name, str(test_code))
            test_results.append((str(test_code), response, test_score, severity, passed, notes))
    score = int(payload.get("overall_score") or (sum(item[2] for item in test_results) / len(test_results) if test_results else 70))
    risk = risk_level_from_score(score)
    evaluation = AIModelEvaluation(
        organization_id=current_user.organization_id or payload.get("organization_id"),
        provider=str(payload.get("provider") or "ollama"),
        model_name=model_name,
        model_identifier=str(payload.get("model_identifier") or ""),
        environment=str(payload.get("environment") or "local"),
        network_blocked=bool(payload.get("network_blocked", True)),
        tools_enabled=bool(payload.get("tools_enabled", False)),
        overall_score=score,
        risk_level=risk,
        recommendation=recommendation_from_risk(risk),
        conclusion=(
            "Bajo estas condiciones locales, aisladas y auditadas, "
            f"el riesgo observado es {risk}."
        ),
    )
    db.add(evaluation)
    db.flush()
    source_results = test_results or [
        (str(test_code), "", score, "medio", score >= 65, "Pendiente de ejecucion controlada detallada.")
        for test_code in requested_tests
    ]
    for test_code, response, test_score, severity, passed, notes in source_results:
        test = catalog_entry(test_code)
        db.add(
            AIModelTestRun(
                organization_id=evaluation.organization_id,
                evaluation_id=evaluation.id,
                test_code=test["code"],
                test_name=test["name"],
                category=test["category"],
                prompt=default_test_prompt(test["code"]),
                response=response,
                observed_behavior=notes,
                severity=severity,
                passed=passed,
                score=test_score,
                notes=notes,
            )
        )
    db.commit()
    db.refresh(evaluation)
    return as_dict(evaluation)


@router.get("/evaluations")
def list_evaluations(
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("audit:read")),
):
    query = db.query(AIModelEvaluation)
    if current_user.organization_id:
        query = query.filter(AIModelEvaluation.organization_id.in_([current_user.organization_id, None]))
    return [as_dict(row) for row in query.order_by(AIModelEvaluation.created_at.desc()).all()]


@router.get("/evaluations/{evaluation_id}/report")
def read_evaluation_report(
    evaluation_id: int,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("audit:read")),
):
    evaluation = db.get(AIModelEvaluation, evaluation_id)
    if not evaluation:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Evaluacion no encontrada")
    if current_user.organization_id and evaluation.organization_id not in {current_user.organization_id, None}:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Evaluación no encontrada")
    tests = db.query(AIModelTestRun).filter_by(evaluation_id=evaluation_id).order_by(AIModelTestRun.id.asc()).all()
    return {"markdown": evaluation_markdown(evaluation, tests)}
