from fastapi import APIRouter, Depends
from sqlalchemy import desc
from sqlalchemy.orm import Session

from operia.cases.models import Case
from operia.core.database import get_db
from operia.identity.models import User

router = APIRouter()


@router.get("/")
def status() -> dict[str, object]:
    return {
        "module": "Users & Cases",
        "status": "legacy-compatible",
        "canonical_modules": ["/api/identity", "/api/cases"],
        "description": "Compatibility surface backed by canonical identity and cases modules.",
    }


@router.get("/cases")
def list_cases(db: Session = Depends(get_db)) -> list[dict[str, object]]:
    cases = db.query(Case).order_by(desc(Case.updated_at)).limit(50).all()
    return [
        {
            "id": item.id,
            "case_code": item.case_code,
            "title": item.title,
            "status": item.status,
            "organization_id": item.organization_id,
        }
        for item in cases
    ]


@router.get("/users")
def list_users(db: Session = Depends(get_db)) -> list[dict[str, object]]:
    users = db.query(User).order_by(User.name).limit(50).all()
    return [
        {
            "id": item.id,
            "name": item.name,
            "email": item.email,
            "role": item.role,
            "organization_id": item.organization_id,
        }
        for item in users
    ]
