from io import BytesIO

from pypdf import PdfReader


def test_case_can_be_closed_operationally_with_pending_warnings(client, admin_headers):
    case = client.post(
        "/api/cases",
        json={
            "case_code": "TEST-CLOSE-WARN-001",
            "title": "Cierre operativo con pendientes",
            "description": "incidente iniciado sin informe final",
            "incident_type": "phishing",
        },
        headers=admin_headers,
    )
    assert case.status_code == 200
    case_id = case.json()["id"]

    status = client.get(f"/api/cases/{case_id}/closure-status", headers=admin_headers)
    assert status.status_code == 200
    assert status.json()["ready_to_close"] is False
    assert status.json()["missing"]

    closed = client.post(
        f"/api/cases/{case_id}/close",
        json={"closure_note": "Cierre decidido por el analista responsable."},
        headers=admin_headers,
    )
    assert closed.status_code == 200
    payload = closed.json()
    assert payload["already_closed"] is True
    assert payload["status"] == "cerrado"
    assert payload["closure_mode"] == "cierre_operativo_con_advertencias"
    assert payload["closure_warnings"]


def test_history_delete_case_requires_auth_and_removes_reports_and_exports(client, admin_headers):
    case = client.post(
        "/api/cases",
        json={
            "case_code": "TEST-HISTORY-DELETE-001",
            "title": "Caso para eliminar desde historial",
            "description": "incidente de prueba con informe asociado",
            "incident_type": "phishing",
        },
        headers=admin_headers,
    )
    assert case.status_code == 200
    case_id = case.json()["id"]

    report = client.post(f"/api/reports/case/{case_id}/generate?author=Analista%20Historial", headers=admin_headers)
    assert report.status_code == 200
    report_id = report.json()["id"]

    pdf = client.get(f"/api/exports/reports/{report_id}/pdf", headers=admin_headers)
    assert pdf.status_code == 200
    assert client.get(f"/api/reports/case/{case_id}", headers=admin_headers).json()
    assert client.get(f"/api/exports/manifests?case_id={case_id}", headers=admin_headers).json()

    unauthenticated_delete = client.delete(f"/api/cases/{case_id}")
    assert unauthenticated_delete.status_code == 401

    deleted = client.delete(f"/api/cases/{case_id}", headers=admin_headers)
    assert deleted.status_code == 200
    assert deleted.json()["deleted_reports"] == 1
    assert client.get(f"/api/cases/{case_id}", headers=admin_headers).status_code == 404
    assert client.get(f"/api/reports/case/{case_id}", headers=admin_headers).status_code == 404
    assert client.get(f"/api/exports/manifests?case_id={case_id}", headers=admin_headers).status_code == 404


def test_case_evidence_report_flow_with_audit(client, admin_headers):
    case = client.post(
        "/api/cases",
        json={
            "case_code": "TEST-CASE-001",
            "title": "Caso de prueba",
            "description": "phishing con acceso no autorizado",
            "incident_type": "phishing",
        },
        headers=admin_headers,
    )
    assert case.status_code == 200
    case_id = case.json()["id"]
    assert case.json()["case_code"] == "TEST-CASE-001"

    evidence = client.post(
        "/api/evidence",
        json={
            "case_id": case_id,
            "evidence_type": "log",
            "description": "Log de acceso",
            "sha256_hash": "abc123",
        },
        headers=admin_headers,
    )
    assert evidence.status_code == 200
    assert evidence.json()["case_id"] == case_id
    evidence_id = evidence.json()["id"]

    evidence_metadata = client.get(f"/api/evidence/{evidence_id}/metadata", headers=admin_headers)
    assert evidence_metadata.status_code == 200
    assert evidence_metadata.json()["sha256_hash"] == "abc123"

    evidence_integrity = client.get(f"/api/evidence/{evidence_id}/integrity", headers=admin_headers)
    assert evidence_integrity.status_code == 200
    assert evidence_integrity.json()["ok"] is False

    seed = client.post("/api/legal-knowledge/articles/seed", headers=admin_headers)
    assert seed.status_code == 200
    articles = client.get("/api/legal-knowledge/articles", headers=admin_headers)
    assert articles.status_code == 200
    article_id = next(item["id"] for item in articles.json() if item["article_number"] == "172")
    mapping = client.post(
        "/api/legal-knowledge/mappings/decision",
        json={
            "case_id": case_id,
            "article_id": article_id,
            "decision_status": "aprobado",
            "analyst_name": "Analista QA",
            "analyst_rationale": "Figura base para phishing.",
            "legal_role": "ardid/perjuicio",
        },
        headers=admin_headers,
    )
    assert mapping.status_code == 200
    link = client.post(
        "/api/legal-knowledge/mappings/evidence",
        json={
            "case_id": case_id,
            "legal_mapping_id": mapping.json()["id"],
            "evidence_id": evidence_id,
            "linked_by": "Analista QA",
            "legal_element": "Ardid o engaño",
            "element_status": "controvertido",
            "probatory_strength": "medio",
            "contradiction_risk": "critico",
            "recommended_measure": "Incorporar comprobante externo y respuesta de proveedor.",
        },
        headers=admin_headers,
    )
    assert link.status_code == 200

    report = client.post(f"/api/reports/case/{case_id}/generate?author=Analista%20QA", headers=admin_headers)
    assert report.status_code == 200
    report_id = report.json()["id"]
    assert report.json()["status"] == "caso_en_proceso_de_inicio_de_investigacion"
    assert "Encuadre legal argentino" in report.json()["markdown_content"]
    assert "CP art. 172" in report.json()["markdown_content"]
    assert "Matriz legal-probatoria aplicada" in report.json()["markdown_content"]
    assert "Semáforo de suficiencia legal" in report.json()["markdown_content"]
    assert "Nivel de exportabilidad" in report.json()["markdown_content"]
    assert "Qué se pudo acreditar" in report.json()["markdown_content"]
    assert "Conclusión específica por phishing/fraude digital" in report.json()["markdown_content"]
    assert "cuenta receptora" in report.json()["markdown_content"]

    preview = client.get(f"/api/reports/{report_id}/preview", headers=admin_headers)
    assert preview.status_code == 200
    assert preview.json()["exportability"]["level"] in {"Informe preliminar", "Listo para revisión", "Apto para presentación"}
    assert preview.json()["contradictions"]["count"] >= 1
    assert preview.json()["can_export_final"] is False
    assert preview.json()["final_checklist"]["ready"] is False
    assert preview.json()["annexes"]["count"] >= 2

    checklist = client.get(f"/api/reports/{report_id}/final-checklist", headers=admin_headers)
    assert checklist.status_code == 200
    assert "Hash SHA-256 de evidencia" in {item["label"] for item in checklist.json()["items"]}

    annexes = client.post(f"/api/reports/{report_id}/annexes/refresh", headers=admin_headers)
    assert annexes.status_code == 200
    assert "Anexos reales" in annexes.json()["markdown_content"]

    final_transition = client.post(
        f"/api/reports/{report_id}/versions/transition",
        json={"status": "final", "user": "Analista QA", "note": "Intento de cierre final"},
        headers=admin_headers,
    )
    assert final_transition.status_code == 409

    preliminar_transition = client.post(
        f"/api/reports/{report_id}/versions/transition",
        json={"status": "preliminar", "user": "Analista QA", "note": "Version preliminar"},
        headers=admin_headers,
    )
    assert preliminar_transition.status_code == 200
    assert preliminar_transition.json()["status"] == "preliminar"

    updated_summary = client.put(
        f"/api/reports/{report_id}/executive-summary",
        json={"executive_summary": "Resumen ejecutivo editado por analista QA.", "author": "Analista QA"},
        headers=admin_headers,
    )
    assert updated_summary.status_code == 200
    assert "Resumen ejecutivo editado por analista QA." in updated_summary.json()["markdown_content"]

    enriched = client.post(
        f"/api/reports/{report_id}/ai-enrich",
        json={"prompt": "Mejorar hipotesis y conclusiones"},
        headers=admin_headers,
    )
    assert enriched.status_code == 200
    enriched_text = enriched.json()["markdown_content"]
    assert "Matriz legal-probatoria aplicada" in enriched_text
    assert "Recomendaciones procesales automáticas" in enriched_text
    assert "Conclusión específica por phishing/fraude digital" in enriched_text
    assert "Hipótesis y análisis del caso" in enriched_text
    assert "Conclusión técnico-jurídica" in enriched_text
    assert "CONCLUSIÓN TÉCNICO-JURÍDICA SOBRE IMPOSIBILIDAD DE ATRIBUCIÓN" in enriched_text
    for forbidden in ("Ollama", "Mistral", "fallback", "IA local", "enriquecido_con_ia"):
        assert forbidden not in enriched_text

    reports = client.get(f"/api/reports/case/{case_id}", headers=admin_headers)
    assert reports.status_code == 200
    assert any(item["id"] == report_id for item in reports.json())

    recommendations = client.post(f"/api/ai/case/{case_id}/recommendations", json={"focus": "phishing"}, headers=admin_headers)
    assert recommendations.status_code == 200
    assert recommendations.json()["external_api_used"] is False
    assert recommendations.json()["human_review_required"] is True

    pdf = client.get(f"/api/exports/reports/{report_id}/pdf", headers=admin_headers)
    assert pdf.status_code == 200
    assert pdf.headers["x-operia-sha256"]
    assert len(pdf.content) > 2500
    pdf_text = "\n".join(page.extract_text() or "" for page in PdfReader(BytesIO(pdf.content)).pages)
    for forbidden in (
        "Ollama",
        "Mistral",
        "fallback",
        "Documento asistido por IA",
        "No hay encuadre legal",
        "enriquecido_con_ia",
    ):
        assert forbidden not in pdf_text
    assert "Analista QA" in pdf_text
    assert "Del análisis efectuado no surgen elementos técnicos suficientes" in pdf_text
    assert "En Proceso de Análisis" in pdf_text
    assert "Nivel de exportabilidad" in pdf_text
    assert "Qué se pudo acreditar" in pdf_text
    assert "CP art. 172" in pdf_text
    assert "Matriz legal-probatoria aplicada" in pdf_text
    assert "semáforo de suficiencia legal" in pdf_text
    assert "Recomendaciones procesales" in pdf_text
    assert "cuenta receptora" in pdf_text
    assert "CONCLUSIÓN TÉCNICO-JURÍDICA SOBRE IMPOSIBILIDAD DE ATRIBUCIÓN" in pdf_text
    assert "La atribución técnica de un ciberataque" in pdf_text
    assert "Anexos reales incorporados" in pdf_text

    final_pdf = client.get(f"/api/exports/reports/{report_id}/pdf?final=true", headers=admin_headers)
    assert final_pdf.status_code == 409

    logs = client.get(f"/api/audit/logs?case_id={case_id}", headers=admin_headers)
    assert logs.status_code == 200
    actions = {item["action"] for item in logs.json()}
    assert {"create_case", "create_evidence", "generate_report", "enrich_report", "export_report_pdf"}.issubset(actions)


def test_operational_hardening_readiness_dashboard_and_ai_health(client, admin_headers):
    readiness = client.get("/api/settings/readiness", headers=admin_headers)
    assert readiness.status_code == 200
    assert readiness.json()["database"]["schema_version"]
    assert readiness.json()["saas_readiness"]["database_migrations"] is True

    dashboard = client.get("/api/dashboard/", headers=admin_headers)
    assert dashboard.status_code == 200
    assert "ready_final_reports" in dashboard.json()["metrics"]
    assert "cases_by_status" in dashboard.json()
    assert "report_readiness" in dashboard.json()

    ai_health = client.get("/api/ai/health?model_name=mistral", headers=admin_headers)
    assert ai_health.status_code == 200
    assert ai_health.json()["external_api_used"] is False
    assert ai_health.json()["provider"] == "ollama"


def test_advanced_case_management_participants_evidence_custody(client, admin_headers):
    case = client.post(
        "/api/cases",
        json={
            "case_code": "TEST-CASE-ADV-001",
            "title": "Caso avanzado",
            "description": "gestion avanzada del expediente",
            "incident_type": "fraude digital",
        },
        headers=admin_headers,
    )
    assert case.status_code == 200
    case_id = case.json()["id"]

    participant = client.post(
        f"/api/cases/{case_id}/participants",
        json={
            "participant_type": "damnificado",
            "person_type": "persona_fisica",
            "display_name": "Persona QA",
            "relationship_to_case": "Damnificado principal",
        },
        headers=admin_headers,
    )
    assert participant.status_code == 200
    participant_id = participant.json()["id"]

    participant_update = participant.json() | {"display_name": "Persona QA Editada"}
    updated_participant = client.put(
        f"/api/cases/participants/{participant_id}",
        json=participant_update,
        headers=admin_headers,
    )
    assert updated_participant.status_code == 200
    assert updated_participant.json()["display_name"] == "Persona QA Editada"

    evidence = client.post(
        "/api/evidence",
        json={
            "case_id": case_id,
            "evidence_type": "log",
            "description": "Log original",
            "sha256_hash": "hash-original",
        },
        headers=admin_headers,
    )
    assert evidence.status_code == 200
    evidence_id = evidence.json()["id"]

    evidence_update = evidence.json() | {"description": "Log editado", "integrity_status": "integra"}
    updated_evidence = client.put(f"/api/evidence/{evidence_id}", json=evidence_update, headers=admin_headers)
    assert updated_evidence.status_code == 200
    assert updated_evidence.json()["description"] == "Log editado"

    custody = client.post(
        "/api/evidence/custody-actions",
        json={
            "case_id": case_id,
            "evidence_id": evidence_id,
            "action_type": "revision",
            "detailed_description": "Revision inicial",
        },
        headers=admin_headers,
    )
    assert custody.status_code == 200
    custody_id = custody.json()["id"]

    custody_update = custody.json() | {"detailed_description": "Revision editada"}
    updated_custody = client.put(
        f"/api/evidence/custody-actions/{custody_id}",
        json=custody_update,
        headers=admin_headers,
    )
    assert updated_custody.status_code == 409
    rectified = client.post(f"/api/evidence/custody-actions/{custody_id}/rectifications", headers=admin_headers,
        json={"reason": "Corrección documentada", "changes": {"detailed_description": "Revision rectificada"}})
    assert rectified.status_code == 200
    assert rectified.json()["ledger_entry"]["version"] == 1

    logs = client.get(f"/api/audit/logs?case_id={case_id}", headers=admin_headers)
    assert logs.status_code == 200
    actions = {item["action"] for item in logs.json()}
    assert {
        "create_case_participant",
        "update_case_participant",
        "create_evidence",
        "create_custody_action",
        "rectify_custody_action",
    }.issubset(actions)


def test_final_sealed_export_requires_ready_checklist_and_registers_manifest(client, admin_headers):
    case = client.post(
        "/api/cases",
        json={
            "case_code": "TEST-CASE-SEAL-001",
            "title": "Caso sellado",
            "description": "phishing con anuncio falso, perjuicio patrimonial y evidencia preservada",
            "incident_type": "phishing",
        },
        headers=admin_headers,
    )
    assert case.status_code == 200
    case_id = case.json()["id"]

    evidence = client.post(
        "/api/evidence",
        json={
            "case_id": case_id,
            "evidence_type": "captura",
            "description": "Anuncio phishing preservado",
            "sha256_hash": "637485a60bba4801e00d255e51da725a7437121923e1af05bba56d960a353e73",
            "md5_hash": "d41d8cd98f00b204e9800998ecf8427e",
        },
        headers=admin_headers,
    )
    assert evidence.status_code == 200
    evidence_id = evidence.json()["id"]

    custody = client.post(
        "/api/evidence/custody-actions",
        json={
            "case_id": case_id,
            "evidence_id": evidence_id,
            "action_type": "preservacion",
            "detailed_description": "Preservacion inicial y calculo de hashes.",
            "hash_after": evidence.json()["sha256_hash"],
            "user_responsible": "Analista Sellado",
        },
        headers=admin_headers,
    )
    assert custody.status_code == 200

    seed = client.post("/api/legal-knowledge/articles/seed", headers=admin_headers)
    assert seed.status_code == 200
    articles = client.get("/api/legal-knowledge/articles", headers=admin_headers)
    article_id = next(item["id"] for item in articles.json() if item["article_number"] == "172")
    mapping = client.post(
        "/api/legal-knowledge/mappings/decision",
        json={
            "case_id": case_id,
            "article_id": article_id,
            "decision_status": "aprobado",
            "analyst_name": "Analista Sellado",
            "analyst_rationale": "El anuncio falso sostiene ardid, error, disposicion y perjuicio.",
            "legal_role": "ardid/perjuicio/nexo causal",
        },
        headers=admin_headers,
    )
    assert mapping.status_code == 200
    link = client.post(
        "/api/legal-knowledge/mappings/evidence",
        json={
            "case_id": case_id,
            "legal_mapping_id": mapping.json()["id"],
            "evidence_id": evidence_id,
            "linked_by": "Analista Sellado",
            "legal_element": "Ardid, error, disposicion patrimonial, perjuicio y nexo causal",
            "element_status": "probado",
            "probatory_strength": "alto",
            "contradiction_risk": "bajo",
            "recommended_measure": "Mantener evidencia y solicitar informes complementarios.",
        },
        headers=admin_headers,
    )
    assert link.status_code == 200

    report = client.post(f"/api/reports/case/{case_id}/generate?author=Analista%20Sellado", headers=admin_headers)
    assert report.status_code == 200
    report_id = report.json()["id"]
    annexes = client.post(f"/api/reports/{report_id}/annexes/refresh", headers=admin_headers)
    assert annexes.status_code == 200
    review = client.post(f"/api/reports/{report_id}/review", headers=admin_headers)
    assert review.status_code == 200
    assert review.json()["score"] >= 80

    checklist = client.get(f"/api/reports/{report_id}/final-checklist", headers=admin_headers)
    assert checklist.status_code == 200
    assert checklist.json()["ready"] is True

    sealed_pdf = client.post(
        f"/api/exports/reports/{report_id}/pdf/seal-final",
        json={"analyst_name": "Analista Sellado", "declaration": "Checklist pericial final verificado."},
        headers=admin_headers,
    )
    assert sealed_pdf.status_code == 200
    assert sealed_pdf.headers["x-operia-seal-id"].startswith("OPERIA-SEAL-")
    assert sealed_pdf.headers["x-operia-export-manifest-id"]
    assert sealed_pdf.headers["x-operia-sha256"]

    pdf_text = "\n".join(page.extract_text() or "" for page in PdfReader(BytesIO(sealed_pdf.content)).pages)
    assert "Sello pericial final" in pdf_text
    assert "Analista Sellado" in pdf_text
    assert "Estado documental" in pdf_text

    updated_report = client.get(f"/api/reports/{report_id}", headers=admin_headers)
    assert updated_report.status_code == 200
    assert updated_report.json()["status"] == "final"
    assert updated_report.json()["version"].startswith("final-")
