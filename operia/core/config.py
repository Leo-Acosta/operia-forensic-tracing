from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, SecretStr


class Settings(BaseSettings):
    app_name: str = "OPERIA Forensic Tracing"
    env: str = "local"
    api_prefix: str = "/api"
    database_url: str = "sqlite:///./storage/operia_forensic_tracing.db"
    storage_dir: Path = Path("./storage")
    mobile_import_max_bytes: int = Field(default=5 * 1024 * 1024, ge=1, le=50 * 1024 * 1024)
    mobile_job_timeout_seconds: int = Field(default=30, ge=1, le=300)
    mobile_storage_quota_bytes: int = Field(default=128 * 1024 * 1024, ge=5 * 1024 * 1024, le=2 * 1024 * 1024 * 1024)
    connector_allowed_hosts: list[str] = []
    auth_signing_key: SecretStr | None = None
    local_ai_enabled: bool = False
    local_ai_gateway_enabled: bool = False
    local_ai_allowed_models: list[str] = ["mistral"]
    local_recovery_enabled: bool = False
    http_max_concurrent_requests: int = Field(default=8, ge=1, le=64)
    http_max_body_bytes: int = Field(default=8 * 1024 * 1024, ge=1024, le=32 * 1024 * 1024)
    http_requests_per_minute: int = Field(default=240, ge=10, le=10000)
    http_auth_per_minute: int = Field(default=20, ge=1, le=1000)
    cors_origins: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
        "http://localhost:5175",
        "http://127.0.0.1:5175",
        "http://localhost:5176",
        "http://127.0.0.1:5176",
        "http://localhost:5177",
        "http://127.0.0.1:5177",
        "http://localhost:5178",
        "http://127.0.0.1:5178",
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
