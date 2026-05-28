def test_legal_knowledge_search_and_recommend(client):
    seed = client.post("/api/legal-knowledge/articles/seed")
    assert seed.status_code == 200

    search = client.get("/api/legal-knowledge/articles?q=ransomware extorsion datos")
    assert search.status_code == 200
    assert len(search.json()) >= 1

    recommend = client.post(
        "/api/legal-knowledge/articles/recommend",
        json={"incident_text": "ransomware con extorsion y filtracion de datos personales"},
    )
    assert recommend.status_code == 200
    assert len(recommend.json()["recommendations"]) >= 1
    assert recommend.json()["disclaimer"]


def test_ai_assistant_gracefully_handles_unavailable_ollama(client):
    response = client.post("/api/ai/assist", json={"prompt": "Analiza phishing con acceso ilegitimo"})
    assert response.status_code == 200
    assert response.json()["status"] in {"completed", "ollama_unavailable"}
    assert response.json()["requires_human_review"] is True


def test_ai_security_evaluation_and_report(client):
    response = client.post(
        "/api/ai-security/evaluations",
        json={"model_name": "mistral", "overall_score": 72, "run_tests": False},
    )
    assert response.status_code == 200
    evaluation_id = response.json()["id"]
    assert response.json()["risk_level"] == "medio"

    report = client.get(f"/api/ai-security/evaluations/{evaluation_id}/report")
    assert report.status_code == 200
    assert "Bajo estas condiciones" in report.json()["markdown"]


def test_exports_create_manifest_and_hash(client, admin_headers):
    response = client.post(
        "/api/exports/pdf",
        json={"title": "Export pytest", "body": "contenido forense", "filename": "pytest-export.pdf"},
        headers=admin_headers,
    )
    assert response.status_code == 200
    assert response.headers["x-operia-sha256"]
    manifest_id = response.headers["x-operia-export-manifest-id"]

    manifest = client.get(f"/api/exports/manifests/{manifest_id}", headers=admin_headers)
    assert manifest.status_code == 200
    assert manifest.json()["sha256_hash"] == response.headers["x-operia-sha256"]

    download = client.get(f"/api/exports/manifests/{manifest_id}/download", headers=admin_headers)
    assert download.status_code == 200
    assert b"OPERIA Forensic Tracing" in download.content

