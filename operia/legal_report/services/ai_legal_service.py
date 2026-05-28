from __future__ import annotations

from dataclasses import dataclass

from operia.cases.models import Case
from operia.legal_knowledge.models import LegalMapping
from operia.legal_report.services.legal_knowledge_base import dogmatic_context, procedural_context
from operia.legal_report.services.text_service import normalize_spanish


@dataclass(frozen=True)
class LegalCandidate:
    area: str
    norm: str
    analysis: str
    finding_id: int | None = None
    hypothesis_id: int | None = None
    verification_status: str = "Fuente pendiente de verificación"


def _has(text: str, *terms: str) -> bool:
    lowered = normalize_spanish(text).lower()
    return any(term.lower() in lowered for term in terms)


def _case_text(case: Case) -> str:
    parts = [
        case.title,
        case.description,
        case.incident_type,
        case.general_observations,
        " ".join(item.description for item in case.technical_data),
        " ".join(item.description for item in case.evidence),
        " ".join(f"{item.title} {item.technical_finding} {item.preliminary_legal_relevance}" for item in case.findings),
        " ".join(f"{item.title} {item.description}" for item in case.hypotheses),
    ]
    return normalize_spanish(" ".join(parts))


def classify_cybercrime(case: Case) -> list[str]:
    text = _case_text(case)
    labels: list[str] = []
    if _has(text, "deepfake", "ia", "voz", "audio", "video manipulado", "engaño habilitado"):
        labels.append("engaño habilitado por IA/deepfake")
    if _has(text, "phishing", "correo", "link", "credencial", "suplantación"):
        labels.append("phishing o suplantación digital")
    if _has(text, "cripto", "wallet", "blockchain", "transacción", "transferencia"):
        labels.append("transferencia cripto fraudulenta")
    if _has(text, "acceso no autorizado", "login", "ip", "log", "sesión"):
        labels.append("acceso no autorizado")
    if _has(text, "ransomware", "cifrado", "rescate", "extorsión"):
        labels.append("ransomware o extorsión digital")
    if _has(text, "datos personales", "filtración", "dni", "base de datos", "privacidad"):
        labels.append("incidente de datos personales")
    if _has(text, "daño informático", "borrado", "alteración", "indisponibilidad"):
        labels.append("daño o afectación informática")
    if not labels:
        labels.append(normalize_spanish(case.incident_type or "incidente digital mixto"))
    return labels


def infer_competence(case: Case) -> list[str]:
    text = _case_text(case)
    competence = ["Jurisdicción argentina indicada para el caso; competencia concreta sujeta a domicilio, lugar del hecho, plataforma interviniente y reglas procesales aplicables."]
    if _has(text, "fraude", "transferencia", "cripto", "phishing", "suplantación", "deepfake"):
        competence.append("Posible competencia penal si se investiga una maniobra defraudatoria, acceso indebido, suplantación, extorsión o perjuicio patrimonial; la competencia concreta debe evaluarse con el Código Procesal Penal de la Nación, el Código Procesal Penal Federal si correspondiera y las reglas territoriales/federales aplicables.")
    if _has(text, "empresa", "cliente", "banco", "fintech", "exchange", "plataforma", "proveedor"):
        competence.append("Posible vía civil o de consumo si intervino un proveedor digital, entidad financiera, plataforma, exchange o relación de consumo.")
    if _has(text, "datos personales", "filtración", "privacidad", "dni"):
        competence.append("Posible intervención de autoridad o vía vinculada a protección de datos personales, según afectación y sujetos responsables.")
    return competence


def build_legal_candidates(case: Case) -> list[LegalCandidate]:
    text = _case_text(case)
    primary_finding = case.findings[0].id if case.findings else None
    primary_hypothesis = case.hypotheses[0].id if case.hypotheses else None
    candidates = [
        LegalCandidate(
            "Prueba digital y cadena de custodia",
            "Código Procesal Penal de la Nación; Código Procesal Penal Federal si correspondiera; guías y protocolos argentinos sobre evidencia digital y cadena de custodia",
            "La evidencia digital debe presentarse con preservación, hash, registro cronológico de acciones, responsable, herramienta utilizada y límites de inferencia. Desde la perspectiva procesal penal, el informe debe orientar medidas útiles: preservación urgente de datos, oficios a proveedores, bancos, billeteras, exchanges o plataformas, secuestro o extracción forense cuando corresponda y documentación de integridad. La IA no debe convertir un dato técnico aislado en conclusión jurídica; debe preservar la secuencia dato técnico, evidencia, hallazgo, hipótesis y conclusión defendible.",
            finding_id=primary_finding,
            verification_status="Fuente oficial cargada; aplicación sujeta a revisión profesional",
        ),
        LegalCandidate(
            "Código Procesal Penal de la Nación y estrategia probatoria",
            "Código Procesal Penal de la Nación, Ley 23.984, texto actualizado; Código Procesal Penal Federal, Ley 27.063, si resultara aplicable por competencia o implementación",
            "El caso debe traducirse en una estrategia procesal: denuncia o ampliación de denuncia, preservación de evidencia digital, solicitud de oficios a plataformas y entidades financieras, identificación de titulares y accesos, requerimiento de logs, IPs, dispositivos, movimientos de fondos, pericias sobre audio, metadatos y dispositivos, y resguardo de garantías. La finalidad no es declarar culpabilidad, sino producir prueba legalmente obtenida, pertinente, útil y controlable.",
            finding_id=primary_finding,
            hypothesis_id=primary_hypothesis,
            verification_status="Fuente oficial cargada; aplicación sujeta a revisión profesional",
        ),
        LegalCandidate(
            "Responsabilidad civil y daños",
            "Código Civil y Comercial de la Nación",
            "Corresponde analizar daño cierto, nexo causal adecuado, factor de atribución, previsibilidad, deber de prevención, medidas de mitigación y cuantificación económica documentada con fuente, fórmula y evidencia de respaldo.",
            hypothesis_id=primary_hypothesis,
        ),
    ]
    if _has(text, "fraude", "phishing", "suplantación", "transferencia", "cripto", "deepfake", "engaño"):
        candidates.append(LegalCandidate(
            "Derecho penal informático y fraude digital",
            "Código Penal argentino; Ley 26.388 de delitos informáticos",
            "El patrón descrito puede ser compatible con una maniobra digital orientada a inducir error, disposición patrimonial o afectación de sistemas. El encuadre debe distinguir tipicidad objetiva y subjetiva, dolo directo o eventual, bien jurídico protegido, iter criminis, consumación o tentativa, autoría o participación, nexo causal e imputación objetiva. No corresponde inferir responsabilidad penal objetiva por el mero resultado ni afirmar autoría personal sin identificación técnica y medidas complementarias.",
            finding_id=primary_finding,
            hypothesis_id=primary_hypothesis,
            verification_status="Fuente oficial cargada; requiere subsunción profesional",
        ))
    if _has(text, "cripto", "wallet", "blockchain", "transacción"):
        candidates.append(LegalCandidate(
            "Blockchain, criptoactivos y trazabilidad económica",
            "Código Civil y Comercial; reglas probatorias; normativa aplicable según plataforma o exchange",
            "La trazabilidad blockchain puede respaldar compatibilidad económica, recorrido de activos y cuantificación preliminar, pero no acredita por sí sola identidad personal del autor ni titularidad efectiva de una wallet. Debe diferenciarse entre trazabilidad del activo, atribución técnica de una dirección y atribución penal subjetiva.",
            finding_id=primary_finding,
        ))
    if _has(text, "datos personales", "filtración", "privacidad", "dni", "correo"):
        candidates.append(LegalCandidate(
            "Protección de datos personales",
            "Ley 25.326 de Protección de Datos Personales",
            "Debe evaluarse si hubo tratamiento, exposición o afectación de datos personales, deberes de seguridad, confidencialidad, información al titular y medidas de mitigación.",
        ))
    if _has(text, "cliente", "consumidor", "banco", "fintech", "exchange", "plataforma", "proveedor"):
        candidates.append(LegalCandidate(
            "Defensa del consumidor y proveedores digitales",
            "Ley 24.240 de Defensa del Consumidor",
            "Si existe relación de consumo, corresponde revisar deber de información, seguridad, trato digno, gestión de reclamos y eventual responsabilidad de bancos, fintech, plataformas, exchanges o proveedores digitales.",
        ))
    if _has(text, "ransomware", "extorsión", "rescate"):
        candidates.append(LegalCandidate(
            "Extorsión digital y afectación de sistemas",
            "Código Penal argentino; Ley 26.388 de delitos informáticos",
            "El análisis debe separar intimidación, exigencia económica, eventual engaño, vectores de acceso, identificación de cuentas receptoras y preservación de logs, sin atribuir autoría sin evidencia suficiente. En clave procesal, corresponde sugerir medidas urgentes de preservación y trazabilidad para evitar pérdida de registros o dispersión de fondos.",
            finding_id=primary_finding,
            verification_status="Fuente oficial cargada; requiere subsunción profesional",
        ))
    if _has(text, "acceso no autorizado", "login", "ip", "log", "sesión"):
        candidates.append(LegalCandidate(
            "Acceso no autorizado",
            "Código Penal argentino; Ley 26.388 de delitos informáticos",
            "Logs, IPs y eventos de sesión pueden sostener compatibilidad técnica con acceso no habitual o no autorizado, pero requieren correlación temporal, integridad, contexto y descarte de hipótesis alternativas. La inferencia penal exige evaluar tipicidad, dolo, ausencia de autorización, nexo de imputación y estándar probatorio suficiente.",
            finding_id=primary_finding,
        ))
    return candidates


def generate_automatic_legal_analysis(case: Case) -> dict:
    labels = classify_cybercrime(case)
    competence = infer_competence(case)
    candidates = build_legal_candidates(case)
    damage_total = sum(item.amount for item in case.damage_items)
    evidence_count = len(case.evidence)
    finding_count = len(case.findings)
    hypothesis_count = len(case.hypotheses)

    justification = (
        f"El caso se clasifica preliminarmente como {', '.join(labels)}. "
        f"La evaluación se apoya en {evidence_count} evidencia(s), {finding_count} hallazgo(s), "
        f"{hypothesis_count} hipótesis y una cuantificación económica preliminar de {damage_total:.2f} ARS. "
        "El análisis jurídico debe formularse con dogmática penal: principio de legalidad, tipicidad objetiva y subjetiva, "
        "dolo o culpa cuando corresponda, antijuridicidad, culpabilidad, imputación objetiva, nexo causal, autoría o participación "
        "y estándar probatorio. En derecho penal no basta el resultado dañoso: debe evitarse toda responsabilidad penal objetiva. "
        "La dimensión procesal debe aplicar el Código Procesal Penal de la Nación y, si corresponde por competencia e implementación, "
        "el Código Procesal Penal Federal, para orientar denuncia, medidas de prueba, preservación de evidencia digital, oficios, "
        "pericias, trazabilidad financiera y control de legalidad. "
        "La conclusión debe mantenerse en términos de compatibilidad técnica, alcance y limitaciones, "
        "sin afirmar autoría personal ni responsabilidad jurídica definitiva sin revisión humana profesional."
    )
    warnings = [
        "La IA asiste y no reemplaza revisión de abogado matriculado ni perito informático.",
        "No se incorporan jurisprudencia ni doctrina no cargadas; toda fuente no verificada queda como Fuente pendiente de verificación.",
        "La competencia concreta depende de hechos jurisdiccionales y procesales que deben validarse manualmente.",
    ]
    if not case.evidence:
        warnings.append("No hay evidencia preservada; el encuadre debe considerarse extremadamente preliminar.")
    if any(not item.sha256_hash for item in case.evidence):
        warnings.append("Hay evidencia sin SHA-256; no conviene usarla como soporte fuerte.")
    if not case.findings:
        warnings.append("No hay hallazgos; completar matriz dato técnico → evidencia → hallazgo antes de cerrar conclusiones.")

    return {
        "incident_classification": labels,
        "competence": competence,
        "justification": normalize_spanish(justification),
        "dogmatic_criteria": normalize_spanish(dogmatic_context()),
        "procedural_criteria": normalize_spanish(procedural_context()),
        "legal_candidates": [
            {
                "legal_area": item.area,
                "norm_reference": item.norm,
                "analysis": normalize_spanish(item.analysis),
                "finding_id": item.finding_id,
                "hypothesis_id": item.hypothesis_id,
                "verification_status": normalize_spanish(item.verification_status),
            }
            for item in candidates
        ],
        "warnings": [normalize_spanish(item) for item in warnings],
        "defensible_conclusion": normalize_spanish(
            "Con el alcance y limitaciones indicadas, la evidencia disponible permite sostener una compatibilidad preliminar "
            "con el incidente digital clasificado, sin afirmar autoría personal ni responsabilidad definitiva hasta completar "
            "validación técnica, jurídica y probatoria."
        ),
    }


def apply_automatic_legal_mappings(case: Case) -> tuple[list[LegalMapping], dict]:
    analysis = generate_automatic_legal_analysis(case)
    existing = {
        (normalize_spanish(item.legal_area).lower(), normalize_spanish(item.norm_reference).lower())
        for item in case.legal_mappings
    }
    created: list[LegalMapping] = []
    for candidate in analysis["legal_candidates"]:
        key = (candidate["legal_area"].lower(), candidate["norm_reference"].lower())
        if key in existing:
            continue
        created.append(
            LegalMapping(
                case=case,
                finding_id=candidate["finding_id"],
                hypothesis_id=candidate["hypothesis_id"],
                legal_area=candidate["legal_area"],
                norm_reference=candidate["norm_reference"],
                analysis=candidate["analysis"],
                verification_status=candidate["verification_status"],
            )
        )
    return created, analysis

