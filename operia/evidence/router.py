from fastapi import APIRouter

from operia.shared.placeholders import module_status

router = APIRouter()


@router.get("/")
def status() -> dict[str, str]:
    return module_status("Evidence", "Evidence vault, uploads, hashes, attachments, and custody actions.")

