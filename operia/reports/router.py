from fastapi import APIRouter

from operia.shared.placeholders import module_status

router = APIRouter()


@router.get("/")
def status() -> dict[str, str]:
    return module_status("Reports", "Canonical reports, sections, versions, reviews, and presentation source material.")

