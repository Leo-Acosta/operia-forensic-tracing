from fastapi import APIRouter

from operia.core.config import settings

router = APIRouter()


@router.get("/")
def read_settings() -> dict[str, object]:
    return {
        "app_name": settings.app_name,
        "env": settings.env,
        "api_prefix": settings.api_prefix,
        "storage_dir": str(settings.storage_dir),
        "database_url": settings.database_url,
    }

