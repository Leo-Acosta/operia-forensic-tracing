import sys
import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from apps.api.main import app
from operia.core.bootstrap import init_platform_schema
from operia.core.database import Base, get_db
from operia.legal_knowledge.bootstrap import init_legal_knowledge_module
from operia.legal_report.bootstrap import init_legal_report_module
from operia.mind.bootstrap import init_mind_module


@pytest.fixture()
def client(monkeypatch):
    tmp_root = ROOT / "storage" / "test_runs" / uuid.uuid4().hex
    tmp_root.mkdir(parents=True, exist_ok=True)
    db_path = tmp_root / "operia_test.db"
    storage_dir = tmp_root / "storage"
    for child in ("exports", "uploads", "evidence", "maps", "temp"):
        (storage_dir / child).mkdir(parents=True, exist_ok=True)

    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    import operia.core.bootstrap as bootstrap
    import operia.core.database as database
    import operia.legal_report.config as legal_config
    import operia.legal_report.bootstrap as legal_bootstrap
    import operia.legal_knowledge.bootstrap as legal_knowledge_bootstrap
    import operia.mind.bootstrap as mind_bootstrap

    monkeypatch.setattr(database, "engine", engine)
    monkeypatch.setattr(database, "SessionLocal", TestingSessionLocal)
    monkeypatch.setattr(bootstrap, "engine", engine)
    monkeypatch.setattr(legal_bootstrap, "SessionLocal", TestingSessionLocal)
    monkeypatch.setattr(legal_knowledge_bootstrap, "SessionLocal", TestingSessionLocal)
    monkeypatch.setattr(mind_bootstrap, "SessionLocal", TestingSessionLocal)
    monkeypatch.setattr(legal_config, "EXPORT_DIR", storage_dir / "exports")
    monkeypatch.setattr(legal_config, "UPLOAD_DIR", storage_dir / "uploads")

    import operia.exports.service as export_service
    import operia.mind.vault as mind_vault

    monkeypatch.setattr(export_service.settings, "storage_dir", storage_dir)
    monkeypatch.setattr(mind_vault.settings, "storage_dir", storage_dir)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    init_platform_schema()
    init_legal_report_module()
    init_legal_knowledge_module()
    init_mind_module()
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture()
def admin_headers(client):
    response = client.post(
        "/api/identity/bootstrap-admin",
        json={
            "organization_name": "OPERIA Test",
            "organization_slug": "operia-test",
            "name": "Test Admin",
            "email": "admin@test.local",
            "password": "TestPassword123!",
        },
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
