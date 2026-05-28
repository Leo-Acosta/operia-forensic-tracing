from __future__ import annotations

from operia.reports.models import Report
from operia.legal_report.services.ai_legal_service import generate_automatic_legal_analysis
from operia.legal_report.services.legal_knowledge_base import dogmatic_context, procedural_context
from operia.legal_report.services.text_service import normalize_spanish


def _pct(part: int, total: int) -> int:
    if total <= 0:
        return 0
    return round((part / total) * 100)


def _score_from_case(report: Report) -> dict[str, int]:
    case = report.case
    evidence_with_hash = sum(1 for item in case.evidence if item.sha256_hash)
    findings_with_evidence = sum(1 for item in case.findings if item.evidence_id or item.supporting_evidence)
    hypotheses_with_support = sum(1 for item in case.hypotheses if item.finding_ids or item.evidence_ids)
    damages_with_formula = sum(1 for item in case.damage_items if item.formula_used and item.value_source)
    legal_verified_or_pending = sum(1 for item in case.legal_mappings if item.norm_reference and item.verification_status)

    evidence_score = 45 + _pct(evidence_with_hash, max(1, len(case.evidence))) * 0.45 if case.evidence else 25
    findings_score = 45 + _pct(findings_with_evidence, max(1, len(case.findings))) * 0.45 if case.findings else 25
    hypothesis_score = 50 + _pct(hypotheses_with_support, max(1, len(case.hypotheses))) * 0.35 if case.hypotheses else 30
    legal_score = 45 + _pct(legal_verified_or_pending, max(1, len(case.legal_mappings))) * 0.4 if case.legal_mappings else 25
    economic_score = 45 + _pct(damages_with_formula, max(1, len(case.damage_items))) * 0.4 if case.damage_items else 30
    custody_score = 80 if case.actions and case.evidence else (55 if case.actions else 25)
    report_score = min(95, max(30, len(normalize_spanish(report.markdown_content or "")) // 120))
    overall = round((evidence_score + findings_score + hypothesis_score + legal_score + economic_score + custody_score + report_score) / 7)

    return {
        "overall_score": int(max(0, min(100, overall))),
        "evidence_score": int(max(0, min(100, evidence_score))),
        "finding_score": int(max(0, min(100, findings_score))),
        "hypothesis_score": int(max(0, min(100, hypothesis_score))),
        "legal_score": int(max(0, min(100, legal_score))),
        "economic_score": int(max(0, min(100, economic_score))),
        "custody_score": int(max(0, min(100, custody_score))),
        "report_score": int(max(0, min(100, report_score))),
    }


def evaluate_report_case(report: Report) -> dict:
    case = report.case
    legal = generate_automatic_legal_analysis(case)
    scores = _score_from_case(report)
    total_damage = sum(item.amount for item in case.damage_items)
    report_text = normalize_spanish(report.markdown_content or "")

    strengths: list[str] = []
    weaknesses: list[str] = []
    next_steps: list[str] = []

    if case.evidence:
        strengths.append(f"El caso tiene {len(case.evidence)} evidencia(s) registrada(s), lo que permite iniciar una cadena probatoria verificable.")
    else:
        weaknesses.append("No hay evidencia preservada; la evaluación queda en nivel preliminar bajo.")
    if any(item.sha256_hash for item in case.evidence):
        strengths.append("Existe al menos una evidencia con hash SHA-256, útil para sostener integridad.")
    elif case.evidence:
        weaknesses.append("Las evidencias cargadas no tienen hash SHA-256 suficiente para soporte fuerte.")

    if case.findings:
        strengths.append(f"Hay {len(case.findings)} hallazgo(s) que conectan evidencia con interpretación técnica.")
    else:
        weaknesses.append("Faltan hallazgos técnicos; no conviene avanzar a conclusiones jurídicas sin esa capa intermedia.")
    if case.hypotheses:
        strengths.append(f"Hay {len(case.hypotheses)} hipótesis investigativa(s) registradas.")
    else:
        weaknesses.append("Faltan hipótesis investigativas y alternativas para evitar una lectura única del caso.")
    if case.legal_mappings:
        strengths.append(f"Hay {len(case.legal_mappings)} encuadre(s) legal(es) cargado(s) o generado(s).")
    else:
        weaknesses.append("Falta encuadre legal argentino asociado a hallazgos o hipótesis.")
    if case.damage_items:
        strengths.append(f"Se cuantificó un daño preliminar de {total_damage:.2f} ARS.")
    else:
        weaknesses.append("No hay cuantificación económica del daño cargada.")

    if "fuente pendiente de verificación" in report_text.lower():
        next_steps.append("Verificar manualmente fuentes normativas, doctrina o jurisprudencia antes de usar el informe como final.")
    if "no resulta posible afirmar autoría personal" not in report_text.lower():
        next_steps.append("Agregar limitación expresa sobre autoría personal si la evidencia solo permite compatibilidad técnica.")
    if not case.actions:
        next_steps.append("Registrar acciones de cadena de custodia para cada evidencia relevante.")
    if any(not item.formula_used or not item.value_source for item in case.damage_items):
        next_steps.append("Completar fórmula y fuente de valor en cada rubro económico.")
    if not next_steps:
        next_steps.append("Revisar redacción final, anexos y fuentes antes de exportar una versión profesional.")

    theory = (
        f"La teoría preliminar del caso se orienta a {', '.join(legal['incident_classification'])}. "
        "La hipótesis debe sostenerse mediante la secuencia dato técnico → evidencia preservada → hallazgo verificable → "
        "hipótesis investigativa → conclusión jurídicamente defendible."
    )
    legal_justification = (
        f"{legal['justification']} La competencia y vía procesal deben validarse según domicilio, lugar del hecho, "
        "sujetos intervinientes, plataforma utilizada y reglas procesales aplicables."
    )
    dogmatic_assessment = (
        "Desde la dogmática penal, el caso debe explicarse sin saltar del daño a la culpabilidad. "
        "Primero se identifica el hecho técnicamente comprobado; luego la inferencia pericial; después la hipótesis investigativa; "
        "y recién entonces la posible relevancia jurídica. Deben analizarse legalidad, tipicidad objetiva, tipicidad subjetiva, "
        "dolo directo o eventual, antijuridicidad, culpabilidad, autoría o participación, nexo causal e imputación objetiva. "
        "La responsabilidad penal objetiva queda descartada como método de atribución: el informe solo puede sostener compatibilidad "
        "o probabilidad si existe evidencia suficiente sobre conducta, conocimiento, voluntad, rol e intervención concreta. "
        f"Criterios guía incorporados: {dogmatic_context().replace(chr(10), '; ')}."
    )
    procedural_assessment = (
        "Desde el Código Procesal Penal de la Nación, el informe debe transformarse en una hoja de ruta probatoria: "
        "formular o ampliar denuncia, preservar de inmediato la evidencia digital, identificar qué medidas requieren oficio, "
        "requerir registros a proveedores de comunicaciones, plataformas, bancos, billeteras, fintech o exchanges, documentar "
        "titularidad y movimientos de fondos, pedir pericias sobre audio, metadatos, dispositivos y registros de conexión, "
        "y conservar cadena de custodia. Si el caso puede ser federal o se encuentra alcanzado por implementación del Código "
        "Procesal Penal Federal, debe indicarse la necesidad de validar competencia material, territorial y funcional. "
        "La aplicación procesal no prueba culpabilidad: ordena medios de prueba pertinentes, útiles, proporcionales y controlables. "
        f"Criterios procesales incorporados: {procedural_context().replace(chr(10), '; ')}."
    )
    evidentiary_assessment = (
        f"El soporte probatorio actual obtiene un puntaje de {scores['evidence_score']}/100 en evidencia, "
        f"{scores['finding_score']}/100 en hallazgos y {scores['custody_score']}/100 en cadena de custodia. "
        "La evaluación debe privilegiar evidencia con hash, bitácora y vínculo explícito con hallazgos."
    )
    conclusion = (
        "Con el alcance y limitaciones indicadas, la IA puede asistir en ordenar y justificar el caso, "
        "pero la conclusión final debe ser revisada por profesional humano. La evidencia disponible permite "
        "formular compatibilidades técnicas y jurídicas preliminares, no atribuciones personales definitivas."
    )

    return {
        **scores,
        "status": "sólido para revisión humana" if scores["overall_score"] >= 80 else "requiere fortalecimiento" if scores["overall_score"] >= 55 else "débil",
        "case_theory": normalize_spanish(theory),
        "legal_justification": normalize_spanish(legal_justification),
        "dogmatic_assessment": normalize_spanish(dogmatic_assessment),
        "procedural_assessment": normalize_spanish(procedural_assessment),
        "evidentiary_assessment": normalize_spanish(evidentiary_assessment),
        "economic_assessment": normalize_spanish(
            f"El daño económico informado asciende preliminarmente a {total_damage:.2f} ARS. "
            "Cada monto debe conservar fórmula, fuente, fecha base, evidencia de respaldo y nivel de certeza."
        ),
        "strengths": [normalize_spanish(item) for item in strengths],
        "weaknesses": [normalize_spanish(item) for item in weaknesses],
        "next_steps": [normalize_spanish(item) for item in next_steps],
        "defensible_conclusion": normalize_spanish(conclusion),
        "legal_classification": legal["incident_classification"],
        "competence": legal["competence"],
    }


def evaluation_to_markdown(evaluation: dict) -> str:
    def bullet(items: list[str]) -> str:
        return "\n".join(f"- {normalize_spanish(item)}" for item in items) or "- Sin elementos."

    return normalize_spanish(f"""## Evaluación integral IA del caso

### Score integral

**Score general:** {evaluation['overall_score']}/100  
**Estado:** {evaluation['status']}

| Dimensión | Score |
| --- | ---: |
| Evidencia | {evaluation['evidence_score']}/100 |
| Hallazgos | {evaluation['finding_score']}/100 |
| Hipótesis | {evaluation['hypothesis_score']}/100 |
| Legal | {evaluation['legal_score']}/100 |
| Daño económico | {evaluation['economic_score']}/100 |
| Cadena de custodia | {evaluation['custody_score']}/100 |
| Informe | {evaluation['report_score']}/100 |

### Teoría preliminar del caso

{evaluation['case_theory']}

### Justificación legal asistida

{evaluation['legal_justification']}

### Evaluación dogmática penal

{evaluation['dogmatic_assessment']}

### Aplicación procesal penal

{evaluation['procedural_assessment']}

### Evaluación probatoria

{evaluation['evidentiary_assessment']}

### Evaluación económica

{evaluation['economic_assessment']}

### Fortalezas

{bullet(evaluation['strengths'])}

### Debilidades

{bullet(evaluation['weaknesses'])}

### Próximos pasos

{bullet(evaluation['next_steps'])}

### Conclusión defendible sugerida

{evaluation['defensible_conclusion']}

> Advertencia: esta evaluación es asistida por IA y requiere revisión humana técnica y jurídica. No inventa fuentes, doctrina ni jurisprudencia.
""")

