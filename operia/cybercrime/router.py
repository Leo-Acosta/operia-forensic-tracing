from typing import Any
import ipaddress
import re
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from operia.core.database import get_db
from operia.cases.models import Case
from operia.cybercrime.models import (
    BlockchainTransaction,
    CTFAnalysisStep,
    CTFChallenge,
    CTFEvent,
    DeepfakeAnalysis,
    ExternalTool,
    ForensicLabSession,
    IoTDevice,
    ProofMatrixRow,
    ToolLaunchLog,
    utcnow,
)
from operia.cybercrime.services import run_lab_command, verify_tool
from operia.evidence.models import ChainOfCustodyAction, Evidence
from operia.exports.service import export_pdf
from operia.legal_report.services.report_service import build_integral_markdown, populate_report_sections, snapshot_report
from operia.reports.models import Report

router = APIRouter()


def analyze_indicator_value(indicator: str) -> dict[str, Any]:
    value = indicator.strip()
    parsed_url = urlparse(value if "://" in value else f"//{value}")
    lowered = value.lower()
    result: dict[str, Any] = {
        "indicator": value,
        "indicator_type": "unknown",
        "risk_level": "medium",
        "confidence": "medium",
        "findings": [],
        "observables": {},
        "recommended_actions": [
            "Preservar evidencia original y trabajar sobre copia.",
            "Registrar fuente, fecha de observacion y responsable.",
            "Correlacionar con logs, cabeceras, DNS, WHOIS, geolocalizacion y evidencia del caso.",
        ],
        "legal_relevance": "Puede tener relevancia probatoria si se vincula con evidencia preservada, trazabilidad temporal y contexto del caso.",
        "human_review_required": True,
    }

    if re.fullmatch(r"[A-Fa-f0-9]{32}", value) or re.fullmatch(r"[A-Fa-f0-9]{40}", value) or re.fullmatch(r"[A-Fa-f0-9]{64}", value):
        hash_type = {32: "MD5", 40: "SHA-1", 64: "SHA-256"}[len(value)]
        result["indicator_type"] = "hash"
        result["risk_level"] = "medium"
        result["confidence"] = "high"
        result["observables"] = {"hash_type": hash_type}
        result["findings"].append(f"Indicador reconocido como hash {hash_type}.")
        result["findings"].append("Un hash permite verificar integridad o correlacionar artefactos, pero no atribuye autoria por si solo.")
        result["recommended_actions"].extend(
            [
                "Comparar contra hashes de evidencia preservada y repositorios internos autorizados.",
                "Documentar ruta de archivo, origen, fecha de obtencion y herramienta de calculo.",
            ]
        )
        return result

    if re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", value):
        local_part, domain = value.rsplit("@", 1)
        result["indicator_type"] = "email"
        result["risk_level"] = "medium"
        result["confidence"] = "high"
        result["observables"] = {"local_part": local_part, "domain": domain}
        result["findings"].append(f"Indicador reconocido como correo electronico asociado al dominio {domain}.")
        if any(term in local_part.lower() for term in ["support", "soporte", "secure", "verify", "admin", "login"]):
            result["risk_level"] = "high"
            result["findings"].append("La cuenta usa terminos frecuentes en suplantacion o soporte falso.")
        result["recommended_actions"].extend(
            [
                "Preservar cabeceras completas del correo y cuerpo original.",
                "Solicitar datos de registracion o proveedor solo por via legal correspondiente.",
            ]
        )
        return result
    try:
        ip = ipaddress.ip_address(value)
        result["indicator_type"] = "ip"
        result["confidence"] = "high"
        result["observables"] = {
            "ip_version": ip.version,
            "is_private": ip.is_private,
            "is_global": ip.is_global,
            "is_loopback": ip.is_loopback,
        }
        result["findings"].append(f"Indicador reconocido como direccion IP version {ip.version}.")
        if ip.is_private:
            result["risk_level"] = "low"
            result["findings"].append("La IP pertenece a un rango privado; no identifica por si sola un origen publico.")
        elif ip.is_loopback or ip.is_link_local:
            result["risk_level"] = "low"
            result["findings"].append("La IP es loopback/link-local; requiere revisar el contexto local.")
        else:
            result["risk_level"] = "medium"
            result["findings"].append("La IP es enrutable publicamente; requiere enriquecimiento OSINT controlado.")
        return result
    except ValueError:
        pass

    hostname = parsed_url.hostname or value
    if "." in hostname:
        result["indicator_type"] = "url" if parsed_url.scheme else "domain"
        result["confidence"] = "medium" if result["indicator_type"] == "url" else "high"
        result["observables"] = {
            "scheme": parsed_url.scheme or "",
            "hostname": hostname,
            "path": parsed_url.path or "",
            "query_present": bool(parsed_url.query),
        }
        result["findings"].append(f"Host extraido: {hostname}.")
        if parsed_url.scheme and parsed_url.scheme not in {"http", "https"}:
            result["risk_level"] = "high"
            result["findings"].append(f"Esquema poco comun detectado: {parsed_url.scheme}.")
        if any(term in hostname.lower() for term in ["login", "verify", "secure", "account", "wallet"]):
            result["risk_level"] = "high"
            result["findings"].append("El host contiene terminos frecuentes en phishing o suplantacion.")
        if any(term in lowered for term in ["token=", "session=", "password=", "redirect=", "verify", "login"]):
            result["risk_level"] = "high"
            result["findings"].append("La URL contiene parametros o rutas que requieren revisar posible captacion de credenciales.")
        if len(hostname.split(".")) > 3:
            result["findings"].append("El host usa multiples subdominios; verificar posible camuflaje.")
        result["recommended_actions"].extend(
            [
                "Capturar DNS, certificado TLS, screenshots y codigo fuente de la pagina si corresponde.",
                "Evitar acceder desde entorno productivo; usar entorno controlado y registrar hora exacta.",
            ]
        )
        return result

    result["findings"].append("Indicador no clasificado automaticamente; requiere enriquecimiento manual.")
    return result


def as_dict(obj: Any) -> dict[str, Any]:
    return {column.name: getattr(obj, column.name) for column in obj.__table__.columns}


def create_row(db: Session, model: Any, payload: dict[str, Any]):
    row = model(**payload)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def list_rows(db: Session, model: Any, case_id: int | None = None):
    query = db.query(model)
    if case_id is not None and hasattr(model, "case_id"):
        query = query.filter(model.case_id == case_id)
    return [as_dict(row) for row in query.order_by(model.id.desc()).all()]


def update_row(db: Session, model: Any, item_id: int, payload: dict[str, Any], label: str):
    row = db.get(model, item_id)
    if not row:
        raise HTTPException(404, f"{label} no encontrado")
    for key, value in payload.items():
        if key not in {"id", "created_at", "updated_at"} and hasattr(row, key):
            setattr(row, key, value)
    db.commit()
    db.refresh(row)
    return row


def delete_row(db: Session, model: Any, item_id: int, label: str):
    row = db.get(model, item_id)
    if not row:
        raise HTTPException(404, f"{label} no encontrado")
    db.delete(row)
    db.commit()
    return {"deleted": True, "id": item_id}


@router.get("/")
def status() -> dict[str, object]:
    return {
        "module": "Cybercrime Intelligence Analyst",
        "status": "migrated",
        "description": "Operational cybercrime intelligence module using shared cases, evidence, reports, dashboard, config, and database.",
        "shared_dependencies": ["cases", "evidence", "reports", "exports", "common_database", "shared_config"],
    }


@router.post("/analyze-indicator")
def analyze_indicator(payload: dict[str, Any], db: Session = Depends(get_db)):
    indicator = str(payload.get("indicator") or "").strip()
    if not indicator:
        raise HTTPException(status_code=400, detail="Debe indicar una IP, dominio o URL.")
    case_id = payload.get("case_id")
    result = analyze_indicator_value(indicator)
    if case_id:
        case = db.get(Case, case_id)
        if not case:
            raise HTTPException(status_code=404, detail="Caso no encontrado")
        db.add(
            ChainOfCustodyAction(
                case_id=case.id,
                action_type="analisis cybercrime",
                detailed_description=f"Analisis de indicador {result['indicator_type']}: {indicator}",
                tool_used="OPERIA Cybercrime Indicator Analyzer",
                result_obtained="; ".join(result["findings"]),
                status="registrada",
            )
        )
        db.commit()
    return result


@router.get("/dashboard")
def dashboard(db: Session = Depends(get_db)):
    cases = db.query(Case).all()
    tools = db.query(ExternalTool).all()
    return {
        "open_cases": sum(1 for case in cases if case.status != "cerrado"),
        "closed_cases": sum(1 for case in cases if case.status == "cerrado"),
        "evidence_count": db.query(Evidence).count(),
        "tools_available": sum(1 for tool in tools if tool.installed_status == "encontrada"),
        "tools_missing": sum(1 for tool in tools if tool.installed_status == "no encontrada"),
        "lab_sessions": db.query(ForensicLabSession).count(),
        "ctf_events": db.query(CTFEvent).count(),
        "ctf_challenges": db.query(CTFChallenge).count(),
        "deepfake_analyses": db.query(DeepfakeAnalysis).count(),
        "iot_devices": db.query(IoTDevice).count(),
        "blockchain_transactions": db.query(BlockchainTransaction).count(),
        "proof_matrix_rows": db.query(ProofMatrixRow).count(),
    }


@router.get("/cases")
def list_shared_cases(db: Session = Depends(get_db)):
    return [as_dict(row) for row in db.query(Case).order_by(Case.updated_at.desc()).all()]


@router.get("/tools")
def get_tools(db: Session = Depends(get_db)):
    return list_rows(db, ExternalTool)


@router.post("/tools")
def create_tool(payload: dict[str, Any], db: Session = Depends(get_db)):
    return as_dict(create_row(db, ExternalTool, payload))


FORENSIC_TOOL_PRESETS: list[dict[str, Any]] = [
    {
        "name": "whois",
        "category": "dominios/osint",
        "default_command": "whois <dominio>",
        "result_import_formats": "TXT",
        "notes": "Consulta registral de dominios. Usar como orientacion; preservar fecha de consulta y fuente.",
        "safety_notes": "No atribuye autoria por si sola. Puede requerir oficio o fuente registral verificable.",
    },
    {
        "name": "nslookup",
        "category": "dns/red",
        "default_command": "nslookup <dominio>",
        "result_import_formats": "TXT",
        "notes": "Resolucion DNS basica para dominios, subdominios y registros.",
        "safety_notes": "Registrar fecha/hora porque DNS puede variar.",
    },
    {
        "name": "dig",
        "category": "dns/red",
        "default_command": "dig <dominio> ANY",
        "result_import_formats": "TXT",
        "notes": "Consulta DNS avanzada para registros A, MX, TXT, NS y trazabilidad tecnica.",
        "safety_notes": "Evitar consultas invasivas; documentar servidor DNS usado.",
    },
    {
        "name": "exiftool",
        "category": "metadatos",
        "default_command": "exiftool <archivo>",
        "result_import_formats": "TXT, JSON, CSV",
        "notes": "Extraccion de metadatos de imagenes, documentos, audio y video.",
        "safety_notes": "Trabajar sobre copia forense. Los metadatos pueden ser manipulados.",
    },
    {
        "name": "sha256sum / Get-FileHash",
        "category": "hash/integridad",
        "default_command": "Get-FileHash <archivo> -Algorithm SHA256",
        "result_import_formats": "TXT",
        "notes": "Calculo de hash para integridad y comparacion de evidencia.",
        "safety_notes": "Registrar herramienta, algoritmo, ruta, fecha y operador.",
    },
    {
        "name": "Autopsy",
        "category": "forense-disco",
        "default_command": "",
        "result_import_formats": "HTML, CSV, TXT, PDF",
        "notes": "Analisis forense de imagenes de disco, timeline, archivos eliminados y artefactos.",
        "safety_notes": "Analizar imagen/copia, no soporte original. Mantener cadena de custodia.",
    },
    {
        "name": "FTK Imager",
        "category": "adquisicion-forense",
        "default_command": "",
        "result_import_formats": "E01, RAW, TXT",
        "notes": "Adquisicion y verificacion de imagenes forenses.",
        "safety_notes": "Documentar hash antes/despues, soporte origen, operador y bitacora.",
    },
    {
        "name": "Volatility",
        "category": "memoria",
        "default_command": "volatility3 -f <memoria> windows.info",
        "result_import_formats": "TXT, JSON",
        "notes": "Analisis de memoria RAM: procesos, conexiones, DLLs y artefactos volatiles.",
        "safety_notes": "Requiere captura valida de memoria y perfil/contexto correcto.",
    },
    {
        "name": "Wireshark",
        "category": "red/pcap",
        "default_command": "",
        "result_import_formats": "PCAP, CSV, TXT",
        "notes": "Analisis de capturas de red, protocolos, sesiones y trafico sospechoso.",
        "safety_notes": "No capturar trafico fuera del alcance autorizado.",
    },
    {
        "name": "nmap",
        "category": "red/reconocimiento",
        "default_command": "nmap -sV <host>",
        "result_import_formats": "TXT, XML",
        "notes": "Identificacion de puertos y servicios en entorno autorizado.",
        "safety_notes": "Usar solo sobre activos propios/autorizados. Puede ser intrusivo.",
    },
    {
        "name": "CyberChef",
        "category": "analisis-datos",
        "default_command": "",
        "result_import_formats": "TXT, JSON",
        "notes": "Decodificacion, conversion, parsing de datos, hashes y artefactos.",
        "safety_notes": "Preferir instancia local/offline para datos sensibles.",
    },
    {
        "name": "Header Analyzer",
        "category": "correo/phishing",
        "default_command": "",
        "result_import_formats": "TXT, HTML, JSON",
        "notes": "Analisis de cabeceras de correo: SPF, DKIM, DMARC, Received y rutas.",
        "safety_notes": "Preservar cabecera completa original; no exponer correos sensibles a servicios externos.",
    },
    {
        "name": "YARA",
        "category": "malware/indicadores",
        "default_command": "yara <regla.yar> <archivo>",
        "result_import_formats": "TXT, JSON",
        "notes": "Busqueda de patrones e indicadores en archivos sospechosos.",
        "safety_notes": "No ejecutar muestras. Analizar en entorno controlado.",
    },
    {
        "name": "SQLite Browser",
        "category": "artefactos/base-de-datos",
        "default_command": "",
        "result_import_formats": "CSV, SQL, TXT",
        "notes": "Revision de bases SQLite de aplicaciones, navegadores y artefactos moviles.",
        "safety_notes": "Abrir copias, registrar ruta y hash del archivo analizado.",
    },
    {
        "name": "Kali Linux",
        "category": "entorno-laboratorio",
        "default_command": "",
        "result_import_formats": "TXT, JSON, PCAP, CSV, HTML, PDF",
        "notes": "Distribucion para laboratorio cybercrime, OSINT tecnico, red, validacion de indicadores y pruebas autorizadas.",
        "safety_notes": "Usar solo con alcance autorizado. Documentar herramienta concreta, comando, fecha, operador, objetivo y resultado. Kali no produce prueba por si mismo.",
    },
    {
        "name": "Tsurugi Linux",
        "category": "entorno-forense",
        "default_command": "",
        "result_import_formats": "TXT, CSV, JSON, HTML, PDF, imagenes forenses",
        "notes": "Distribucion orientada a forense digital, respuesta a incidentes, OSINT y analisis de evidencia.",
        "safety_notes": "Trabajar sobre copias forenses y registrar bitacora. Validar salida de cada herramienta usada.",
    },
    {
        "name": "CAINE",
        "category": "entorno-forense",
        "default_command": "",
        "result_import_formats": "TXT, CSV, HTML, PDF, imagenes forenses",
        "notes": "Distribucion forense para adquisicion, preservacion y analisis de evidencia digital.",
        "safety_notes": "Mantener modo forense/no escritura cuando corresponda. Registrar hashes y cadena de custodia.",
    },
    {
        "name": "REMnux",
        "category": "entorno-malware",
        "default_command": "",
        "result_import_formats": "TXT, JSON, PCAP, CSV",
        "notes": "Entorno especializado para analisis de malware, artefactos sospechosos, trafico y scripts.",
        "safety_notes": "No ejecutar muestras fuera de sandbox o entorno aislado. Bloquear red si el analisis lo requiere.",
    },
    {
        "name": "SIFT Workstation",
        "category": "entorno-forense-ir",
        "default_command": "",
        "result_import_formats": "TXT, CSV, JSON, timeline, bodyfile",
        "notes": "Suite de respuesta a incidentes y forense digital para timeline, disco, memoria y artefactos.",
        "safety_notes": "Documentar version, comandos y artefactos analizados. Preservar evidencia original.",
    },
    {
        "name": "Windows Sysinternals Suite",
        "category": "suite-windows-ir",
        "default_command": "",
        "result_import_formats": "TXT, CSV, EVTX",
        "notes": "Suite para analisis en Windows: procesos, arranque, conexiones, handles, persistencia y actividad del sistema.",
        "safety_notes": "Usar con minimo impacto. Registrar si la herramienta fue ejecutada sobre sistema vivo y sus limitaciones.",
    },
    {
        "name": "KAPE",
        "category": "triage-windows",
        "default_command": "",
        "result_import_formats": "CSV, JSON, TXT, ZIP",
        "notes": "Herramienta de coleccion y triage forense en Windows para artefactos, logs y evidencia rapida.",
        "safety_notes": "Configurar targets/modules segun alcance. Documentar ruta de salida, hash y operador.",
    },
]


@router.post("/tools/seed-forensic-set")
def seed_forensic_tool_set(db: Session = Depends(get_db)):
    created = 0
    updated = 0
    for preset in FORENSIC_TOOL_PRESETS:
        tool = db.query(ExternalTool).filter(ExternalTool.name == preset["name"]).one_or_none()
        if tool:
            for key, value in preset.items():
                setattr(tool, key, value)
            updated += 1
        else:
            db.add(ExternalTool(**preset))
            created += 1
    db.commit()
    return {
        "created": created,
        "updated": updated,
        "total": db.query(ExternalTool).count(),
        "message": "Set pericial base cargado. Verificar disponibilidad local antes de usar cada herramienta.",
    }


@router.patch("/tools/{tool_id}")
def update_tool(tool_id: int, payload: dict[str, Any], db: Session = Depends(get_db)):
    return as_dict(update_row(db, ExternalTool, tool_id, payload, "Herramienta"))


@router.delete("/tools/{tool_id}")
def delete_tool(tool_id: int, db: Session = Depends(get_db)):
    return delete_row(db, ExternalTool, tool_id, "Herramienta")


@router.post("/tools/{tool_id}/verify")
def verify_external_tool(tool_id: int, db: Session = Depends(get_db)):
    tool = db.get(ExternalTool, tool_id)
    if not tool:
        raise HTTPException(404, "Herramienta no encontrada")
    status_value, path = verify_tool(tool.executable_path, tool.name)
    tool.installed_status = status_value
    tool.executable_path = path
    db.commit()
    db.refresh(tool)
    return as_dict(tool)


@router.get("/lab/sessions")
def get_lab_sessions(case_id: int | None = None, db: Session = Depends(get_db)):
    return list_rows(db, ForensicLabSession, case_id)


@router.post("/lab/sessions")
def create_lab_session(payload: dict[str, Any], db: Session = Depends(get_db)):
    next_id = db.query(ForensicLabSession).count() + 1
    payload.setdefault("session_code", f"LAB-{next_id:04d}")
    payload.setdefault("checklist", "Trabajar sobre copia; hash antes/despues; no ejecutar muestra sospechosa; registrar limitaciones.")
    session = create_row(db, ForensicLabSession, payload)
    return as_dict(session)


@router.post("/lab/sessions/{session_id}/run")
def run_lab_session(session_id: int, payload: dict[str, Any] | None = None, db: Session = Depends(get_db)):
    payload = payload or {}
    session = db.get(ForensicLabSession, session_id)
    if not session:
        raise HTTPException(404, "Sesion de laboratorio no encontrada")
    if not payload.get("safety_ack") and not session.safety_ack:
        raise HTTPException(400, "Debe confirmar checklist de seguridad antes de ejecutar.")
    tool = db.get(ExternalTool, session.tool_id) if session.tool_id else None
    command = payload.get("command") or session.command or (tool.default_command if tool else None)
    if not command:
        raise HTTPException(400, "No hay comando configurado para esta sesion.")
    session.command = command
    session.safety_ack = True
    session.started_at = utcnow()
    result = run_lab_command(command, capture_output=bool(payload.get("capture_output", True)))
    session.finished_at = utcnow()
    session.command_status = result["status"]
    session.status = "ejecutada"
    session.result_summary = result["output"] or result["status"]
    if tool:
        db.add(ToolLaunchLog(tool_id=tool.id, case_id=session.case_id, command=command, status=result["status"], result_summary=session.result_summary))
    if session.case_id:
        db.add(
            ChainOfCustodyAction(
                case_id=session.case_id,
                evidence_id=session.evidence_id,
                action_type="analisis",
                detailed_description=f"Ejecucion de laboratorio {session.session_code}: {session.title}",
                tool_used=tool.name if tool else "Cybercrime Lab",
                command_or_procedure=command,
                result_obtained=session.result_summary,
                status="registrada",
            )
        )
    db.commit()
    db.refresh(session)
    return as_dict(session) | {"return_code": result["return_code"]}


@router.get("/ctf/events")
def get_ctf_events(db: Session = Depends(get_db)):
    return list_rows(db, CTFEvent)


@router.post("/ctf/events")
def create_ctf_event(payload: dict[str, Any], db: Session = Depends(get_db)):
    return as_dict(create_row(db, CTFEvent, payload))


@router.get("/ctf/challenges")
def get_ctf_challenges(event_id: int | None = None, db: Session = Depends(get_db)):
    query = db.query(CTFChallenge)
    if event_id is not None:
        query = query.filter(CTFChallenge.event_id == event_id)
    return [as_dict(row) for row in query.order_by(CTFChallenge.id.desc()).all()]


@router.post("/ctf/challenges")
def create_ctf_challenge(payload: dict[str, Any], db: Session = Depends(get_db)):
    return as_dict(create_row(db, CTFChallenge, payload))


@router.post("/ctf/challenges/{challenge_id}/mark-solved")
def mark_ctf_solved(challenge_id: int, payload: dict[str, Any] | None = None, db: Session = Depends(get_db)):
    payload = payload or {}
    challenge = db.get(CTFChallenge, challenge_id)
    if not challenge:
        raise HTTPException(404, "Challenge no encontrado")
    challenge.status = "resuelto"
    challenge.solved_at = utcnow()
    if payload.get("final_flag"):
        challenge.final_flag = payload["final_flag"]
    db.commit()
    db.refresh(challenge)
    return as_dict(challenge)


@router.get("/ctf/challenges/{challenge_id}/analysis-steps")
def get_ctf_steps(challenge_id: int, db: Session = Depends(get_db)):
    return [as_dict(row) for row in db.query(CTFAnalysisStep).filter(CTFAnalysisStep.challenge_id == challenge_id).order_by(CTFAnalysisStep.id.desc()).all()]


@router.post("/ctf/challenges/{challenge_id}/analysis-steps")
def create_ctf_step(challenge_id: int, payload: dict[str, Any], db: Session = Depends(get_db)):
    payload["challenge_id"] = challenge_id
    return as_dict(create_row(db, CTFAnalysisStep, payload))


forensic_models = {
    "deepfake-analyses": DeepfakeAnalysis,
    "iot-devices": IoTDevice,
    "blockchain-transactions": BlockchainTransaction,
    "proof-matrix": ProofMatrixRow,
}


@router.post("/reports/from-case/{case_id}/export/pdf")
def export_case_pdf(case_id: int, db: Session = Depends(get_db)):
    case = db.get(Case, case_id)
    if not case:
        raise HTTPException(404, "Caso no encontrado")
    markdown = build_integral_markdown(case)
    report = Report(case=case, title=f"Informe Cybercrime - {case.title}", author="OPERIA Cybercrime Intelligence", markdown_content=markdown)
    db.add(report)
    db.flush()
    report.sections = populate_report_sections(report, markdown)
    report.versions.append(snapshot_report(report, report.author, "Generacion desde Cybercrime Intelligence"))
    db.commit()
    db.refresh(report)
    return FileResponse(export_pdf(report), filename=f"cybercrime-report-{report.id}.pdf")


def list_cybercrime_collection(collection: str, case_id: int | None, db: Session):
    return list_rows(db, forensic_models[collection], case_id)


def create_cybercrime_collection_item(collection: str, payload: dict[str, Any], db: Session):
    model = forensic_models[collection]
    if collection == "blockchain-transactions" and "approximate_value" not in payload:
        payload["approximate_value"] = float(payload.get("amount", 0)) * float(payload.get("unit_value", 0))
    if collection == "proof-matrix":
        conclusion = (payload.get("defensible_conclusion") or "").lower()
        if any(term in conclusion for term in ["el acusado", "prueba absoluta", "autor", "identidad real"]):
            payload["risk_flag"] = "Revisar salto logico: la conclusion puede ser demasiado categorica."
    return as_dict(create_row(db, model, payload))


@router.get("/deepfake-analyses")
def list_deepfake_analyses(case_id: int | None = None, db: Session = Depends(get_db)):
    return list_cybercrime_collection("deepfake-analyses", case_id, db)


@router.post("/deepfake-analyses")
def create_deepfake_analysis(payload: dict[str, Any], db: Session = Depends(get_db)):
    return create_cybercrime_collection_item("deepfake-analyses", payload, db)


@router.get("/iot-devices")
def list_iot_devices(case_id: int | None = None, db: Session = Depends(get_db)):
    return list_cybercrime_collection("iot-devices", case_id, db)


@router.post("/iot-devices")
def create_iot_device(payload: dict[str, Any], db: Session = Depends(get_db)):
    return create_cybercrime_collection_item("iot-devices", payload, db)


@router.get("/blockchain-transactions")
def list_blockchain_transactions(case_id: int | None = None, db: Session = Depends(get_db)):
    return list_cybercrime_collection("blockchain-transactions", case_id, db)


@router.post("/blockchain-transactions")
def create_blockchain_transaction(payload: dict[str, Any], db: Session = Depends(get_db)):
    return create_cybercrime_collection_item("blockchain-transactions", payload, db)


@router.get("/proof-matrix")
def list_proof_matrix(case_id: int | None = None, db: Session = Depends(get_db)):
    return list_cybercrime_collection("proof-matrix", case_id, db)


@router.post("/proof-matrix")
def create_proof_matrix_row(payload: dict[str, Any], db: Session = Depends(get_db)):
    return create_cybercrime_collection_item("proof-matrix", payload, db)
