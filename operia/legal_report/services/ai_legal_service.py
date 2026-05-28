from __future__ import annotations

from dataclasses import dataclass

from operia.legal_report.models import Case, LegalMapping
from operia.legal_report.services.legal_knowledge_base import dogmatic_context, procedural_context
from operia.legal_report.services.text_service import normalize_spanish


@dataclass(frozen=True)
class LegalCandidate:
    area: str
    norm: str
    analysis: str
    finding_id: int | None = None
    hypothesis_id: int | None = None
    verification_status: str = "Fuente pendiente de verificaciÃ³n"


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
    if _has(text, "deepfake", "ia", "voz", "audio", "video manipulado", "engaÃ±o habilitado"):
        labels.append("engaÃ±o habilitado por IA/deepfake")
    if _has(text, "phishing", "correo", "link", "credencial", "suplantaciÃ³n"):
        labels.append("phishing o suplantaciÃ³n digital")
    if _has(text, "cripto", "wallet", "blockchain", "transacciÃ³n", "transferencia"):
        labels.append("transferencia cripto fraudulenta")
    if _has(text, "acceso no autorizado", "login", "ip", "log", "sesiÃ³n"):
        labels.append("acceso no autorizado")
    if _has(text, "ransomware", "cifrado", "rescate", "extorsiÃ³n"):
        labels.append("ransomware o extorsiÃ³n digital")
    if _has(text, "datos personales", "filtraciÃ³n", "dni", "base de datos", "privacidad"):
        labels.append("incidente de datos personales")
    if _has(text, "daÃ±o informÃ¡tico", "borrado", "alteraciÃ³n", "indisponibilidad"):
        labels.append("daÃ±o o afectaciÃ³n informÃ¡tica")
    if not labels:
        labels.append(normalize_spanish(case.incident_type or "incidente digital mixto"))
    return labels


def infer_competence(case: Case) -> list[str]:
    text = _case_text(case)
    competence = ["JurisdicciÃ³n argentina indicada para el caso; competencia concreta sujeta a domicilio, lugar del hecho, plataforma interviniente y reglas procesales aplicables."]
    if _has(text, "fraude", "transferencia", "cripto", "phishing", "suplantaciÃ³n", "deepfake"):
        competence.append("Posible competencia penal si se investiga una maniobra defraudatoria, acceso indebido, suplantaciÃ³n, extorsiÃ³n o perjuicio patrimonial; la competencia concreta debe evaluarse con el CÃ³digo Procesal Penal de la NaciÃ³n, el CÃ³digo Procesal Penal Federal si correspondiera y las reglas territoriales/federales aplicables.")
    if _has(text, "empresa", "cliente", "banco", "fintech", "exchange", "plataforma", "proveedor"):
        competence.append("Posible vÃ­a civil o de consumo si intervino un proveedor digital, entidad financiera, plataforma, exchange o relaciÃ³n de consumo.")
    if _has(text, "datos personales", "filtraciÃ³n", "privacidad", "dni"):
        competence.append("Posible intervenciÃ³n de autoridad o vÃ­a vinculada a protecciÃ³n de datos personales, segÃºn afectaciÃ³n y sujetos responsables.")
    return competence


def build_legal_candidates(case: Case) -> list[LegalCandidate]:
    text = _case_text(case)
    primary_finding = case.findings[0].id if case.findings else None
    primary_hypothesis = case.hypotheses[0].id if case.hypotheses else None
    candidates = [
        LegalCandidate(
            "Prueba digital y cadena de custodia",
            "CÃ³digo Procesal Penal de la NaciÃ³n; CÃ³digo Procesal Penal Federal si correspondiera; guÃ­as y protocolos argentinos sobre evidencia digital y cadena de custodia",
            "La evidencia digital debe presentarse con preservaciÃ³n, hash, registro cronolÃ³gico de acciones, responsable, herramienta utilizada y lÃ­mites de inferencia. Desde la perspectiva procesal penal, el informe debe orientar medidas Ãºtiles: preservaciÃ³n urgente de datos, oficios a proveedores, bancos, billeteras, exchanges o plataformas, secuestro o extracciÃ³n forense cuando corresponda y documentaciÃ³n de integridad. La IA no debe convertir un dato tÃ©cnico aislado en conclusiÃ³n jurÃ­dica; debe preservar la secuencia dato tÃ©cnico, evidencia, hallazgo, hipÃ³tesis y conclusiÃ³n defendible.",
            finding_id=primary_finding,
            verification_status="Fuente oficial cargada; aplicaciÃ³n sujeta a revisiÃ³n profesional",
        ),
        LegalCandidate(
            "CÃ³digo Procesal Penal de la NaciÃ³n y estrategia probatoria",
            "CÃ³digo Procesal Penal de la NaciÃ³n, Ley 23.984, texto actualizado; CÃ³digo Procesal Penal Federal, Ley 27.063, si resultara aplicable por competencia o implementaciÃ³n",
            "El caso debe traducirse en una estrategia procesal: denuncia o ampliaciÃ³n de denuncia, preservaciÃ³n de evidencia digital, solicitud de oficios a plataformas y entidades financieras, identificaciÃ³n de titulares y accesos, requerimiento de logs, IPs, dispositivos, movimientos de fondos, pericias sobre audio, metadatos y dispositivos, y resguardo de garantÃ­as. La finalidad no es declarar culpabilidad, sino producir prueba legalmente obtenida, pertinente, Ãºtil y controlable.",
            finding_id=primary_finding,
            hypothesis_id=primary_hypothesis,
            verification_status="Fuente oficial cargada; aplicaciÃ³n sujeta a revisiÃ³n profesional",
        ),
        LegalCandidate(
            "Responsabilidad civil y daÃ±os",
            "CÃ³digo Civil y Comercial de la NaciÃ³n",
            "Corresponde analizar daÃ±o cierto, nexo causal adecuado, factor de atribuciÃ³n, previsibilidad, deber de prevenciÃ³n, medidas de mitigaciÃ³n y cuantificaciÃ³n econÃ³mica documentada con fuente, fÃ³rmula y evidencia de respaldo.",
            hypothesis_id=primary_hypothesis,
        ),
    ]
    if _has(text, "fraude", "phishing", "suplantaciÃ³n", "transferencia", "cripto", "deepfake", "engaÃ±o"):
        candidates.append(LegalCandidate(
            "Derecho penal informÃ¡tico y fraude digital",
            "CÃ³digo Penal argentino; Ley 26.388 de delitos informÃ¡ticos",
            "El patrÃ³n descrito puede ser compatible con una maniobra digital orientada a inducir error, disposiciÃ³n patrimonial o afectaciÃ³n de sistemas. El encuadre debe distinguir tipicidad objetiva y subjetiva, dolo directo o eventual, bien jurÃ­dico protegido, iter criminis, consumaciÃ³n o tentativa, autorÃ­a o participaciÃ³n, nexo causal e imputaciÃ³n objetiva. No corresponde inferir responsabilidad penal objetiva por el mero resultado ni afirmar autorÃ­a personal sin identificaciÃ³n tÃ©cnica y medidas complementarias.",
            finding_id=primary_finding,
            hypothesis_id=primary_hypothesis,
            verification_status="Fuente oficial cargada; requiere subsunciÃ³n profesional",
        ))
    if _has(text, "cripto", "wallet", "blockchain", "transacciÃ³n"):
        candidates.append(LegalCandidate(
            "Blockchain, criptoactivos y trazabilidad econÃ³mica",
            "CÃ³digo Civil y Comercial; reglas probatorias; normativa aplicable segÃºn plataforma o exchange",
            "La trazabilidad blockchain puede respaldar compatibilidad econÃ³mica, recorrido de activos y cuantificaciÃ³n preliminar, pero no acredita por sÃ­ sola identidad personal del autor ni titularidad efectiva de una wallet. Debe diferenciarse entre trazabilidad del activo, atribuciÃ³n tÃ©cnica de una direcciÃ³n y atribuciÃ³n penal subjetiva.",
            finding_id=primary_finding,
        ))
    if _has(text, "datos personales", "filtraciÃ³n", "privacidad", "dni", "correo"):
        candidates.append(LegalCandidate(
            "ProtecciÃ³n de datos personales",
            "Ley 25.326 de ProtecciÃ³n de Datos Personales",
            "Debe evaluarse si hubo tratamiento, exposiciÃ³n o afectaciÃ³n de datos personales, deberes de seguridad, confidencialidad, informaciÃ³n al titular y medidas de mitigaciÃ³n.",
        ))
    if _has(text, "cliente", "consumidor", "banco", "fintech", "exchange", "plataforma", "proveedor"):
        candidates.append(LegalCandidate(
            "Defensa del consumidor y proveedores digitales",
            "Ley 24.240 de Defensa del Consumidor",
            "Si existe relaciÃ³n de consumo, corresponde revisar deber de informaciÃ³n, seguridad, trato digno, gestiÃ³n de reclamos y eventual responsabilidad de bancos, fintech, plataformas, exchanges o proveedores digitales.",
        ))
    if _has(text, "ransomware", "extorsiÃ³n", "rescate"):
        candidates.append(LegalCandidate(
            "ExtorsiÃ³n digital y afectaciÃ³n de sistemas",
            "CÃ³digo Penal argentino; Ley 26.388 de delitos informÃ¡ticos",
            "El anÃ¡lisis debe separar intimidaciÃ³n, exigencia econÃ³mica, eventual engaÃ±o, vectores de acceso, identificaciÃ³n de cuentas receptoras y preservaciÃ³n de logs, sin atribuir autorÃ­a sin evidencia suficiente. En clave procesal, corresponde sugerir medidas urgentes de preservaciÃ³n y trazabilidad para evitar pÃ©rdida de registros o dispersiÃ³n de fondos.",
            finding_id=primary_finding,
            verification_status="Fuente oficial cargada; requiere subsunciÃ³n profesional",
        ))
    if _has(text, "acceso no autorizado", "login", "ip", "log", "sesiÃ³n"):
        candidates.append(LegalCandidate(
            "Acceso no autorizado",
            "CÃ³digo Penal argentino; Ley 26.388 de delitos informÃ¡ticos",
            "Logs, IPs y eventos de sesiÃ³n pueden sostener compatibilidad tÃ©cnica con acceso no habitual o no autorizado, pero requieren correlaciÃ³n temporal, integridad, contexto y descarte de hipÃ³tesis alternativas. La inferencia penal exige evaluar tipicidad, dolo, ausencia de autorizaciÃ³n, nexo de imputaciÃ³n y estÃ¡ndar probatorio suficiente.",
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
        f"La evaluaciÃ³n se apoya en {evidence_count} evidencia(s), {finding_count} hallazgo(s), "
        f"{hypothesis_count} hipÃ³tesis y una cuantificaciÃ³n econÃ³mica preliminar de {damage_total:.2f} ARS. "
        "El anÃ¡lisis jurÃ­dico debe formularse con dogmÃ¡tica penal: principio de legalidad, tipicidad objetiva y subjetiva, "
        "dolo o culpa cuando corresponda, antijuridicidad, culpabilidad, imputaciÃ³n objetiva, nexo causal, autorÃ­a o participaciÃ³n "
        "y estÃ¡ndar probatorio. En derecho penal no basta el resultado daÃ±oso: debe evitarse toda responsabilidad penal objetiva. "
        "La dimensiÃ³n procesal debe aplicar el CÃ³digo Procesal Penal de la NaciÃ³n y, si corresponde por competencia e implementaciÃ³n, "
        "el CÃ³digo Procesal Penal Federal, para orientar denuncia, medidas de prueba, preservaciÃ³n de evidencia digital, oficios, "
        "pericias, trazabilidad financiera y control de legalidad. "
        "La conclusiÃ³n debe mantenerse en tÃ©rminos de compatibilidad tÃ©cnica, alcance y limitaciones, "
        "sin afirmar autorÃ­a personal ni responsabilidad jurÃ­dica definitiva sin revisiÃ³n humana profesional."
    )
    warnings = [
        "La IA asiste y no reemplaza revisiÃ³n de abogado matriculado ni perito informÃ¡tico.",
        "No se incorporan jurisprudencia ni doctrina no cargadas; toda fuente no verificada queda como Fuente pendiente de verificaciÃ³n.",
        "La competencia concreta depende de hechos jurisdiccionales y procesales que deben validarse manualmente.",
    ]
    if not case.evidence:
        warnings.append("No hay evidencia preservada; el encuadre debe considerarse extremadamente preliminar.")
    if any(not item.sha256_hash for item in case.evidence):
        warnings.append("Hay evidencia sin SHA-256; no conviene usarla como soporte fuerte.")
    if not case.findings:
        warnings.append("No hay hallazgos; completar matriz dato tÃ©cnico â†’ evidencia â†’ hallazgo antes de cerrar conclusiones.")

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
            "con el incidente digital clasificado, sin afirmar autorÃ­a personal ni responsabilidad definitiva hasta completar "
            "validaciÃ³n tÃ©cnica, jurÃ­dica y probatoria."
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

