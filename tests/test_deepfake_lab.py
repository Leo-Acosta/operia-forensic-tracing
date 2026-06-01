from io import BytesIO

from pypdf import PdfReader


def test_deepfake_lab_registers_finding_legal_mapping_and_report(client, admin_headers):
    case = client.post(
        "/api/cases",
        json={
            "case_code": "DEEPFAKE-001",
            "title": "Medio sospechoso",
            "description": "Video publicado con posible afectación de imagen, honor y uso documental.",
            "incident_type": "deepfake / autenticación de medios",
        },
        headers=admin_headers,
    )
    assert case.status_code == 200
    case_id = case.json()["id"]

    evidence = client.post(
        "/api/evidence",
        json={
            "case_id": case_id,
            "evidence_type": "video",
            "description": "Video preservado de publicación denunciada",
            "source": "URL preservada en acta interna",
            "sha256_hash": "d" * 64,
            "tool_used": "exiftool",
            "preservation_method": "copia íntegra sin recomprimir",
        },
        headers=admin_headers,
    )
    assert evidence.status_code == 200
    evidence_id = evidence.json()["id"]

    analysis = client.post(
        "/api/cybercrime/deepfake",
        json={
            "case_id": case_id,
            "evidence_id": evidence_id,
            "media_type": "video",
            "source_origin": "Publicación preservada con URL y timestamp",
            "metadata_summary": "Metadatos conservados; se observan recomprasión y edición previa.",
            "tool_used": "exiftool + revisión frame-by-frame",
            "findings": "Se observan indicios de edición y posible afectación al honor; el video se usó como constancia documental.",
            "limitations": "No se cuenta aún con pericia biométrica ni fuente original independiente.",
            "classification": "indicios de edición",
            "checklist": {
                "source_origin": True,
                "original_preserved": True,
                "hash": True,
                "metadata": True,
                "compression": True,
                "frame_analysis": True,
                "publication_traceability": True,
                "limitations": True,
            },
        },
        headers=admin_headers,
    )
    assert analysis.status_code == 200
    body = analysis.json()
    assert body["case_id"] == case_id
    assert body["evidence_id"] == evidence_id
    assert body["evidence_hash"] == "d" * 64
    assert body["classification"] == "indicios de edición"
    assert "preliminar" in body["warning"]

    listing = client.get(f"/api/cybercrime/deepfake/case/{case_id}", headers=admin_headers)
    assert listing.status_code == 200
    assert listing.json()[0]["id"] == body["id"]
    assert any(item["label"] == "Hash" and item["ok"] for item in listing.json()[0]["checklist"])

    finding = client.post(f"/api/cybercrime/deepfake/{body['id']}/finding", headers=admin_headers)
    assert finding.status_code == 200
    assert finding.json()["confidence_level"] in {"bajo", "medio"}

    legal = client.post(
        f"/api/cybercrime/deepfake/{body['id']}/apply-legal",
        json={
            "honor_affectation": True,
            "document_falsity": True,
            "personal_data": True,
            "intellectual_property": True,
        },
        headers=admin_headers,
    )
    assert legal.status_code == 200
    applied = {item["norm_reference"] for item in legal.json()["applied"]}
    assert any(ref.startswith("CCCN art. 51-53") for ref in applied)
    assert any(ref.startswith("LPI art. 1") for ref in applied)
    assert any(ref.startswith("CP art. 293") for ref in applied)
    assert any(ref.startswith("CP art. 296") for ref in applied)
    assert any(ref.startswith("CP art. 109") for ref in applied)
    assert any(ref.startswith("CP art. 110") for ref in applied)
    assert any(ref.startswith("LPDP art. 5") for ref in applied)

    report = client.post(f"/api/reports/case/{case_id}/generate?author=Analista%20Deepfake", headers=admin_headers)
    assert report.status_code == 200
    markdown = report.json()["markdown_content"]
    assert "Autenticación de medios y análisis deepfake" in markdown
    assert "no permite afirmar de forma concluyente" in markdown
    assert "es un deepfake" not in markdown.lower()
    assert "archivo es deepfake" not in markdown.lower()

    pdf = client.get(f"/api/exports/reports/{report.json()['id']}/pdf", headers=admin_headers)
    assert pdf.status_code == 200
    pdf_text = "\n".join(page.extract_text() or "" for page in PdfReader(BytesIO(pdf.content)).pages)
    assert "Autenticación de medios" in pdf_text
    assert "no permite afirmar de forma concluyente" in pdf_text
