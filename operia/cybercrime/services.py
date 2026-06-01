import shutil
import subprocess
from pathlib import Path
from typing import Any
import json

from sqlalchemy.orm import Session

from operia.cases.models import Finding
from operia.cybercrime.models import BlockchainTransaction, DeepfakeAnalysis
from operia.evidence.models import ChainOfCustodyAction, Evidence
from operia.legal_knowledge.models import LegalArticle, LegalMapping, LegalMappingEvidence
from operia.legal_knowledge.service import ensure_legal_articles
from operia.shared.time import utcnow


DEEPFAKE_MEDIA_TYPES = {"imagen", "video", "audio", "documento", "captura"}
DEEPFAKE_CLASSIFICATIONS = {
    "auténtico preliminar",
    "manipulado probable",
    "indicios de edición",
    "no concluyente",
    "requiere pericia especializada",
}
DEEPFAKE_WARNING = (
    "La clasificación es preliminar. No permite afirmar de forma concluyente que un archivo sea deepfake "
    "sin pericia especializada, preservación del original y corroboración independiente."
)
DEEPFAKE_CHECKLIST = [
    ("source_origin", "Origen del archivo"),
    ("original_preserved", "Preservación de original"),
    ("hash", "Hash"),
    ("metadata", "Metadatos EXIF/media"),
    ("compression", "Compresión"),
    ("visual_inconsistencies", "Inconsistencias visuales"),
    ("audio_inconsistencies", "Inconsistencias de audio"),
    ("lip_sync", "Sincronización labial"),
    ("frame_analysis", "Análisis frame-by-frame"),
    ("known_source_comparison", "Comparación con fuente conocida"),
    ("publication_traceability", "Trazabilidad de publicación"),
    ("external_tool_used", "Herramienta externa usada"),
    ("limitations", "Limitaciones"),
]

BLOCKCHAIN_WALLET_CLASSIFICATIONS = {
    "wallet personal no verificada",
    "exchange",
    "mixer",
    "bridge",
    "contrato inteligente",
    "wallet receptora",
    "wallet intermediaria",
    "desconocido",
}
BLOCKCHAIN_WARNING = (
    "Una wallet o transacción permite orientar trazabilidad económica, pero no identifica por sí sola a una persona "
    "sin evidencia externa corroborante, información de plataforma, comunicaciones, cuentas u otros registros."
)
BLOCKCHAIN_RECOMMENDED_MEASURES = [
    "Preservar captura del explorador.",
    "Registrar fecha/hora de consulta.",
    "Guardar URL del explorador si fue usada manualmente.",
    "Identificar exchange o plataforma si aplica.",
    "Solicitar información a la plataforma por vía legal correspondiente.",
    "Correlacionar con comunicaciones, pagos, cuentas, IPs y evidencia del caso.",
    "Evitar atribución personal solo por wallet.",
]


def verify_tool(executable_path: str | None, fallback_name: str) -> tuple[str, str | None]:
    if executable_path and Path(executable_path).exists():
        return "encontrada", executable_path
    discovered = shutil.which(fallback_name)
    if discovered:
        return "encontrada", discovered
    return "no encontrada", executable_path


def run_lab_command(command: str, capture_output: bool = True, timeout_seconds: int = 60) -> dict[str, Any]:
    if capture_output:
        completed = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
        output = "\n".join(part for part in [completed.stdout, completed.stderr] if part).strip()
        return {
            "status": "completado" if completed.returncode == 0 else "completado con advertencias",
            "return_code": completed.returncode,
            "output": output[-12000:],
        }
    subprocess.Popen(command, shell=True)
    return {
        "status": "lanzamiento solicitado",
        "return_code": None,
        "output": "Herramienta abierta como proceso externo. Importar resultados manualmente al finalizar.",
    }


def normalize_media_type(value: str | None) -> str:
    normalized = (value or "video").strip().lower()
    return normalized if normalized in DEEPFAKE_MEDIA_TYPES else "video"


def normalize_classification(value: str | None) -> str:
    normalized = (value or "no concluyente").strip().lower()
    return normalized if normalized in DEEPFAKE_CLASSIFICATIONS else "no concluyente"


def normalize_checklist(payload: Any) -> list[dict[str, Any]]:
    incoming: dict[str, Any] = {}
    if isinstance(payload, str) and payload.strip():
        try:
            parsed = json.loads(payload)
            incoming = parsed if isinstance(parsed, dict) else {}
        except json.JSONDecodeError:
            incoming = {}
    elif isinstance(payload, dict):
        incoming = payload
    elif isinstance(payload, list):
        incoming = {str(item.get("key")): item for item in payload if isinstance(item, dict) and item.get("key")}

    normalized: list[dict[str, Any]] = []
    for key, label in DEEPFAKE_CHECKLIST:
        raw = incoming.get(key, {})
        if isinstance(raw, dict):
            ok = bool(raw.get("ok"))
            note = str(raw.get("note") or "").strip()
        else:
            ok = bool(raw)
            note = ""
        normalized.append({"key": key, "label": label, "ok": ok, "note": note})
    return normalized


def serialize_checklist(checklist: Any) -> str:
    return json.dumps({item["key"]: {"ok": item["ok"], "note": item["note"]} for item in normalize_checklist(checklist)}, ensure_ascii=False)


def checklist_for_response(checklist: str | None) -> list[dict[str, Any]]:
    return normalize_checklist(checklist or "")


def deepfake_payload(analysis: DeepfakeAnalysis) -> dict[str, Any]:
    evidence = analysis.evidence
    return {
        "id": analysis.id,
        "case_id": analysis.case_id,
        "evidence_id": analysis.evidence_id,
        "evidence_description": evidence.description if evidence else "",
        "finding_id": analysis.finding_id,
        "media_type": analysis.media_type,
        "source_origin": analysis.source_origin,
        "evidence_hash": analysis.evidence_hash,
        "metadata_summary": analysis.metadata_summary or "",
        "checklist": checklist_for_response(analysis.checklist),
        "tool_used": analysis.tool_used,
        "findings": analysis.findings,
        "limitations": analysis.limitations,
        "classification": analysis.classification,
        "legal_relevance": analysis.legal_relevance,
        "legal_mapping_ids": [int(item) for item in analysis.legal_mapping_ids.split(",") if item.strip().isdigit()],
        "analyst_name": analysis.analyst_name,
        "warning": analysis.warning or DEEPFAKE_WARNING,
        "created_at": analysis.created_at.isoformat() if analysis.created_at else "",
        "updated_at": analysis.updated_at.isoformat() if analysis.updated_at else "",
    }


def create_deepfake_analysis_record(db: Session, payload: dict[str, Any]) -> DeepfakeAnalysis:
    evidence: Evidence | None = None
    evidence_id = payload.get("evidence_id")
    case_id = int(payload.get("case_id") or 0)
    if evidence_id:
        evidence = db.get(Evidence, int(evidence_id))
        if not evidence:
            raise ValueError("Evidencia no encontrada")
        if evidence.case_id != case_id:
            raise ValueError("La evidencia no pertenece al caso indicado")

    analysis = DeepfakeAnalysis(
        case_id=case_id,
        evidence_id=evidence.id if evidence else None,
        media_type=normalize_media_type(payload.get("media_type")),
        source_origin=str(payload.get("source_origin") or (evidence.source if evidence else "") or (evidence.file_location if evidence else "") or "").strip(),
        evidence_hash=str(payload.get("evidence_hash") or (evidence.sha256_hash if evidence else "") or "").strip(),
        checklist=serialize_checklist(payload.get("checklist") or {}),
        metadata_summary=str(payload.get("metadata_summary") or "").strip(),
        external_results=str(payload.get("external_results") or "").strip(),
        tool_used=str(payload.get("tool_used") or (evidence.tool_used if evidence else "") or "OPERIA Deepfake Lab").strip(),
        findings=str(payload.get("findings") or "").strip(),
        limitations=str(payload.get("limitations") or "Resultado preliminar sujeto a pericia especializada y corroboración independiente.").strip(),
        legal_relevance=str(payload.get("legal_relevance") or "").strip(),
        analyst_name=str(payload.get("analyst_name") or "").strip(),
        classification=normalize_classification(payload.get("classification")),
        warning=DEEPFAKE_WARNING,
    )
    db.add(analysis)
    db.flush()
    db.add(
        ChainOfCustodyAction(
            case_id=case_id,
            evidence_id=analysis.evidence_id,
            action_type="autenticacion de medios",
            detailed_description=f"Registro de análisis {analysis.media_type} en Deepfake Lab con clasificación preliminar: {analysis.classification}.",
            tool_used=analysis.tool_used,
            result_obtained=analysis.findings or "Análisis registrado sin hallazgos concluyentes.",
            hash_after=analysis.evidence_hash,
            legal_observations=DEEPFAKE_WARNING,
            status="registrada",
        )
    )
    db.commit()
    db.refresh(analysis)
    return analysis


def create_deepfake_finding(db: Session, analysis: DeepfakeAnalysis, payload: dict[str, Any] | None = None) -> Finding:
    payload = payload or {}
    title = payload.get("title") or f"Autenticación de medios - {analysis.media_type}"
    technical_finding = payload.get("technical_finding") or analysis.findings or "Se registró análisis preliminar del medio sin hallazgo técnico concluyente."
    finding = Finding(
        case_id=analysis.case_id,
        evidence_id=analysis.evidence_id,
        title=title,
        technical_finding=technical_finding,
        explanation=(
            f"Clasificación preliminar: {analysis.classification}. "
            "El resultado orienta la investigación y no prueba por sí solo autenticidad, falsedad ni autoría."
        ),
        confidence_level=payload.get("confidence_level") or ("medio" if analysis.classification in {"indicios de edición", "manipulado probable"} else "bajo"),
        weaknesses_or_limitations=payload.get("weaknesses_or_limitations") or analysis.limitations or DEEPFAKE_WARNING,
        tools_used=payload.get("tools_used") or analysis.tool_used,
        supporting_evidence=f"Evidencia #{analysis.evidence_id or '-'}; SHA-256: {analysis.evidence_hash or 'pendiente'}",
        preliminary_legal_relevance=analysis.legal_relevance
        or "Puede relacionarse con imagen, voz, identidad, propiedad intelectual, datos personales, honor, fraude o falsedad documental según el caso y la evidencia.",
        status="validado",
    )
    db.add(finding)
    db.flush()
    analysis.finding_id = finding.id
    db.add(
        ChainOfCustodyAction(
            case_id=analysis.case_id,
            evidence_id=analysis.evidence_id,
            action_type="hallazgo",
            detailed_description=f"Hallazgo #{finding.id} creado desde Deepfake Lab.",
            tool_used="OPERIA Deepfake Lab",
            result_obtained=technical_finding,
            status="registrada",
        )
    )
    db.commit()
    db.refresh(finding)
    db.refresh(analysis)
    return finding


def _article(db: Session, code: str, number: str) -> LegalArticle | None:
    return db.query(LegalArticle).filter(LegalArticle.code == code, LegalArticle.article_number == number).first()


def apply_deepfake_legal_mapping(db: Session, analysis: DeepfakeAnalysis, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = payload or {}
    ensure_legal_articles(db)
    text = " ".join([analysis.findings, analysis.limitations, analysis.legal_relevance, analysis.media_type]).lower()
    refs: list[tuple[str, str, str, str]] = [
        ("CCCN", "51-53", "principal", "Imagen, voz, identidad y dignidad afectadas por medio sospechoso."),
    ]
    if payload.get("personal_data") or any(term in text for term in ["dato personal", "datos personales", "dni", "identidad", "voz", "imagen"]):
        refs.extend(
            [
                ("LPDP", "5", "conexa", "Revisar consentimiento/base legal si el medio contiene datos personales."),
                ("LPDP", "9", "conexa", "Revisar seguridad y resguardo si intervienen bases o datos personales."),
            ]
        )
    if payload.get("intellectual_property") or any(term in text for term in ["obra", "audiovisual", "fotografia", "música", "musica", "autor"]):
        refs.extend(
            [
                ("LPI", "1", "principal", "Posible uso de obra protegida o material audiovisual/fonográfico."),
                ("LPI", "71", "conexa", "Solo evaluar si hay defraudación a derechos de propiedad intelectual probada."),
            ]
        )
    if payload.get("fraud") or any(term in text for term in ["fraude", "estafa", "pago", "transferencia", "engaño", "engano"]):
        refs.append(("CP", "172", "conexa", "Evaluar si el medio fue usado como ardid con perjuicio patrimonial."))
    if payload.get("document_falsity") or analysis.media_type == "documento" or any(term in text for term in ["documento", "certificado", "firma", "constancia"]):
        refs.extend(
            [
                ("CP", "293", "conexa", "Evaluar falsedad documental solo si el archivo tiene aptitud jurídica o probatoria."),
                ("CP", "296", "conexa", "Evaluar uso de documento falso si hubo presentación o utilización concreta."),
            ]
        )
    if payload.get("honor_affectation") or any(term in text for term in ["honor", "reputacion", "reputación", "imputa", "delito"]):
        refs.extend(
            [
                ("CP", "109", "conexa", "Evaluar calumnias si hay imputación falsa de delito concreto."),
                ("CP", "110", "conexa", "Evaluar injurias si hay afectación al honor con contexto suficiente."),
            ]
        )

    created_or_updated: list[LegalMapping] = []
    seen: set[tuple[str, str]] = set()
    for code, number, role, applicability in refs:
        if (code, number) in seen:
            continue
        seen.add((code, number))
        article = _article(db, code, number)
        if not article:
            continue
        mapping = (
            db.query(LegalMapping)
            .filter(LegalMapping.case_id == analysis.case_id, LegalMapping.article_id == article.id)
            .one_or_none()
        )
        if not mapping:
            mapping = LegalMapping(
                case_id=analysis.case_id,
                finding_id=analysis.finding_id,
                legal_area="Autenticación de medios y análisis deepfake",
                norm_reference=f"{article.code} art. {article.article_number}{(' inc. ' + article.subsection) if article.subsection else ''}",
                source_id=article.source_id,
                article_id=article.id,
                analysis=(
                    f"Aplicación sugerida desde Deepfake Lab. {applicability} "
                    "No implica atribución de autoría ni conclusión definitiva de manipulación."
                ),
                verification_status="Fuente registrada en biblioteca legal OPERIA",
            )
            db.add(mapping)
        mapping.finding_id = analysis.finding_id or mapping.finding_id
        mapping.decision_status = "aprobado"
        mapping.analyst_name = payload.get("analyst_name") or analysis.analyst_name or "OPERIA Deepfake Lab"
        mapping.analyst_rationale = payload.get("analyst_rationale") or "Norma aplicada como marco preliminar a partir de análisis de medio sospechoso."
        mapping.legal_role = role
        mapping.applicability_to_case = applicability
        mapping.probatory_limits = article.evidentiary_requirements + " " + DEEPFAKE_WARNING
        mapping.confidence_level = "medio"
        mapping.requires_human_review = True
        mapping.decided_at = utcnow().isoformat()
        db.flush()
        if analysis.evidence_id and not db.query(LegalMappingEvidence).filter_by(legal_mapping_id=mapping.id, evidence_id=analysis.evidence_id).first():
            db.add(
                LegalMappingEvidence(
                    case_id=analysis.case_id,
                    legal_mapping_id=mapping.id,
                    evidence_id=analysis.evidence_id,
                    linked_by=mapping.analyst_name,
                    link_rationale="Vinculación automática por análisis de autenticación de medios.",
                    legal_element="Medio digital preservado",
                    probatory_strength="medio",
                    element_status="pendiente",
                    missing_evidence="Validación pericial, contexto de publicación, consentimiento y corroboración externa.",
                    contradiction_risk="medio",
                    recommended_measure="Completar pericia especializada, trazabilidad de publicación y contraste con fuente conocida.",
                )
            )
        created_or_updated.append(mapping)

    analysis.legal_mapping_ids = ",".join(str(item.id) for item in created_or_updated)
    db.commit()
    db.refresh(analysis)
    return {
        "analysis_id": analysis.id,
        "case_id": analysis.case_id,
        "applied": [
            {
                "mapping_id": item.id,
                "norm_reference": item.norm_reference,
                "legal_role": item.legal_role,
                "applicability_to_case": item.applicability_to_case,
                "probatory_limits": item.probatory_limits,
            }
            for item in created_or_updated
        ],
        "warning": DEEPFAKE_WARNING,
    }


def normalize_wallet_classification(value: str | None) -> str:
    normalized = (value or "desconocido").strip().lower()
    return normalized if normalized in BLOCKCHAIN_WALLET_CLASSIFICATIONS else "desconocido"


def blockchain_payload(transaction: BlockchainTransaction) -> dict[str, Any]:
    evidence = transaction.evidence
    measures = [item.strip() for item in (transaction.recommended_measures or "").split("\n") if item.strip()]
    if not measures:
        measures = BLOCKCHAIN_RECOMMENDED_MEASURES
    return {
        "id": transaction.id,
        "case_id": transaction.case_id,
        "evidence_id": transaction.evidence_id,
        "evidence_description": evidence.description if evidence else "",
        "finding_id": transaction.finding_id,
        "source_wallet": transaction.source_wallet or "",
        "destination_wallet": transaction.destination_wallet or "",
        "tx_hash": transaction.tx_hash,
        "blockchain": transaction.blockchain,
        "token": transaction.token,
        "amount": transaction.amount,
        "approximate_value": transaction.approximate_value,
        "tx_datetime": transaction.tx_datetime or "",
        "explorer_url": transaction.explorer_url or "",
        "route_hypothesis": transaction.route_hypothesis or "",
        "wallet_classification": transaction.wallet_classification,
        "evidence_hash": transaction.evidence_hash,
        "tool_used": transaction.tool_used,
        "limitations": transaction.limitations,
        "recommended_measures": measures,
        "legal_mapping_ids": [int(item) for item in transaction.legal_mapping_ids.split(",") if item.strip().isdigit()],
        "analyst_name": transaction.analyst_name,
        "warning": transaction.warning or BLOCKCHAIN_WARNING,
        "created_at": transaction.created_at.isoformat() if transaction.created_at else "",
        "updated_at": transaction.updated_at.isoformat() if transaction.updated_at else "",
    }


def create_blockchain_transaction_record(db: Session, payload: dict[str, Any]) -> BlockchainTransaction:
    evidence: Evidence | None = None
    case_id = int(payload.get("case_id") or 0)
    evidence_id = payload.get("evidence_id")
    if evidence_id:
        evidence = db.get(Evidence, int(evidence_id))
        if not evidence:
            raise ValueError("Evidencia no encontrada")
        if evidence.case_id != case_id:
            raise ValueError("La evidencia no pertenece al caso indicado")

    amount = float(payload.get("amount") or 0)
    approximate_value = payload.get("approximate_value")
    if approximate_value in (None, ""):
        approximate_value = amount * float(payload.get("unit_value") or 0)

    transaction = BlockchainTransaction(
        case_id=case_id,
        evidence_id=evidence.id if evidence else None,
        source_wallet=str(payload.get("source_wallet") or "").strip(),
        destination_wallet=str(payload.get("destination_wallet") or "").strip(),
        tx_hash=str(payload.get("tx_hash") or "").strip(),
        blockchain=str(payload.get("blockchain") or "Bitcoin").strip(),
        token=str(payload.get("token") or "BTC").strip(),
        amount=amount,
        approximate_value=float(approximate_value or 0),
        tx_datetime=str(payload.get("tx_datetime") or "").strip(),
        explorer_url=str(payload.get("explorer_url") or "").strip(),
        route_hypothesis=str(payload.get("route_hypothesis") or "").strip(),
        wallet_classification=normalize_wallet_classification(payload.get("wallet_classification")),
        evidence_hash=str(payload.get("evidence_hash") or (evidence.sha256_hash if evidence else "") or "").strip(),
        tool_used=str(payload.get("tool_used") or (evidence.tool_used if evidence else "") or "OPERIA Blockchain Forensics").strip(),
        limitations=str(payload.get("limitations") or BLOCKCHAIN_WARNING).strip(),
        recommended_measures="\n".join(payload.get("recommended_measures") or BLOCKCHAIN_RECOMMENDED_MEASURES),
        analyst_name=str(payload.get("analyst_name") or "").strip(),
        warning=BLOCKCHAIN_WARNING,
    )
    if not transaction.tx_hash:
        raise ValueError("Debe indicar hash de transacción")
    db.add(transaction)
    db.flush()
    db.add(
        ChainOfCustodyAction(
            case_id=case_id,
            evidence_id=transaction.evidence_id,
            action_type="analisis blockchain",
            detailed_description=f"Registro de transacción {transaction.blockchain}/{transaction.token}: {transaction.tx_hash}.",
            tool_used=transaction.tool_used,
            result_obtained=transaction.route_hypothesis or "Transacción registrada para trazabilidad blockchain.",
            hash_after=transaction.evidence_hash,
            legal_observations=BLOCKCHAIN_WARNING,
            status="registrada",
        )
    )
    db.commit()
    db.refresh(transaction)
    return transaction


def create_blockchain_finding(db: Session, transaction: BlockchainTransaction, payload: dict[str, Any] | None = None) -> Finding:
    payload = payload or {}
    finding = Finding(
        case_id=transaction.case_id,
        evidence_id=transaction.evidence_id,
        title=payload.get("title") or f"Análisis blockchain - {transaction.blockchain} {transaction.token}",
        technical_finding=payload.get("technical_finding")
        or (
            f"Transacción {transaction.tx_hash} registrada en {transaction.blockchain}. "
            f"Monto: {transaction.amount} {transaction.token}. Clasificación wallet: {transaction.wallet_classification}. "
            f"Hipótesis de ruta: {transaction.route_hypothesis or 'pendiente'}."
        ),
        explanation=(
            "La transacción aporta trazabilidad económica y debe correlacionarse con comunicaciones, cuentas, IPs, "
            "plataformas y evidencia preservada. No identifica por sí sola a una persona."
        ),
        confidence_level=payload.get("confidence_level") or "medio",
        weaknesses_or_limitations=payload.get("weaknesses_or_limitations") or transaction.limitations or BLOCKCHAIN_WARNING,
        tools_used=payload.get("tools_used") or transaction.tool_used,
        supporting_evidence=f"Evidencia #{transaction.evidence_id or '-'}; SHA-256: {transaction.evidence_hash or 'pendiente'}; URL: {transaction.explorer_url or 'pendiente'}",
        preliminary_legal_relevance=(
            "Puede relacionarse con estafa, defraudación informática, extorsión, chantaje o datos personales según hechos acreditados."
        ),
        status="validado",
    )
    db.add(finding)
    db.flush()
    transaction.finding_id = finding.id
    db.add(
        ChainOfCustodyAction(
            case_id=transaction.case_id,
            evidence_id=transaction.evidence_id,
            action_type="hallazgo blockchain",
            detailed_description=f"Hallazgo #{finding.id} creado desde Blockchain Forensics Lab.",
            tool_used="OPERIA Blockchain Forensics",
            result_obtained=finding.technical_finding,
            status="registrada",
        )
    )
    db.commit()
    db.refresh(finding)
    db.refresh(transaction)
    return finding


def apply_blockchain_legal_mapping(db: Session, transaction: BlockchainTransaction, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = payload or {}
    ensure_legal_articles(db)
    text = " ".join(
        [
            transaction.route_hypothesis or "",
            transaction.limitations or "",
            transaction.wallet_classification or "",
            transaction.blockchain or "",
            transaction.token or "",
        ]
    ).lower()
    refs: list[tuple[str, str, str, str]] = []
    if payload.get("fraud") or any(term in text for term in ["estafa", "fraude", "engaño", "engano", "phishing"]):
        refs.append(("CP", "172", "principal", "Evaluar estafa si la transacción fue producto de ardid, error y perjuicio patrimonial."))
    if payload.get("computer_manipulation") or any(term in text for term in ["manipulación", "manipulacion", "sistema", "smart contract", "contrato inteligente"]):
        refs.append(("CP", "173", "conexa", "Evaluar defraudación mediante manipulación informática si hay alteración o uso técnico del sistema."))
    if payload.get("extortion") or any(term in text for term in ["extorsión", "extorsion", "ransomware", "rescate"]):
        refs.append(("CP", "168", "principal", "Evaluar extorsión si hubo intimidación y exigencia patrimonial."))
    if payload.get("blackmail") or any(term in text for term in ["chantaje", "revelación", "revelacion"]):
        refs.append(("CP", "169", "conexa", "Evaluar chantaje si hubo amenaza de revelación o imputación para obtener ventaja."))
    if payload.get("personal_data") or any(term in text for term in ["dato personal", "datos personales", "cuenta", "kyc", "exchange"]):
        refs.extend(
            [
                ("LPDP", "5", "conexa", "Revisar consentimiento/base legal si se tratan datos personales asociados a cuentas o plataformas."),
                ("LPDP", "9", "conexa", "Revisar seguridad de datos si hubo exposición o tratamiento de información personal."),
            ]
        )

    created_or_updated: list[LegalMapping] = []
    seen: set[tuple[str, str]] = set()
    for code, number, role, applicability in refs:
        if (code, number) in seen:
            continue
        seen.add((code, number))
        article = _article(db, code, number)
        if not article:
            continue
        mapping = (
            db.query(LegalMapping)
            .filter(LegalMapping.case_id == transaction.case_id, LegalMapping.article_id == article.id)
            .one_or_none()
        )
        if not mapping:
            norm_reference = f"{article.code} art. {article.article_number}{(' inc. ' + article.subsection) if article.subsection else ''}"
            mapping = LegalMapping(
                case_id=transaction.case_id,
                finding_id=transaction.finding_id,
                legal_area="Blockchain Forensics",
                norm_reference=norm_reference,
                source_id=article.source_id,
                article_id=article.id,
                analysis=f"Aplicación sugerida desde Blockchain Forensics Lab. {applicability} {BLOCKCHAIN_WARNING}",
                verification_status="Fuente registrada en biblioteca legal OPERIA",
            )
            db.add(mapping)
        mapping.finding_id = transaction.finding_id or mapping.finding_id
        mapping.decision_status = "aprobado"
        mapping.analyst_name = payload.get("analyst_name") or transaction.analyst_name or "OPERIA Blockchain Forensics"
        mapping.analyst_rationale = payload.get("analyst_rationale") or "Norma aplicada como marco preliminar por trazabilidad blockchain registrada."
        mapping.legal_role = role
        mapping.applicability_to_case = applicability
        mapping.probatory_limits = article.evidentiary_requirements + " " + BLOCKCHAIN_WARNING
        mapping.confidence_level = "medio"
        mapping.requires_human_review = True
        mapping.decided_at = utcnow().isoformat()
        db.flush()
        if transaction.evidence_id and not db.query(LegalMappingEvidence).filter_by(legal_mapping_id=mapping.id, evidence_id=transaction.evidence_id).first():
            db.add(
                LegalMappingEvidence(
                    case_id=transaction.case_id,
                    legal_mapping_id=mapping.id,
                    evidence_id=transaction.evidence_id,
                    linked_by=mapping.analyst_name,
                    link_rationale="Vinculación automática por transacción blockchain registrada.",
                    legal_element="Trazabilidad patrimonial digital",
                    probatory_strength="medio",
                    element_status="pendiente",
                    missing_evidence="Información de plataforma, titularidad, comunicaciones, IPs, KYC u otra evidencia externa.",
                    contradiction_risk="medio",
                    recommended_measure="Solicitar información a plataforma/exchange y correlacionar con comunicaciones, pagos, cuentas e IPs.",
                )
            )
        created_or_updated.append(mapping)

    transaction.legal_mapping_ids = ",".join(str(item.id) for item in created_or_updated)
    db.commit()
    db.refresh(transaction)
    return {
        "transaction_id": transaction.id,
        "case_id": transaction.case_id,
        "applied": [
            {
                "mapping_id": item.id,
                "norm_reference": item.norm_reference,
                "legal_role": item.legal_role,
                "applicability_to_case": item.applicability_to_case,
                "probatory_limits": item.probatory_limits,
            }
            for item in created_or_updated
        ],
        "warning": BLOCKCHAIN_WARNING,
    }
