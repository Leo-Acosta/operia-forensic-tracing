from io import BytesIO

from pypdf import PdfReader


def _create_case(client, admin_headers, code):
    response = client.post(
        "/api/cases",
        json={
            "case_code": code,
            "title": f"Caso {code}",
            "description": "phishing con transferencia y acceso no autorizado",
            "incident_type": "phishing",
        },
        headers=admin_headers,
    )
    assert response.status_code == 200
    return response.json()["id"]


def _score(client, case_id, admin_headers):
    response = client.post(f"/api/rubrics/case/{case_id}/evaluate", headers=admin_headers)
    assert response.status_code == 200
    return response.json()


def test_rubric_empty_case_has_low_score(client, admin_headers):
    case_id = _create_case(client, admin_headers, "RUBRIC-EMPTY-001")
    rubric = client.get("/api/rubrics/report-2026", headers=admin_headers)
    assert rubric.status_code == 200
    assert rubric.json()["title"] == "Written Legal Evidence Report 2026"

    score = _score(client, case_id, admin_headers)
    assert score["total_score"] <= 4
    assert score["status"] == "incompleto"
    assert len(score["sections"]) == 4

    latest = client.get(f"/api/rubrics/case/{case_id}/score", headers=admin_headers)
    assert latest.status_code == 200
    assert latest.json()["id"] == score["id"]


def test_rubric_improves_with_evidence_hash_and_custody(client, admin_headers):
    case_id = _create_case(client, admin_headers, "RUBRIC-EVID-001")
    baseline = _score(client, case_id, admin_headers)

    evidence = client.post(
        "/api/evidence",
        json={
            "case_id": case_id,
            "evidence_type": "log",
            "description": "Log de acceso preservado",
            "sha256_hash": "a" * 64,
            "tool_used": "sha256sum",
            "preservation_method": "copia forense",
        },
        headers=admin_headers,
    )
    assert evidence.status_code == 200
    custody = client.post(
        "/api/evidence/custody-actions",
        json={
            "case_id": case_id,
            "evidence_id": evidence.json()["id"],
            "action_type": "analisis",
            "detailed_description": "Validación de integridad y solicitud de preservación al proveedor.",
            "tool_used": "sha256sum",
            "command_or_procedure": "sha256sum log.txt",
            "hash_after": "a" * 64,
            "legal_observations": "Solicitud de preservación de logs al proveedor.",
        },
        headers=admin_headers,
    )
    assert custody.status_code == 200

    improved = _score(client, case_id, admin_headers)
    assert improved["total_score"] > baseline["total_score"]
    assert any(section["key"] == "B" and section["status"] in {"parcial", "completo"} for section in improved["sections"])


def test_rubric_improves_with_approved_legal_mapping(client, admin_headers):
    case_id = _create_case(client, admin_headers, "RUBRIC-LEGAL-001")
    evidence = client.post(
        "/api/evidence",
        json={"case_id": case_id, "evidence_type": "captura", "description": "Comprobante de transferencia", "sha256_hash": "b" * 64},
        headers=admin_headers,
    )
    assert evidence.status_code == 200
    before = _score(client, case_id, admin_headers)

    client.post("/api/legal-knowledge/articles/seed", headers=admin_headers)
    articles = client.get("/api/legal-knowledge/articles", headers=admin_headers).json()
    article_id = next(item["id"] for item in articles if item["code"] == "CP" and item["article_number"] == "172")
    mapping = client.post(
        "/api/legal-knowledge/mappings/decision",
        json={
            "case_id": case_id,
            "article_id": article_id,
            "decision_status": "aprobado",
            "analyst_name": "Analista QA",
            "analyst_rationale": "Ardid, error y perjuicio patrimonial en revisión.",
            "legal_role": "principal",
        },
        headers=admin_headers,
    )
    assert mapping.status_code == 200
    link = client.post(
        "/api/legal-knowledge/mappings/evidence",
        json={
            "case_id": case_id,
            "legal_mapping_id": mapping.json()["id"],
            "evidence_id": evidence.json()["id"],
            "legal_element": "Ardid o engaño",
            "probatory_strength": "medio",
            "element_status": "probado",
        },
        headers=admin_headers,
    )
    assert link.status_code == 200

    after = _score(client, case_id, admin_headers)
    assert after["total_score"] > before["total_score"]
    legal_section = next(section for section in after["sections"] if section["key"] == "C")
    assert legal_section["estimated_score"] > 0


def test_rubric_improves_with_reviewed_report_and_pdf_includes_evaluation(client, admin_headers):
    case_id = _create_case(client, admin_headers, "RUBRIC-PDF-001")
    evidence = client.post(
        "/api/evidence",
        json={
            "case_id": case_id,
            "evidence_type": "log",
            "description": "Log con IP de acceso y comprobante de pago",
            "sha256_hash": "c" * 64,
            "tool_used": "exiftool",
        },
        headers=admin_headers,
    )
    assert evidence.status_code == 200
    client.post(
        "/api/evidence/custody-actions",
        json={
            "case_id": case_id,
            "evidence_id": evidence.json()["id"],
            "action_type": "preservacion",
            "detailed_description": "Preservación, análisis técnico y oficio proyectado al proveedor.",
            "tool_used": "exiftool",
            "command_or_procedure": "exiftool evidencia.png",
            "legal_observations": "Oficio y solicitud de datos de abonado pendientes.",
        },
        headers=admin_headers,
    )
    report = client.post(f"/api/reports/case/{case_id}/generate?author=Analista%20Rubrica", headers=admin_headers)
    assert report.status_code == 200
    report_id = report.json()["id"]
    before_review = _score(client, case_id, admin_headers)

    review = client.post(f"/api/reports/{report_id}/review", headers=admin_headers)
    assert review.status_code == 200
    after_review = _score(client, case_id, admin_headers)
    assert after_review["total_score"] >= before_review["total_score"]
    assert next(section for section in after_review["sections"] if section["key"] == "D")["estimated_score"] >= 5

    refreshed = client.post(f"/api/reports/case/{case_id}/generate?author=Analista%20Rubrica", headers=admin_headers)
    assert "Cumplimiento de rúbrica del informe" in refreshed.json()["markdown_content"]

    pdf = client.get(f"/api/exports/reports/{report_id}/pdf", headers=admin_headers)
    assert pdf.status_code == 200
    pdf_text = "\n".join(page.extract_text() or "" for page in PdfReader(BytesIO(pdf.content)).pages)
    assert "Cumplimiento de rúbrica del informe" in pdf_text
    assert "Written Legal Evidence Report 2026" in pdf_text
