from fastapi import APIRouter

from operia.shared.placeholders import module_status

router = APIRouter()


@router.get("/")
def status() -> dict[str, str]:
    return module_status("Exports", "PDF, DOCX, HTML, Markdown, CSV, JSON, and map export workflows.")

