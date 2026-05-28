from __future__ import annotations

import re

from operia.cases.models import Case, DamageItem, Finding, Hypothesis, TechnicalData
from operia.evidence.models import ChainOfCustodyAction
from operia.legal_report.services.ai_legal_service import apply_automatic_legal_mappings, classify_cybercrime
from operia.legal_report.services.text_service import normalize_spanish


def _case_text(case: Case) -> str:
    parts = [
        case.title,
        case.description,
        case.incident_type,
        case.general_observations,
        " ".join(item.description for item in case.technical_data),
        " ".join(item.value for item in case.technical_data),
        " ".join(item.description for item in case.evidence),
        " ".join(f"{item.concept} {item.amount} {item.currency} {item.observations}" for item in case.damage_items),
    ]
    return normalize_spanish(" ".join(parts))


def _parse_argentine_amounts(text: str) -> list[float]:
    normalized = normalize_spanish(text)
    candidates: list[float] = []
    money_patterns = [
        r"(?:\$|ars|pesos?|suma de|importe de)\s*([0-9]{1,3}(?:\.[0-9]{3})+(?:,[0-9]{1,2})?)",
        r"([0-9]{1,3}(?:\.[0-9]{3})+(?:,[0-9]{1,2})?)\s*(?:ars|pesos?)",
        r"(?:\$|ars|pesos?|suma de|importe de)\s*([0-9]+(?:,[0-9]{1,2})?)",
    ]
    for pattern in money_patterns:
        for match in re.findall(pattern, normalized, flags=re.IGNORECASE):
            raw = match.replace(".", "").replace(",", ".")
            try:
                value = float(raw)
            except ValueError:
                continue
            if value > 0:
                candidates.append(value)
    return sorted(set(candidates), reverse=True)


def _suggest_incident_type(case: Case) -> str:
    text = _case_text(case).lower()
    if any(term in text for term in ["secuestr", "rescate", "lo mataban", "matar", "amenaza", "extors"]):
        if any(term in text for term in ["whatsapp", "voz", "audio", "ia", "deepfake"]):
            return "extorsión digital con posible engaño habilitado por IA"
        return "extorsión digital"
    labels = classify_cybercrime(case)
    if labels:
        label = labels[0]
        if "transferencia cripto" in label:
            return "transferencia cripto fraudulenta"
        if "phishing" in label:
            return "phishing o suplantación digital"
        if "deepfake" in label:
            return "deepfake o engaño habilitado por IA"
        if "acceso" in label:
            return "acceso no autorizado"
    return normalize_spanish(case.incident_type or "incidente mixto")


def _has_title(items, title: str) -> bool:
    needle = normalize_spanish(title).lower()
    return any(normalize_spanish(getattr(item, "title", "")).lower() == needle for item in items)


def _has_damage_concept(case: Case, concept: str) -> DamageItem | None:
    needle = normalize_spanish(concept).lower()
    for item in case.damage_items:
        if needle in normalize_spanish(item.concept).lower():
            return item
    return None


def analyze_consistency(case: Case) -> dict:
    text = _case_text(case)
    amounts = _parse_argentine_amounts(text)
    detected_amount = amounts[0] if amounts else 0
    current_damage = sum(item.amount for item in case.damage_items)
    suggested_incident = _suggest_incident_type(case)
    problems: list[str] = []
    recommendations: list[str] = []
    suggested_actions: list[str] = []

    if detected_amount and (current_damage == 0 or current_damage < detected_amount * 0.1):
        problems.append(
            f"El relato sugiere un monto aproximado de {detected_amount:,.2f} ARS, pero la cuantificación cargada suma {current_damage:,.2f} ARS."
        )
        suggested_actions.append("Crear o corregir rubro de daño patrimonial directo con el monto detectado.")
    if normalize_spanish(case.incident_type).lower() in ["otro", "incidente mixto", ""]:
        problems.append(f"El tipo de incidente es genérico. Se sugiere reclasificarlo como: {suggested_incident}.")
        suggested_actions.append("Actualizar tipo de incidente para mejorar encuadre penal y procesal.")
    if not case.technical_data:
        problems.append("No hay dato técnico inicial cargado; el relato debería registrarse como denuncia o relato de víctima.")
        suggested_actions.append("Crear dato técnico inicial desde el relato del caso.")
    if not case.findings:
        problems.append("No hay hallazgos técnicos; el informe no debería saltar directamente a hipótesis o conclusión.")
        suggested_actions.append("Crear hallazgos sugeridos en estado borrador, con limitaciones expresas.")
    if case.hypotheses and not case.findings:
        problems.append("Hay hipótesis sin hallazgos previos; la cadena lógica queda débil.")
    if not case.hypotheses:
        suggested_actions.append("Crear hipótesis principal y alternativa con hechos faltantes por probar.")
    if not case.legal_mappings:
        suggested_actions.append("Generar encuadre legal automático penal, procesal, civil y probatorio.")
    if case.damage_items and any(not item.formula_used or not item.value_source for item in case.damage_items):
        problems.append("Hay daños sin fórmula o fuente de valor.")
        suggested_actions.append("Completar fórmula y fuente en los rubros económicos.")

    recommendations.extend([
        "Preservar archivos originales, capturas, comprobantes y audios antes de formular conclusiones fuertes.",
        "Pedir medidas procesales de preservación y oficios a plataformas, bancos, billeteras o proveedores involucrados.",
        "Expresar toda conclusión como compatibilidad técnica preliminar hasta contar con evidencia validada.",
    ])

    return {
        "detected_amount": detected_amount,
        "current_damage": current_damage,
        "final_damage": current_damage,
        "suggested_incident_type": suggested_incident,
        "problems": [normalize_spanish(item) for item in problems],
        "suggested_actions": [normalize_spanish(item) for item in suggested_actions],
        "recommendations": [normalize_spanish(item) for item in recommendations],
    }


def enrich_case(case: Case, apply: bool = True) -> dict:
    analysis = analyze_consistency(case)
    created: list[str] = []
    updated: list[str] = []
    text = _case_text(case)
    detected_amount = analysis["detected_amount"]

    if not apply:
        return {**analysis, "created": created, "updated": updated}

    suggested_incident = analysis["suggested_incident_type"]
    if normalize_spanish(case.incident_type).lower() in ["otro", "incidente mixto", ""]:
        case.incident_type = suggested_incident
        updated.append(f"Tipo de incidente actualizado a: {suggested_incident}.")

    if not case.technical_data and normalize_spanish(case.description):
        td = TechnicalData(
            case=case,
            data_type="denuncia o relato de víctima",
            description=normalize_spanish(case.description),
            source="Relato inicial cargado en el caso",
            loaded_by="Operia IA",
            value=normalize_spanish(case.description),
            observations="Dato técnico generado desde el relato para iniciar la cadena lógica. Requiere validación humana.",
            initial_relevance="alto",
            status="pendiente",
        )
        case.technical_data.append(td)
        created.append("Dato técnico inicial creado desde el relato del caso.")

    if detected_amount:
        damage = _has_damage_concept(case, "fondos")
        if damage and damage.amount < detected_amount * 0.1:
            damage.amount = detected_amount
            damage.currency = "ARS"
            damage.formula_used = damage.formula_used or "Daño patrimonial directo = importe transferido denunciado"
            damage.value_source = damage.value_source or "Relato del caso; requiere comprobante bancario"
            damage.supporting_evidence = damage.supporting_evidence or "Pendiente de comprobante o evidencia bancaria"
            damage.observations = normalize_spanish(
                f"Monto corregido automáticamente por consistencia con el relato: {detected_amount:,.2f} ARS. Requiere validación documental."
            )
            updated.append("Daño patrimonial directo corregido según monto detectado en el relato.")
        elif not damage and sum(item.amount for item in case.damage_items) < detected_amount * 0.1:
            case.damage_items.append(DamageItem(
                case=case,
                concept="fondos sustraídos",
                amount=detected_amount,
                currency="ARS",
                value_source="Relato del caso; requiere comprobante bancario",
                formula_used="Daño patrimonial directo = importe transferido denunciado",
                supporting_evidence="Pendiente de comprobante o evidencia bancaria",
                certainty_level="medio",
                observations="Rubro creado automáticamente por consistencia. Validar con documentación.",
            ))
            created.append("Daño patrimonial directo creado con el monto detectado en el relato.")

    first_td = case.technical_data[0] if case.technical_data else None
    first_ev = case.evidence[0] if case.evidence else None
    if not _has_title(case.findings, "Relato compatible con maniobra de extorsión digital"):
        if any(term in text.lower() for term in ["secuestr", "rescate", "amenaza", "lo mataban", "matar", "whatsapp"]):
            case.findings.append(Finding(
                case=case,
                technical_data_id=first_td.id if first_td and first_td.id else None,
                evidence_id=first_ev.id if first_ev else None,
                title="Relato compatible con maniobra de extorsión digital",
                technical_finding="El relato describe presión temporal, amenaza grave y exigencia de transferencia, patrón compatible con extorsión digital o fraude bajo intimidación.",
                explanation="Hallazgo sugerido desde el relato. No acredita autoría personal ni confirma por sí solo la existencia de una organización criminal.",
                confidence_level="medio" if first_ev else "bajo",
                weaknesses_or_limitations="Requiere evidencia preservada: audio, capturas, comprobante de transferencia, registros de plataforma y constancias bancarias.",
                tools_used="Operia IA de consistencia",
                supporting_evidence="Relato de víctima; evidencia documental pendiente o vinculada si existe.",
                preliminary_legal_relevance="Puede orientar análisis de extorsión, estafa, suplantación, dolo, daño patrimonial y medidas procesales urgentes.",
                status="borrador",
            ))
            created.append("Hallazgo sugerido creado en borrador.")

    if not _has_title(case.hypotheses, "Maniobra coordinada de extorsión digital"):
        case.hypotheses.append(Hypothesis(
            case=case,
            title="Maniobra coordinada de extorsión digital",
            description="Una o más personas habrían utilizado un canal digital y presión intimidatoria para inducir a la víctima a realizar una transferencia patrimonial.",
            finding_ids="pendiente de vinculación",
            evidence_ids="pendiente de vinculación",
            support_degree="débil" if not case.evidence else "medio",
            alternative_hypotheses="Imitación humana de voz sin IA; uso de cuenta mule sin conocimiento pleno; error o transferencia no vinculada al hecho.",
            error_risks="Confundir compatibilidad narrativa con autoría; asumir deepfake sin pericia acústica; atribuir responsabilidad al titular de cuenta sin prueba subjetiva.",
            facts_to_prove="Origen de la llamada, titularidad de cuenta receptora, movimientos posteriores, existencia o no de IA, dolo, intervención concreta y nexo causal.",
            provisional_conclusion="La hipótesis es plausible, pero requiere evidencia preservada, oficios y pericias antes de formular conclusiones fuertes.",
            status="abierta",
        ))
        created.append("Hipótesis principal y alternativas creadas.")

    legal_created, legal_analysis = apply_automatic_legal_mappings(case)
    if legal_created:
        created.append(f"{len(legal_created)} encuadre(s) legal(es) automático(s) creados.")

    case.actions.append(ChainOfCustodyAction(
        case=case,
        action_type="revisión",
        user_responsible="Operia IA",
        user_role="asistente jurídico-forense",
        detailed_description="Motor de consistencia y enriquecimiento revisó relato, daños, tipo de incidente, hallazgos, hipótesis y encuadre legal.",
        tool_used="Operia IA consistencia local",
        result_obtained="; ".join(created + updated) or "Sin cambios automáticos; se emitieron recomendaciones.",
        legal_observations=legal_analysis["defensible_conclusion"],
        status="requiere revisión humana",
    ))

    return {
        **analysis,
        "final_damage": sum(item.amount for item in case.damage_items),
        "created": [normalize_spanish(item) for item in created],
        "updated": [normalize_spanish(item) for item in updated],
    }

