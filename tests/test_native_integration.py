from pathlib import Path
from apps.api.main import app
from operia.identity.dependencies import CurrentUser, get_optional_user
from operia.forensic_jobs import worker
from operia.forensic_engine.canonical import sha256
from test_native_mobile_workflow import setup, enqueue, database_factory, native_review


def test_integration_preserves_revisions_and_scopes(client, admin_headers):
    root, acquisition, raw = setup(client, admin_headers)
    job = enqueue(client, admin_headers, root, acquisition)
    assert worker.run_once(database_factory(), timeout=15)
    path = root + f"/jobs/{job['id']}"
    result = client.get(path, headers=admin_headers).json()["result"]
    revision = client.post(path + "/reviews", headers=admin_headers,
        json=native_review([a["id"] for a in result["artifacts"]], rationale="Revisado <script>alert(1)</script> como texto no ejecutable")).json()
    url = path + f"/integrations?review_id={revision['id']}"
    response = client.post(url, headers=admin_headers)
    assert response.status_code == 200, response.text
    link = response.json()
    from operia.evidence.models import CustodyLedgerEntry
    with database_factory()() as db:
        entry = db.query(CustodyLedgerEntry).filter_by(action_id=link["custody_id"]).one()
        assert entry.actor_user_id == 1 and entry.version == 0
    assert client.post(url, headers=admin_headers).json() == link
    evidence = f"/api/evidence/{link['evidence_id']}"
    report = f"/api/reports/{link['report_id']}"
    assert client.get(evidence).status_code == 401
    assert client.get(evidence + "/download", headers=admin_headers).content == raw
    assert client.get(evidence + "/integrity", headers=admin_headers).json()["ok"]
    snapshot = client.get(report, headers=admin_headers).json()["markdown_content"]
    assert sha256(raw) in snapshot and str(revision["id"]) in snapshot
    for fmt in ("pdf", "docx", "markdown", "html"):
        exported = client.get(report + "/export/" + fmt, headers=admin_headers)
        assert exported.status_code == 200, exported.text
        assert exported.content
        from io import BytesIO
        if fmt == "pdf":
            from pypdf import PdfReader
            text = "".join(page.extract_text() for page in PdfReader(BytesIO(exported.content)).pages)
            assert link["snapshot_sha256"] in text
            assert "Revisado" in text
        if fmt == "docx":
            from docx import Document
            text = "\n".join(p.text for p in Document(BytesIO(exported.content)).paragraphs)
            assert link["snapshot_sha256"] in text and "Revisado" in text
        if fmt == "html":
            assert b"<script>" not in exported.content and b"&lt;script&gt;" in exported.content
    snapshot_url = path + f"/integrations/{link['id']}"
    preserved = client.get(snapshot_url, headers=admin_headers)
    assert sha256(preserved.content) == link["snapshot_sha256"]
    assert preserved.json()["review"]["id"] == revision["id"]
    assert client.delete(f"/api/cases/{acquisition['case_id']}", headers=admin_headers).status_code == 409
    assert client.delete(evidence, headers=admin_headers).status_code == 409
    assert client.put(report, headers=admin_headers, json={"title": "overwrite"}).status_code == 409
    assert client.get(report, headers=admin_headers).json()["markdown_content"] == snapshot
    client.post(path + "/reviews", headers=admin_headers,
        json=native_review([a["id"] for a in result["artifacts"]], rationale="Nueva revisión independiente preservada"))
    assert client.get(report, headers=admin_headers).json()["markdown_content"] == snapshot
    for org in (99999,):
        app.dependency_overrides[get_optional_user] = lambda: CurrentUser(1, org, "Otra", None, "admin")
        for suffix in (evidence, evidence + "/download", report, report + "/sections", report + "/versions", report + "/export/pdf"):
            assert client.get(suffix).status_code == 404, suffix
        assert client.post(url).status_code == 404
    app.dependency_overrides.pop(get_optional_user)


def test_canonical_case_reference_cannot_cross_cases(client, admin_headers):
    root, acquisition, _ = setup(client, admin_headers, code="FIRST")
    other, second, _ = setup(client, admin_headers, code="SECOND")
    evidence = client.post("/api/evidence", headers=admin_headers, json={"case_id": acquisition["case_id"], "description": "Original"}).json()
    assert client.post("/api/evidence/custody-actions", headers=admin_headers, json={
        "case_id": second["case_id"], "evidence_id": evidence["id"], "detailed_description": "Wrong case"}).status_code == 422
    assert client.put(f"/api/evidence/{evidence['id']}", headers=admin_headers, json={
        "case_id": second["case_id"], "description": "Moved"}).status_code in (409, 422)


def test_two_organizations_use_real_tokens_and_legacy_null_rows(client, admin_headers):
    from operia.identity.models import Organization, User
    from operia.identity.security import hash_password
    from operia.evidence.models import Evidence
    root, acquisition, raw = setup(client, admin_headers)
    case_id = acquisition["case_id"]
    with database_factory()() as db:
        org = Organization(name="Second tenant", slug="second")
        db.add(org)
        db.flush()
        db.add(User(organization_id=org.id, name="Other admin", email="other@test.local", role="admin",
            password_hash=hash_password("OtherPassword123!")))
        legacy = Evidence(case_id=case_id, organization_id=None, description="Historical unassigned child")
        db.add(legacy)
        db.commit()
        evidence_id = legacy.id
    response = client.post("/api/identity/login", json={"email": "other@test.local", "password": "OtherPassword123!"})
    assert response.status_code == 200, response.text
    other_headers = {"Authorization": "Bearer " + response.json()["access_token"]}
    assert client.get(f"/api/evidence/{evidence_id}", headers=admin_headers).status_code == 200
    for prefix in ("/api/evidence/case/", "/api/reports/case/", "/api/legal-knowledge/case/"):
        suffix = "/probatory-matrix" if "knowledge" in prefix else ""
        assert client.get(prefix + str(case_id) + suffix, headers=other_headers).status_code == 404
    assert client.get(f"/api/evidence/{evidence_id}", headers=other_headers).status_code == 404
    assert all(c["id"] != case_id for c in client.get("/api/cases", headers=other_headers).json())
    assert all(c["id"] != case_id for c in client.get("/api/users-cases/cases", headers=other_headers).json())
    assert all(u["email"] != "admin@test.local" for u in client.get("/api/users-cases/users", headers=other_headers).json())
    assert client.get("/api/dashboard", headers=other_headers).json()["metrics"]["evidence"] == 0
    assert client.post("/api/evidence", headers=other_headers,
        json={"case_id": case_id, "description": "Cross tenant"}).status_code == 404
    with database_factory()() as db:
        assert db.get(Evidence, evidence_id).organization_id is None


def test_upload_does_not_overwrite_and_rejects_external_paths(client, admin_headers, tmp_path):
    root, acquisition, _ = setup(client, admin_headers)
    case_id = acquisition["case_id"]
    url = f"/api/evidence/case/{case_id}/upload?description=Preserved"
    first = client.post(url, headers=admin_headers, files={"file": ("same.txt", b"first")})
    second = client.post(url, headers=admin_headers, files={"file": ("same.txt", b"second")})
    assert first.status_code == second.status_code == 200
    for response, raw in ((first, b"first"), (second, b"second")):
        assert client.get(f"/api/evidence/{response.json()['id']}/download", headers=admin_headers).content == raw
    outside = tmp_path / "private.txt"
    outside.write_text("not evidence", encoding="utf-8")
    row = client.post("/api/evidence", headers=admin_headers, json={"case_id": case_id,
        "description": "Untrusted location", "file_location": str(outside)}).json()
    assert client.get(f"/api/evidence/{row['id']}/download", headers=admin_headers).status_code == 403


def test_additive_migration_preserves_external_history_and_backup(client, admin_headers, tmp_path):
    import importlib
    from alembic.migration import MigrationContext
    from alembic.operations import Operations
    from sqlalchemy import create_engine
    from operia.forensic_jobs.models import EvidenceIntegration
    from test_mobile_forensics import historical, RAW
    from scripts.sqlite_backup import copy_database, verify
    root, device, exam, export_id, original_snapshot = historical(client, admin_headers)
    with database_factory()() as db:
        source = Path(db.bind.url.database)
    backup = tmp_path / "historical.db"
    restored = tmp_path / "restored.db"
    copy_database(source, backup)
    verify(backup)
    copy_database(backup, restored)
    engine = create_engine(f"sqlite:///{restored}")
    migration = importlib.import_module("migrations.versions.20261016_0004_evidence_integration")
    with engine.begin() as conn:
        EvidenceIntegration.__table__.drop(conn, checkfirst=True)
        with Operations.context(MigrationContext.configure(conn)):
            migration.upgrade()
            migration.upgrade()
            migration.downgrade()
        assert conn.exec_driver_sql("SELECT original_bytes FROM mobile_exams WHERE id=?", (exam,)).scalar_one() == RAW
        assert conn.exec_driver_sql("SELECT content FROM mobile_exports WHERE id=?", (export_id,)).scalar_one() == original_snapshot
    engine.dispose()
    assert client.delete(root.replace("/mobile-forensics", "/legal-report"), headers=admin_headers).status_code == 409
    assert client.get(root + f"/exams/{exam}/original", headers=admin_headers).content == RAW


def test_reader_cannot_integrate_and_foreign_review_is_rejected(client, admin_headers):
    root, acquisition, raw = setup(client, admin_headers)
    job = enqueue(client, admin_headers, root, acquisition)
    assert worker.run_once(database_factory(), timeout=15)
    path = root + f"/jobs/{job['id']}"
    assert client.post(path + "/integrations?review_id=9999", headers=admin_headers).status_code == 404
    app.dependency_overrides[get_optional_user] = lambda: CurrentUser(1, acquisition["organization_id"], "Reader", None, "lector")
    assert client.post(path + "/integrations?review_id=9999").status_code == 403
    app.dependency_overrides.pop(get_optional_user)


def test_export_paths_are_fresh_and_reject_cross_scope_before_writing(client, admin_headers):
    root, acquisition, _ = setup(client, admin_headers)
    body = {"filename": "preserved.json", "content": {"marker": "original"}, "case_id": acquisition["case_id"]}
    first = client.post("/api/exports/json", headers=admin_headers, json=body)
    assert first.status_code == 200
    first_id = first.headers["x-operia-export-manifest-id"]
    first_manifest = client.get(f"/api/exports/manifests/{first_id}", headers=admin_headers).json()
    first_path = Path(first_manifest["file_path"])
    preserved = first_path.read_bytes()
    body["content"] = {"marker": "later"}
    assert client.post("/api/exports/json", headers=admin_headers, json=body).status_code == 200
    assert first_path.read_bytes() == preserved
    for name in ("../escape.json", "..\\escape.json", "C:escape.json"):
        body["filename"] = name
        assert client.post("/api/exports/json", headers=admin_headers, json=body).status_code == 422
    app.dependency_overrides[get_optional_user] = lambda: CurrentUser(1, 99999, "Other", None, "admin")
    body["filename"] = "valid.json"
    assert client.post("/api/exports/json", json=body).status_code == 404
    app.dependency_overrides.pop(get_optional_user)
