def test_iot_forensics_registers_finding_legal_mapping_and_report(client, admin_headers):
    case = client.post(
        "/api/cases",
        json={
            "case_code": "IOT-001",
            "title": "Dispositivo conectado",
            "description": "Cámara IP con logs y posible acceso no autorizado.",
            "incident_type": "iot / dispositivos conectados",
        },
        headers=admin_headers,
    )
    assert case.status_code == 200
    case_id = case.json()["id"]

    evidence = client.post(
        "/api/evidence",
        json={
            "case_id": case_id,
            "evidence_type": "captura iot",
            "description": "Fotografía del dispositivo y export de configuración",
            "source": "Relevamiento físico controlado",
            "sha256_hash": "a" * 64,
            "tool_used": "hash local",
            "preservation_method": "fotografía, export de configuración y hash",
        },
        headers=admin_headers,
    )
    assert evidence.status_code == 200
    evidence_id = evidence.json()["id"]

    device = client.post(
        "/api/cybercrime/iot",
        json={
            "case_id": case_id,
            "evidence_id": evidence_id,
            "device_type": "cámara IP",
            "manufacturer": "Acme",
            "model": "Cam-100",
            "firmware": "1.2.3",
            "internal_ip": "192.168.1.40",
            "external_ip": "203.0.113.10",
            "mac": "00:11:22:33:44:55",
            "open_ports": "80/tcp observado en captura de configuración; 554/tcp declarado por manual.",
            "known_vulnerabilities": "Credenciales por defecto reportadas; posible acceso ilegítimo y alteración de configuración.",
            "logs_available": "Logs de acceso, red e interrupción de comunicación exportados.",
            "tool_used": "OPERIA IoT Forensics",
            "limitations": "No se ejecutaron escaneos reales; requiere correlación con logs de red y autorizaciones.",
            "checklist": {
                "physical_identification": True,
                "photo_capture": True,
                "evidence_hash": True,
                "firmware": True,
                "configuration": True,
                "logs": True,
                "ports": True,
                "default_credentials": True,
                "network_connection": True,
                "timeline": True,
                "state_preservation": True,
                "alteration_risk": True,
            },
        },
        headers=admin_headers,
    )
    assert device.status_code == 200
    body = device.json()
    assert body["case_id"] == case_id
    assert body["evidence_id"] == evidence_id
    assert body["evidence_hash"] == "a" * 64
    assert any(item["label"] == "Firmware" and item["ok"] for item in body["checklist"])
    assert "No ejecutar escaneos reales" in body["warning"]

    listing = client.get(f"/api/cybercrime/iot/case/{case_id}", headers=admin_headers)
    assert listing.status_code == 200
    assert listing.json()[0]["model"] == "Cam-100"

    finding = client.post(f"/api/cybercrime/iot/{body['id']}/finding", headers=admin_headers)
    assert finding.status_code == 200
    assert "metodologia" in finding.json()["message"]

    legal = client.post(
        f"/api/cybercrime/iot/{body['id']}/apply-legal",
        json={
            "unauthorized_access": True,
            "damage": True,
            "public_systems": True,
            "communications_interruption": True,
            "personal_data": True,
        },
        headers=admin_headers,
    )
    assert legal.status_code == 200
    applied = {item["norm_reference"] for item in legal.json()["applied"]}
    assert any(ref.startswith("CP art. 153 bis") for ref in applied)
    assert any(ref.startswith("CP art. 183") for ref in applied)
    assert any(ref.startswith("CP art. 184") for ref in applied)
    assert any(ref.startswith("CP art. 197") for ref in applied)
    assert any(ref.startswith("LPDP art. 5") for ref in applied)

    report = client.post(f"/api/reports/case/{case_id}/generate?author=Analista%20IoT", headers=admin_headers)
    assert report.status_code == 200
    markdown = report.json()["markdown_content"]
    assert "Análisis forense de dispositivos IoT" in markdown
    assert "no se ejecutan escaneos reales" in markdown
    assert "no identifica por si solo a una persona" in markdown or "no identifica por sí solo a una persona" in markdown
