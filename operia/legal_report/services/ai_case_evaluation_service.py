from __future__ import annotations

from operia.legal_report.models import Report
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
        weaknesses.append("No hay evidencia preservada; la evaluaciÃ³n queda en nivel preliminar bajo.")
    if any(item.sha256_hash for item in case.evidence):
        strengths.append("Existe al menos una evidencia con hash SHA-256, Ãºtil para sostener integridad.")
    elif case.evidence:
        weaknesses.append("Las evidencias cargadas no tienen hash SHA-256 suficiente para soporte fuerte.")

    if case.findings:
        strengths.append(f"Hay {len(case.findings)} hallazgo(s) que conectan evidencia con interpretaciÃ³n tÃ©cnica.")
    else:
        weaknesses.append("Faltan hallazgos tÃ©cnicos; no conviene avanzar a conclusiones jurÃ­dicas sin esa capa intermedia.")
    if case.hypotheses:
        strengths.append(f"Hay {len(case.hypotheses)} hipÃ³tesis investigativa(s) registradas.")
    else:
        weaknesses.append("Faltan hipÃ³tesis investigativas y alternativas para evitar una lectura Ãºnica del caso.")
    if case.legal_mappings:
        strengths.append(f"Hay {len(case.legal_mappings)} encuadre(s) legal(es) cargado(s) o generado(s).")
    else:
        weaknesses.append("Falta encuadre legal argentino asociado a hallazgos o hipÃ³tesis.")
    if case.damage_items:
        strengths.append(f"Se cuantificÃ³ un daÃ±o preliminar de {total_damage:.2f} ARS.")
    else:
        weaknesses.append("No hay cuantificaciÃ³n econÃ³mica del daÃ±o cargada.")

    if "fuente pendiente de verificaciÃ³n" in report_text.lower():
        next_steps.append("Verificar manualmente fuentes normativas, doctrina o jurisprudencia antes de usar el informe como final.")
    if "no resulta posible afirmar autorÃ­a personal" not in report_text.lower():
        next_steps.append("Agregar limitaciÃ³n expresa sobre autorÃ­a personal si la evidencia solo permite compatibilidad tÃ©cnica.")
    if not case.actions:
        next_steps.append("Registrar acciones de cadena de custodia para cada evidencia relevante.")
    if any(not item.formula_used or not item.value_source for item in case.damage_items):
        next_steps.append("Completar fÃ³rmula y fuente de valor en cada rubro econÃ³mico.")
    if not next_steps:
        next_steps.append("Revisar redacciÃ³n final, anexos y fuentes antes de exportar una versiÃ³n profesional.")

    theory = (
        f"La teorÃ­a preliminar del caso se orienta a {', '.join(legal['incident_classification'])}. "
        "La hipÃ³tesis debe sostenerse mediante la secuencia dato tÃ©cnico â†’ evidencia preservada â†’ hallazgo verificable â†’ "
        "hipÃ³tesis investigativa â†’ conclusiÃ³n jurÃ­dicamente defendible."
    )
    legal_justification = (
        f"{legal['justification']} La competencia y vÃ­a procesal deben validarse segÃºn domicilio, lugar del hecho, "
        "sujetos intervinientes, plataforma utilizada y reglas procesales aplicables."
    )
    dogmatic_assessment = (
        "Desde la dogmÃ¡tica penal, el caso debe explicarse sin saltar del daÃ±o a la culpabilidad. "
        "Primero se identifica el hecho tÃ©cnicamente comprobado; luego la inferencia pericial; despuÃ©s la hipÃ³tesis investigativa; "
        "y reciÃ©n entonces la posible relevancia jurÃ­dica. Deben analizarse legalidad, tipicidad objetiva, tipicidad subjetiva, "
        "dolo directo o eventual, antijuridicidad, culpabilidad, autorÃ­a o participaciÃ³n, nexo causal e imputaciÃ³n objetiva. "
        "La responsabilidad penal objetiva queda descartada como mÃ©todo de atribuciÃ³n: el informe solo puede sostener compatibilidad "
        "o probabilidad si existe evidencia suficiente sobre conducta, conocimiento, voluntad, rol e intervenciÃ³n concreta. "
        f"Criterios guÃ­a incorporados: {dogmatic_context().replace(chr(10), '; ')}."
    )
    procedural_assessment = (
        "Desde el CÃ³digo Procesal Penal de la NaciÃ³n, el informe debe transformarse en una hoja de ruta probatoria: "
        "formular o ampliar denuncia, preservar de inmediato la evidencia digital, identificar quÃ© medidas requieren oficio, "
        "requerir registros a proveedores de comunicaciones, plataformas, bancos, billeteras, fintech o exchanges, documentar "
        "titularidad y movimientos de fondos, pedir pericias sobre audio, metadatos, dispositivos y registros de conexiÃ³n, "
        "y conservar cadena de custodia. Si el caso puede ser federal o se encuentra alcanzado por implementaciÃ³n del CÃ³digo "
        "Procesal Penal Federal, debe indicarse la necesidad de validar competencia material, territorial y funcional. "
        "La aplicaciÃ³n procesal no prueba culpabilidad: ordena medios de prueba pertinentes, Ãºtiles, proporcionales y controlables. "
        f"Criterios procesales incorporados: {procedural_context().replace(chr(10), '; ')}."
    )
    evidentiary_assessment = (
        f"El soporte probatorio actual obtiene un puntaje de {scores['evidence_score']}/100 en evidencia, "
        f"{scores['finding_score']}/100 en hallazgos y {scores['custody_score']}/100 en cadena de custodia. "
        "La evaluaciÃ³n debe privilegiar evidencia con hash, bitÃ¡cora y vÃ­nculo explÃ­cito con hallazgos."
    )
    conclusion = (
        "Con el alcance y limitaciones indicadas, la IA puede asistir en ordenar y justificar el caso, "
        "pero la conclusiÃ³n final debe ser revisada por profesional humano. La evidencia disponible permite "
        "formular compatibilidades tÃ©cnicas y jurÃ­dicas preliminares, no atribuciones personales definitivas."
    )

    return {
        **scores,
        "status": "sÃ³lido para revisiÃ³n humana" if scores["overall_score"] >= 80 else "requiere fortalecimiento" if scores["overall_score"] >= 55 else "dÃ©bil",
        "case_theory": normalize_spanish(theory),
        "legal_justification": normalize_spanish(legal_justification),
        "dogmatic_assessment": normalize_spanish(dogmatic_assessment),
        "procedural_assessment": normalize_spanish(procedural_assessment),
        "evidentiary_assessment": normalize_spanish(evidentiary_assessment),
        "economic_assessment": normalize_spanish(
            f"El daÃ±o econÃ³mico informado asciende preliminarmente a {total_damage:.2f} ARS. "
            "Cada monto debe conservar fÃ³rmula, fuente, fecha base, evidencia de respaldo y nivel de certeza."
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

    return normalize_spanish(f"""## EvaluaciÃ³n integral IA del caso

### Score integral

**Score general:** {evaluation['overall_score']}/100  
**Estado:** {evaluation['status']}

| DimensiÃ³n | Score |
| --- | ---: |
| Evidencia | {evaluation['evidence_score']}/100 |
| Hallazgos | {evaluation['finding_score']}/100 |
| HipÃ³tesis | {evaluation['hypothesis_score']}/100 |
| Legal | {evaluation['legal_score']}/100 |
| DaÃ±o econÃ³mico | {evaluation['economic_score']}/100 |
| Cadena de custodia | {evaluation['custody_score']}/100 |
| Informe | {evaluation['report_score']}/100 |

### TeorÃ­a preliminar del caso

{evaluation['case_theory']}

### JustificaciÃ³n legal asistida

{evaluation['legal_justification']}

### EvaluaciÃ³n dogmÃ¡tica penal

{evaluation['dogmatic_assessment']}

### AplicaciÃ³n procesal penal

{evaluation['procedural_assessment']}

### EvaluaciÃ³n probatoria

{evaluation['evidentiary_assessment']}

### EvaluaciÃ³n econÃ³mica

{evaluation['economic_assessment']}

### Fortalezas

{bullet(evaluation['strengths'])}

### Debilidades

{bullet(evaluation['weaknesses'])}

### PrÃ³ximos pasos

{bullet(evaluation['next_steps'])}

### ConclusiÃ³n defendible sugerida

{evaluation['defensible_conclusion']}

> Advertencia: esta evaluaciÃ³n es asistida por IA y requiere revisiÃ³n humana tÃ©cnica y jurÃ­dica. No inventa fuentes, doctrina ni jurisprudencia.
""")

