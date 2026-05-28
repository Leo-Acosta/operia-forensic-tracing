from io import BytesIO

from pypdf import PdfReader


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

    report = client.post(f"/api/reports/case/{case_id}/generate?author=Analista%20QA", headers=admin_headers)
    assert report.status_code == 200
    report_id = report.json()["id"]
    assert report.json()["status"] == "caso_en_proceso_de_inicio_de_investigacion"
    assert "Texto legal resumido" in report.json()["markdown_content"]
    assert "CP art. 172" in report.json()["markdown_content"]
    assert "Matriz legal-probatoria aplicada" in report.json()["markdown_content"]
    assert "Semáforo de suficiencia legal" in report.json()["markdown_content"]
    assert "Nivel de exportabilidad" in report.json()["markdown_content"]
    assert "Qué se pudo acreditar" in report.json()["markdown_content"]
    assert "Conclusión específica por phishing/fraude digital" in report.json()["markdown_content"]
    assert "Recomendaciones procesales automáticas" in report.json()["markdown_content"]
    assert "cuenta receptora" in report.json()["markdown_content"]

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

    logs = client.get(f"/api/audit/logs?case_id={case_id}", headers=admin_headers)
    assert logs.status_code == 200
    actions = {item["action"] for item in logs.json()}
    assert {"create_case", "create_evidence", "generate_report", "enrich_report", "export_report_pdf"}.issubset(actions)


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
    assert updated_custody.status_code == 200
    assert updated_custody.json()["detailed_description"] == "Revision editada"

    logs = client.get(f"/api/audit/logs?case_id={case_id}", headers=admin_headers)
    assert logs.status_code == 200
    actions = {item["action"] for item in logs.json()}
    assert {
        "create_case_participant",
        "update_case_participant",
        "create_evidence",
        "create_custody_action",
        "update_custody_action",
    }.issubset(actions)
