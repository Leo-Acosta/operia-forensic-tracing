from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "OPERIA Forensic Tracing"
    env: str = "local"
    api_prefix: str = "/api"
    database_url: str = "sqlite:///./storage/operia_forensic_tracing.db"
    storage_dir: Path = Path("./storage")
    cors_origins: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
    ]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="OPERIA_",
        case_sensitive=False,
    )

    @property
    def evidence_dir(self) -> Path:
        return self.storage_dir / "evidence"

    @property
    def uploads_dir(self) -> Path:
        return self.storage_dir / "uploads"

    @property
    def exports_dir(self) -> Path:
        return self.storage_dir / "exports"

    @property
    def maps_dir(self) -> Path:
        return self.storage_dir / "maps"

    @property
    def temp_dir(self) -> Path:
        return self.storage_dir / "temp"


@lru_cache
def get_settings() -> Settings:
    value = Settings()
    for directory in (
        value.storage_dir,
        value.evidence_dir,
        value.uploads_dir,
        value.exports_dir,
        value.maps_dir,
        value.temp_dir,
    ):
        directory.mkdir(parents=True, exist_ok=True)
    return value


settings = get_settings()

