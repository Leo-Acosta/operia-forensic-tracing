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


def test_legal_knowledge_attack_profile_for_phishing(client):
    seed = client.post("/api/legal-knowledge/articles/seed")
    assert seed.status_code == 200

    attack_types = client.get("/api/legal-knowledge/attack-types")
    assert attack_types.status_code == 200
    assert any(item["value"] == "phishing" for item in attack_types.json())

    profile = client.get("/api/legal-knowledge/attack-types/phishing")
    assert profile.status_code == 200
    assert profile.json()["label"] == "Phishing / fraude digital"
    assert "engaño" in profile.json()["legal_theory"] or "engano" in profile.json()["legal_theory"]
    assert len(profile.json()["required_evidence"]) >= 3

    recommendation = client.post(
        "/api/legal-knowledge/articles/recommend",
        json={"incident_text": "phishing por anuncio falso con pago y captura de datos"},
    )
    assert recommendation.status_code == 200
    body = recommendation.json()
    assert body["profile"]["key"] == "phishing"
    principal = body["recommendations"][0]
    assert principal["reference"] == "CP art. 172"
    assert principal["legal_role"] == "principal"
    assert principal["confidence"] == "alto"
    assert principal["precedents"] == []
    assert principal["doctrine"] == []

    context = client.get(f"/api/legal-knowledge/articles/{principal['article_id']}/context?crime_type=phishing")
    assert context.status_code == 200
    assert context.json()["context"]["precedents"] == []
    assert context.json()["context"]["doctrine"] == []


def test_analyst_can_approve_and_reject_legal_mapping(client, admin_headers):
    seed = client.post("/api/legal-knowledge/articles/seed")
    assert seed.status_code == 200
    case = client.post(
        "/api/cases",
        json={
            "case_code": "LEGAL-MAP-001",
            "title": "Mapeo legal",
            "description": "phishing por anuncio falso",
            "incident_type": "phishing",
        },
        headers=admin_headers,
    )
    assert case.status_code == 200
    case_id = case.json()["id"]

    recommendation = client.post(
        "/api/legal-knowledge/articles/recommend",
        json={"incident_text": "phishing por anuncio falso con pago"},
    )
    principal = recommendation.json()["recommendations"][0]
    approved = client.post(
        "/api/legal-knowledge/mappings/decision",
        json={
            "case_id": case_id,
            "article_id": principal["article_id"],
            "decision_status": "aprobado",
            "analyst_name": "Analista QA",
            "analyst_rationale": "Se verifican elementos compatibles con estafa digital.",
            "legal_role": principal["legal_role"],
            "applicability_to_case": principal["applicability_to_case"],
            "probatory_limits": principal["probatory_limits"],
            "confidence_level": principal["confidence"],
        },
        headers=admin_headers,
    )
    assert approved.status_code == 200
    assert approved.json()["decision_status"] == "aprobado"
    assert approved.json()["verification_status"] == "aprobado_por_analista"
    assert approved.json()["analyst_name"] == "Analista QA"

    connected = recommendation.json()["recommendations"][1]
    rejected = client.post(
        "/api/legal-knowledge/mappings/decision",
        json={
            "case_id": case_id,
            "article_id": connected["article_id"],
            "decision_status": "descartado",
            "analyst_name": "Analista QA",
            "analyst_rationale": "No hay evidencia suficiente de manipulacion informatica directa.",
            "legal_role": connected["legal_role"],
            "applicability_to_case": connected["applicability_to_case"],
            "probatory_limits": connected["probatory_limits"],
            "confidence_level": connected["confidence"],
        },
        headers=admin_headers,
    )
    assert rejected.status_code == 200
    assert rejected.json()["decision_status"] == "descartado"
    assert rejected.json()["verification_status"] == "descartado_por_analista"

    mappings = client.get(f"/api/legal-knowledge/case/{case_id}/mappings", headers=admin_headers)
    assert mappings.status_code == 200
    decisions = {item["decision_status"] for item in mappings.json()}
    assert {"aprobado", "descartado"}.issubset(decisions)

    logs = client.get(f"/api/audit/logs?case_id={case_id}", headers=admin_headers)
    actions = {item["action"] for item in logs.json()}
    assert {"approve_legal_mapping", "reject_legal_mapping"}.issubset(actions)


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
