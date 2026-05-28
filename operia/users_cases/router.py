from fastapi import APIRouter

from operia.shared.placeholders import module_status

router = APIRouter()


@router.get("/")
def status() -> dict[str, str]:
    return module_status("Users & Cases", "Shared users, roles, cases, teams, and permissions.")


@router.get("/cases")
def list_cases_placeholder() -> list[dict[str, str]]:
    return [
        {
            "case_code": "OP-TRACE-DEMO",
            "title": "Placeholder case for OPERIA Forensic Tracing",
            "status": "scaffold",
        }
    ]

