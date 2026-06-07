from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from operia.audit.service import write_audit
from operia.cases.models import Case
from operia.core.database import get_db
from operia.identity.dependencies import CurrentUser, require_permission
from operia.rubrics.service import (
    evaluation_payload,
    latest_case_evaluation,
    list_rubrics,
    persist_case_evaluation,
    rubric_definition,
)
from operia.shared.crud import get_or_404

router = APIRouter()


@router.get("/")
def get_rubrics():
    return list_rubrics()


@router.get("/report-2026")
def get_report_2026_rubric():
    return rubric_definition()


@router.get("/case/{case_id}/score")
def get_case_rubric_score(case_id: int, db: Session = Depends(get_db)):
    get_or_404(db, Case, case_id)
    item = latest_case_evaluation(db, case_id)
    if not item:
        raise HTTPException(status_code=404, detail="No hay evaluación de rúbrica para este caso")
    return evaluation_payload(item)


@router.post("/case/{case_id}/evaluate")
def evaluate_case_rubric_endpoint(
    case_id: int,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("reports:write")),
):
    case = get_or_404(db, Case, case_id)
    item = persist_case_evaluation(db, case, evaluated_by=current_user.name)
    write_audit(
        db,
        "evaluate_report_rubric",
        "rubrics",
        current_user,
        case_id=case_id,
        entity_type="rubric_evaluation",
        entity_id=str(item.id),
        details=f"{item.rubric_title}: {item.total_score}/{item.max_score}",
    )
    db.commit()
    db.refresh(item)
    return evaluation_payload(item)
