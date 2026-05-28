from __future__ import annotations

import re

from operia.legal_report.models import Case, Report
from operia.legal_report.services.text_service import normalize_spanish


REQUIRED_SECTIONS = [
    "CarÃ¡tula",
    "Datos del caso",
    "Objeto del informe",
    "Alcance del anÃ¡lisis",
    "Limitaciones",
    "MetodologÃ­a utilizada",
    "Resumen ejecutivo",
    "DescripciÃ³n del incidente",
    "Evidencia recibida",
    "Registro de cadena de custodia",
    "LÃ­nea de tiempo de eventos",
    "AnÃ¡lisis tÃ©cnico-forense",
    "Matriz dato tÃ©cnico -> evidencia -> hallazgo",
    "Hallazgos principales",
    "HipÃ³tesis investigativas",
    "EvaluaciÃ³n de hipÃ³tesis alternativas",
    "Conclusiones tÃ©cnicas",
    "Encuadre jurÃ­dico argentino",
    "Responsabilidad penal preliminar",
    "Responsabilidad civil preliminar",
    "ProtecciÃ³n de datos personales",
    "CuantificaciÃ³n econÃ³mica del daÃ±o",
    "ConclusiÃ³n jurÃ­dicamente defendible",
    "Recomendaciones",
    "Anexos",
    "Glosario tÃ©cnico",
    "Preguntas y respuestas para testimonio experto",
]

RISKY_LANGUAGE = [
    "sin dudas",
    "queda probado",
    "fue culpable",
    "el atacante fue",
    "demuestra que",
    "se prueba que",
    "autor indiscutible",
    "culpable",
    "responsable penal",
]

DEFENSIBLE_LANGUAGE = [
    "la evidencia resulta compatible con",
    "con el alcance y limitaciones indicadas",
    "no resulta posible afirmar autorÃ­a personal",
    "requiere validaciÃ³n humana",
    "sujeto a verificaciÃ³n",
]

INCIDENT_LEGAL_HINTS = {
    "phishing": ["fraude", "CÃ³digo Penal", "Ley 26.388"],
    "fraude": ["fraude", "CÃ³digo Penal", "Ley 26.388"],
    "cripto": ["blockchain", "trazabilidad", "daÃ±o"],
    "transferencia": ["fraude", "daÃ±o", "trazabilidad"],
    "datos": ["Ley 25.326", "datos personales"],
    "filtraciÃ³n": ["Ley 25.326", "datos personales"],
    "deepfake": ["engaÃ±o", "IA", "fraude"],
    "ia": ["engaÃ±o", "IA", "fraude"],
    "acceso": ["acceso no autorizado", "Ley 26.388"],
    "ransomware": ["daÃ±o informÃ¡tico", "extorsiÃ³n", "Ley 26.388"],
}


def _contains_any(text: str, terms: list[str]) -> bool:
    lowered = text.lower()
    return any(term.lower() in lowered for term in terms)


def _evidence_ref_present(content: str, evidence_id: int) -> bool:
    patterns = [f"evidencia #{evidence_id}", f"evidencia {evidence_id}", f"#{evidence_id}"]
    return _contains_any(content, patterns)


def _finding_ref_present(content: str, finding_id: int, title: str) -> bool:
    return _contains_any(content, [f"hallazgo #{finding_id}", title])


def review_report(report: Report, case: Case) -> dict:
    content = normalize_spanish(report.markdown_content or "")
    content_lower = content.lower()
    critical: list[str] = []
    warnings: list[str] = []
    suggestions: list[str] = []
    unsupported: list[str] = []

    incomplete = [section for section in REQUIRED_SECTIONS if section.lower() not in content_lower]

    evidence_without_hash = [e for e in case.evidence if not e.sha256_hash]
    evidence_without_custody = [
        e for e in case.evidence
        if not any(action.evidence_id == e.id for action in case.actions)
    ]
    findings_without_evidence = [f for f in case.findings if not f.evidence_id and not f.supporting_evidence]
    findings_without_data = [f for f in case.findings if not f.technical_data_id]
    draft_findings = [f for f in case.findings if f.status == "borrador"]
    data_without_evidence = [
        d for d in case.technical_data
        if not any(e.technical_data_id == d.id for e in case.evidence)
    ]
    evidence_without_finding = [
        e for e in case.evidence
        if not any(f.evidence_id == e.id for f in case.findings)
    ]
    hypotheses_without_support = [
        h for h in case.hypotheses
        if not h.finding_ids.strip() and not h.evidence_ids.strip()
    ]
    hypotheses_without_limits = [
        h for h in case.hypotheses
        if not h.alternative_hypotheses.strip() or not h.error_risks.strip() or not h.facts_to_prove.strip()
    ]
    legal_without_source = [
        m for m in case.legal_mappings
        if not m.norm_reference.strip() or "pendiente" in m.verification_status.lower()
    ]
    damages_without_formula = [
        d for d in case.damage_items
        if not d.formula_used.strip() or not d.value_source.strip()
    ]
    damages_without_support = [
        d for d in case.damage_items
        if not d.supporting_evidence.strip()
    ]

    if incomplete:
        critical.append(f"Faltan {len(incomplete)} secciones obligatorias del informe.")
    if evidence_without_hash:
        critical.append("Existen evidencias sin hash SHA-256; no conviene usarlas como soporte fuerte.")
    if findings_without_evidence:
        critical.append("Existen hallazgos sin evidencia vinculada ni respaldo textual.")
    if "limitaciones" not in content_lower:
        critical.append("El informe no explicita limitaciones del anÃ¡lisis.")
    if case.findings and not case.evidence:
        critical.append("Hay hallazgos cargados sin evidencia preservada en el caso.")

    if data_without_evidence:
        warnings.append(f"{len(data_without_evidence)} dato(s) tÃ©cnico(s) todavÃ­a no fueron convertidos o vinculados a evidencia.")
    if evidence_without_finding:
        warnings.append(f"{len(evidence_without_finding)} evidencia(s) no estÃ¡n usadas en ningÃºn hallazgo.")
    if evidence_without_custody:
        warnings.append(f"{len(evidence_without_custody)} evidencia(s) no tienen acciÃ³n especÃ­fica de cadena de custodia vinculada.")
    if findings_without_data:
        warnings.append(f"{len(findings_without_data)} hallazgo(s) no indican dato tÃ©cnico de origen.")
    if draft_findings:
        warnings.append(f"{len(draft_findings)} hallazgo(s) siguen en borrador.")
    if case.findings and not case.hypotheses:
        warnings.append("Existen hallazgos, pero todavÃ­a no hay hipÃ³tesis investigativas asociadas.")
    if hypotheses_without_support:
        warnings.append(f"{len(hypotheses_without_support)} hipÃ³tesis no tienen hallazgos o evidencia de soporte.")
    if hypotheses_without_limits:
        warnings.append("Hay hipÃ³tesis sin alternativas, riesgos de error o hechos faltantes.")
    if not case.actions:
        warnings.append("No hay acciones registradas en la bitÃ¡cora forense.")
    if legal_without_source:
        warnings.append("Hay encuadres jurÃ­dicos con norma incompleta o fuente pendiente de verificaciÃ³n.")
    if not case.legal_mappings:
        warnings.append("El caso no tiene encuadre legal manual cargado.")
    if damages_without_formula:
        warnings.append("Hay cÃ¡lculos econÃ³micos sin fÃ³rmula o fuente de valor.")
    if damages_without_support:
        warnings.append("Hay conceptos de daÃ±o sin evidencia de respaldo.")
    if case.damage_items and any(item.amount <= 0 for item in case.damage_items):
        warnings.append("Hay conceptos de daÃ±o con monto cero o negativo.")

    for phrase in RISKY_LANGUAGE:
        if phrase in content_lower:
            warnings.append(f"Lenguaje demasiado categÃ³rico detectado: '{phrase}'.")
    if "autorÃ­a" in content_lower and "no resulta posible afirmar autorÃ­a personal" not in content_lower:
        warnings.append("El informe menciona autorÃ­a, pero no incluye una limitaciÃ³n expresa de atribuciÃ³n personal.")

    for evidence in case.evidence:
        if not _evidence_ref_present(content_lower, evidence.id):
            unsupported.append(f"Evidencia #{evidence.id}: no aparece citada en el informe.")
    for finding in case.findings:
        if not _finding_ref_present(content_lower, finding.id, finding.title):
            unsupported.append(f"Hallazgo #{finding.id}: {finding.title} no aparece integrado al informe.")
        if finding.confidence_level == "bajo" and "limit" not in (finding.weaknesses_or_limitations or "").lower():
            warnings.append(f"Hallazgo #{finding.id} tiene confianza baja y necesita limitaciones expresas.")

    incident = (case.incident_type or "").lower()
    for key, expected_terms in INCIDENT_LEGAL_HINTS.items():
        if key in incident and not _contains_any(content, expected_terms):
            suggestions.append(f"Reforzar encuadre para '{case.incident_type}' con: {', '.join(expected_terms)}.")
            break

    if incomplete:
        suggestions.append("Completar secciones obligatorias antes de exportar una versiÃ³n final.")
    if not any(term in content_lower for term in DEFENSIBLE_LANGUAGE):
        suggestions.append("Agregar lenguaje defendible: compatibilidad tÃ©cnica, alcance, limitaciones y revisiÃ³n humana.")
    if "fuente pendiente de verificaciÃ³n" in content_lower:
        suggestions.append("Revisar fuentes normativas, doctrinarias o jurisprudenciales antes de presentar como final.")
    if damages_without_formula:
        suggestions.append("Cada monto debe indicar fÃ³rmula, fuente del valor y evidencia que respalda el cÃ¡lculo.")
    if hypotheses_without_support:
        suggestions.append("Vincular cada hipÃ³tesis con hallazgos y evidencias concretas.")
    if evidence_without_finding:
        suggestions.append("Usar la matriz probatoria para transformar evidencia preservada en hallazgos verificables.")

    score = 100
    score -= min(45, len(critical) * 16)
    score -= min(30, len(warnings) * 5)
    score -= min(20, len(incomplete) * 2)
    score -= min(15, len(unsupported) * 3)
    score = max(0, min(100, score))
    status = (
        "listo para revisiÃ³n humana" if score >= 85
        else "sÃ³lido" if score >= 70
        else "bueno" if score >= 55
        else "aceptable" if score >= 40
        else "dÃ©bil"
    )

    return {
        "score": score,
        "status": status,
        "critical_errors": [normalize_spanish(item) for item in critical],
        "warnings": [normalize_spanish(item) for item in warnings],
        "suggestions": [normalize_spanish(item) for item in suggestions],
        "incomplete_sections": [normalize_spanish(item) for item in incomplete],
        "unused_evidence": [
            normalize_spanish(f"Evidencia #{e.id}: {e.description}")
            for e in case.evidence
            if not _evidence_ref_present(content_lower, e.id)
        ],
        "unsupported_conclusions": [normalize_spanish(item) for item in unsupported],
        "drafting_recommendations": [
            "Usar fÃ³rmulas como 'la evidencia resulta compatible con' y 'con el alcance y limitaciones indicadas'.",
            "Distinguir hecho comprobado, inferencia tÃ©cnica, hipÃ³tesis, opiniÃ³n experta y conclusiÃ³n jurÃ­dica.",
            "Evitar atribuciÃ³n penal personal si solo hay compatibilidad tÃ©cnica o trazabilidad parcial.",
            "No citar jurisprudencia o doctrina que no estÃ© cargada o verificada.",
        ],
    }


def review_presentation(slides: list) -> dict:
    titles = " ".join(normalize_spanish(slide.title).lower() for slide in slides)
    text = " ".join(normalize_spanish(getattr(slide, "text", "")).lower() for slide in slides)
    score = 78
    risks: list[str] = []
    recommendations: list[str] = []

    for required in ("resumen", "lÃ­nea", "evidencia", "hallazgos", "jurÃ­dico", "daÃ±o", "conclusiÃ³n"):
        if required not in titles and required not in text:
            score -= 5
            recommendations.append(f"Incluir o reforzar pÃ¡gina de {required}.")
    if len(slides) < 5:
        score -= 10
        risks.append("La presentaciÃ³n puede ser demasiado breve para sostener la exposiciÃ³n.")
    if len(slides) > 20:
        score -= 8
        recommendations.append("Reducir extensiÃ³n para mantener claridad ejecutiva.")
    if any(phrase in text for phrase in RISKY_LANGUAGE):
        score -= 8
        risks.append("La presentaciÃ³n contiene lenguaje categÃ³rico que puede ser vulnerable en exposiciÃ³n oral.")

    return {
        "score": max(0, min(100, score)),
        "clarity": max(0, min(100, score + 5)),
        "evidentiary_strength": max(0, min(100, score)),
        "narrative_coherence": max(0, min(100, score)),
        "legal_solidity": max(0, min(100, score - 5)),
        "visual_quality": 80,
        "oral_exposure_risks": risks,
        "recommendations": recommendations or ["Mantener lenguaje probabilÃ­stico y conectar cada afirmaciÃ³n fuerte con evidencia."],
    }
def _score(base: int, penalties: list[int], bonus: int = 0) -> int:
    return max(0, min(100, base - sum(penalties) + bonus))


def review_presentation(presentation_or_slides) -> dict:
    slides = getattr(presentation_or_slides, "slides", presentation_or_slides)
    slides = sorted(list(slides), key=lambda slide: slide.slide_number)
    case = getattr(presentation_or_slides, "case", None)
    report = getattr(presentation_or_slides, "source_report", None)
    source_text = normalize_spanish(getattr(report, "markdown_content", "") or "")

    titles = " ".join(normalize_spanish(slide.title or "").lower() for slide in slides)
    body = " ".join(normalize_spanish(getattr(slide, "text", "") or "").lower() for slide in slides)
    notes = " ".join(normalize_spanish(getattr(slide, "speaker_notes", "") or "").lower() for slide in slides)
    full_text = f"{titles} {body} {notes}"
    public_text = " ".join(
        normalize_spanish(slide.text or "").lower()
        for slide in slides
        if normalize_spanish(slide.confidentiality_level).lower() == "pÃºblico"
    )

    critical: list[str] = []
    warnings: list[str] = []
    risks: list[str] = []
    recommendations: list[str] = []
    page_recommendations: list[str] = []

    required_topics = {
        "resumen ejecutivo": ("resumen", "quÃ© ocurriÃ³"),
        "teorÃ­a del caso": ("teorÃ­a", "hipÃ³tesis central"),
        "lÃ­nea de tiempo": ("lÃ­nea de tiempo", "cronolog"),
        "mapa de evidencia": ("evidencia", "hallazgo"),
        "hallazgos principales": ("hallazgos", "confianza"),
        "hipÃ³tesis": ("hipÃ³tesis", "alternativa"),
        "encuadre jurÃ­dico": ("jurÃ­dico", "norma"),
        "cuantificaciÃ³n del daÃ±o": ("daÃ±o", "monto"),
        "conclusiÃ³n defendible": ("conclusiÃ³n", "limitaciones"),
        "preguntas del jurado": ("preguntas", "jurado"),
    }
    missing_topics = [
        topic for topic, terms in required_topics.items()
        if not any(term in full_text for term in terms)
    ]
    if missing_topics:
        warnings.append("Faltan o estÃ¡n dÃ©biles estos bloques de presentaciÃ³n: " + ", ".join(missing_topics) + ".")

    if not slides:
        critical.append("La presentaciÃ³n no tiene pÃ¡ginas editables.")
    if len(slides) < 5:
        critical.append("La presentaciÃ³n es demasiado breve para una exposiciÃ³n defendible.")
    if len(slides) > 18:
        warnings.append("La presentaciÃ³n puede ser extensa para un deck ejecutivo; conviene separar versiÃ³n completa y versiÃ³n pÃºblica.")

    for slide in slides:
        text = normalize_spanish(slide.text or "").strip()
        slide_notes = normalize_spanish(slide.speaker_notes or "").strip()
        label = f"PÃ¡gina {slide.slide_number} ({normalize_spanish(slide.title)})"
        if len(text) < 40:
            page_recommendations.append(f"{label}: ampliar contenido visual; hoy parece demasiado escueta.")
        if len(text) > 950:
            warnings.append(f"{label}: contiene mucho texto para exposiciÃ³n oral; conviene dividir o resumir.")
        if not slide_notes:
            page_recommendations.append(f"{label}: agregar notas del expositor.")
        if any(phrase in text.lower() for phrase in RISKY_LANGUAGE):
            risks.append(f"{label}: contiene lenguaje categÃ³rico que puede ser vulnerable en contraexamen.")
        if normalize_spanish(slide.confidentiality_level).lower() == "pÃºblico":
            sensitive_terms = ["wallet", "hash", "correo", "dni", "domicilio", "contraseÃ±a", "clave", "vÃ­ctima"]
            if any(term in text.lower() for term in sensitive_terms):
                warnings.append(f"{label}: marcada como pÃºblica, pero contiene posibles datos sensibles.")

    strong_claim_terms = ["responsable", "autorÃ­a", "culpable", "demuestra", "probado", "sin dudas"]
    if any(term in body for term in strong_claim_terms) and not _contains_any(full_text, ["compatible con", "limitaciones", "preliminar", "no resulta posible afirmar"]):
        risks.append("Hay afirmaciones fuertes sin suficiente lenguaje de alcance, compatibilidad tÃ©cnica o limitaciÃ³n probatoria.")

    if "daÃ±o" in full_text and not _contains_any(full_text, ["fÃ³rmula", "fuente", "certeza", "monto"]):
        warnings.append("La cuantificaciÃ³n del daÃ±o aparece sin suficiente explicaciÃ³n de fÃ³rmula, fuente o nivel de certeza.")
    if "jurÃ­dico" in full_text and not _contains_any(full_text, ["cÃ³digo penal", "ley", "fuente pendiente", "norma"]):
        warnings.append("El encuadre jurÃ­dico necesita norma, fuente o marca de verificaciÃ³n pendiente.")
    if "evidencia" in full_text and not _contains_any(full_text, ["sha-256", "hash", "cadena de custodia", "preserv"]):
        warnings.append("La evidencia clave deberÃ­a mencionar hash, preservaciÃ³n o cadena de custodia.")
    if "hipÃ³tesis" in full_text and "alternativa" not in full_text:
        recommendations.append("Agregar hipÃ³tesis alternativas o explicar por quÃ© quedan pendientes.")
    if source_text:
        source_keywords = [word for word in re.findall(r"[a-zÃ¡Ã©Ã­Ã³ÃºÃ±]{7,}", source_text.lower())[:80]]
        matched = sum(1 for word in set(source_keywords) if word in full_text)
        if matched < 8:
            warnings.append("La presentaciÃ³n parece poco alineada con el informe fuente; revisar selecciÃ³n de fragmentos.")

    if case:
        incident = normalize_spanish(case.incident_type or "").lower()
        if "deepfake" in incident and "deepfake" not in full_text and "ia" not in full_text:
            recommendations.append("El tipo de incidente menciona deepfake/IA; la presentaciÃ³n debe explicarlo en lenguaje claro.")
        if ("cripto" in incident or "blockchain" in incident) and not _contains_any(full_text, ["cripto", "blockchain", "wallet", "transacciÃ³n"]):
            recommendations.append("El incidente tiene componente cripto; conviene sumar trazabilidad, wallet o transacciÃ³n relevante.")

    if public_text and _contains_any(public_text, ["confidencial", "reservado", "dni", "wallet", "hash"]):
        risks.append("La versiÃ³n pÃºblica puede exponer informaciÃ³n sensible; revisar confidencialidad por pÃ¡gina.")

    if not _contains_any(full_text, ["con el alcance", "limitaciones", "preliminar", "compatible con"]):
        recommendations.append("Incluir una diapositiva o cierre con lÃ­mites del anÃ¡lisis y conclusiÃ³n jurÃ­dicamente defendible.")
    if not notes.strip():
        risks.append("No hay notas del expositor; la defensa oral queda menos preparada.")

    clarity = _score(92, [8 for slide in slides if len(normalize_spanish(slide.text or "")) > 950] + [4 for _ in missing_topics[:4]])
    evidentiary_strength = _score(90, [10 if "evidencia" not in full_text else 0, 8 if "hash" not in full_text and "sha-256" not in full_text else 0, 8 if "custodia" not in full_text else 0])
    narrative_coherence = _score(88, [5 for _ in missing_topics], 5 if "lÃ­nea de tiempo" in full_text and "conclusiÃ³n" in full_text else 0)
    legal_solidity = _score(86, [10 if "jurÃ­dico" not in full_text else 0, 8 if not _contains_any(full_text, ["ley", "cÃ³digo penal", "norma", "fuente pendiente"]) else 0])
    visual_quality = _score(86, [6 for slide in slides if len(normalize_spanish(slide.text or "")) > 950] + [4 for slide in slides if len(normalize_spanish(slide.text or "")) < 40])
    score = round((clarity + evidentiary_strength + narrative_coherence + legal_solidity + visual_quality) / 5)
    score -= min(30, len(critical) * 12 + len(risks) * 5 + len(warnings) * 2)
    score = max(0, min(100, score))

    if critical:
        status = "dÃ©bil"
    elif score >= 85:
        status = "lista para revisiÃ³n humana"
    elif score >= 72:
        status = "sÃ³lida"
    elif score >= 58:
        status = "buena"
    elif score >= 42:
        status = "aceptable"
    else:
        status = "dÃ©bil"

    if not recommendations:
        recommendations.append("Mantener lenguaje probabilÃ­stico y conectar cada afirmaciÃ³n fuerte con evidencia preservada.")
    if not page_recommendations:
        page_recommendations.append("Las pÃ¡ginas tienen estructura editable suficiente; revisar estilo visual antes del PDF premium.")

    return {
        "score": score,
        "status": status,
        "clarity": clarity,
        "evidentiary_strength": evidentiary_strength,
        "narrative_coherence": narrative_coherence,
        "legal_solidity": legal_solidity,
        "visual_quality": visual_quality,
        "critical_errors": [normalize_spanish(item) for item in critical],
        "warnings": [normalize_spanish(item) for item in warnings],
        "oral_exposure_risks": [normalize_spanish(item) for item in risks],
        "recommendations": [normalize_spanish(item) for item in recommendations],
        "page_recommendations": [normalize_spanish(item) for item in page_recommendations],
    }

