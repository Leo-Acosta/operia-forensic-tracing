from __future__ import annotations

from dataclasses import dataclass

from operia.legal_knowledge.models import LegalSource
from operia.legal_report.services.text_service import normalize_spanish


@dataclass(frozen=True)
class OfficialLegalSource:
    title: str
    source_type: str
    citation: str
    url: str
    content: str
    verified: bool = True


OFFICIAL_LEGAL_SOURCES: list[OfficialLegalSource] = [
    OfficialLegalSource(
        "Código Penal argentino",
        "norma",
        "Código Penal de la Nación Argentina, texto actualizado. Fuente oficial Infoleg/Argentina.gob.ar.",
        "https://www.argentina.gob.ar/normativa/nacional/ley-11179-16546/actualizacion",
        "Base penal general: legalidad, tipicidad, autoría, participación, tentativa, dolo, culpa, delitos contra la propiedad, privacidad, sistemas y bienes jurídicos vinculados.",
    ),
    OfficialLegalSource(
        "Ley 26.388 de delitos informáticos",
        "norma",
        "Ley 26.388. Modificación del Código Penal en materia de criminalidad informática. Fuente oficial Infoleg/Argentina.gob.ar.",
        "https://www.argentina.gob.ar/normativa/nacional/ley-26388-141790/texto",
        "Incorpora y modifica figuras penales vinculadas con datos, sistemas, comunicaciones, privacidad, daño informático y conductas cometidas mediante tecnologías de la información.",
    ),
    OfficialLegalSource(
        "Código Procesal Penal de la Nación",
        "norma procesal",
        "Ley 23.984. Código Procesal Penal de la Nación, texto actualizado. Fuente oficial Infoleg/Argentina.gob.ar.",
        "https://www.argentina.gob.ar/normativa/nacional/ley-23984-383/texto",
        "Marco procesal penal nacional para denuncia, investigación, medidas de prueba, intervención del Ministerio Público, valoración de evidencia, actos urgentes, secuestro, peritajes, oficios y resguardo de garantías.",
    ),
    OfficialLegalSource(
        "Código Procesal Penal Federal",
        "norma procesal",
        "Ley 27.063. Código Procesal Penal Federal, texto oficial. Fuente oficial Infoleg/Argentina.gob.ar.",
        "https://www.argentina.gob.ar/normativa/nacional/ley-27063-239340/texto",
        "Marco procesal federal de orientación acusatoria para investigación penal, actuación fiscal, medidas de investigación, evidencia digital, cooperación y tutela judicial efectiva, sujeto a implementación territorial.",
    ),
    OfficialLegalSource(
        "Ley 25.326 de Protección de Datos Personales",
        "norma",
        "Ley 25.326. Protección de Datos Personales. Fuente oficial Infoleg/Argentina.gob.ar.",
        "https://www.argentina.gob.ar/normativa/nacional/ley-25326-64790/texto",
        "Marco argentino de protección de datos personales, habeas data, tratamiento, confidencialidad, seguridad, derechos del titular y responsabilidades.",
    ),
    OfficialLegalSource(
        "Ley 24.240 de Defensa del Consumidor",
        "norma",
        "Ley 24.240. Defensa del Consumidor. Fuente oficial Infoleg/Argentina.gob.ar.",
        "https://www.argentina.gob.ar/normativa/nacional/ley-24240-638/texto",
        "Relaciones de consumo, deber de información, seguridad, trato digno, responsabilidad de proveedores, plataformas, entidades financieras o servicios digitales.",
    ),
    OfficialLegalSource(
        "Código Civil y Comercial de la Nación",
        "norma",
        "Código Civil y Comercial de la Nación. Fuente oficial Infoleg/Argentina.gob.ar.",
        "https://www.argentina.gob.ar/normativa/nacional/ley-26994-235975/texto",
        "Responsabilidad civil, daño resarcible, nexo causal, factor de atribución, reparación plena, deber de prevención y cuantificación patrimonial.",
    ),
    OfficialLegalSource(
        "Ley 27.411 - Convenio de Budapest sobre Ciberdelito",
        "tratado",
        "Ley 27.411. Aprobación del Convenio sobre Ciberdelito del Consejo de Europa. Fuente oficial Infoleg.",
        "https://www.argentina.gob.ar/normativa/nacional/ley-27411-304798/texto",
        "Marco internacional de cooperación, armonización penal, investigación, preservación y obtención de evidencia electrónica transfronteriza.",
    ),
    OfficialLegalSource(
        "Convenio de Budapest sobre Ciberdelincuencia",
        "tratado internacional",
        "Council of Europe. Convention on Cybercrime, ETS No. 185.",
        "https://www.coe.int/en/web/cybercrime/the-budapest-convention",
        "Estándar internacional para criminalización de conductas, poderes procesales, preservación de datos, cooperación internacional y evidencia electrónica.",
    ),
    OfficialLegalSource(
        "Segundo Protocolo Adicional al Convenio de Budapest",
        "tratado internacional",
        "Council of Europe. Second Additional Protocol to the Cybercrime Convention, CETS No. 224.",
        "https://www.coe.int/en/web/cybercrime/second-additional-protocol",
        "Cooperación reforzada y divulgación de evidencia electrónica, con foco en acceso transfronterizo, proveedores de servicios y garantías.",
    ),
    OfficialLegalSource(
        "Normativa argentina de ciberseguridad",
        "fuente oficial",
        "Argentina.gob.ar. Dirección Nacional de Ciberseguridad - Normativa.",
        "https://www.argentina.gob.ar/jefatura/innovacion-publica/direccion-nacional-ciberseguridad/normativa",
        "Repositorio oficial de normativa, políticas, estrategias y lineamientos argentinos vinculados a ciberseguridad.",
    ),
    OfficialLegalSource(
        "Política criminal argentina sobre ciberdelitos",
        "fuente oficial",
        "Argentina.gob.ar. Subsecretaría de Política Criminal - Ciberdelitos.",
        "https://www.argentina.gob.ar/node/200726",
        "Lineamientos institucionales sobre prevención, investigación, persecución penal de ciberdelitos, evidencia digital, cooperación internacional y adecuación normativa.",
    ),
]


PENAL_DOGMATIC_LEXICON = [
    "principio de legalidad",
    "tipicidad objetiva y subjetiva",
    "bien jurídico protegido",
    "antijuridicidad",
    "culpabilidad",
    "dolo directo, eventual o eventualidad cognoscitiva",
    "culpa, imprudencia o negligencia cuando corresponda",
    "imputación objetiva del resultado",
    "creación o incremento de un riesgo jurídicamente desaprobado",
    "realización del riesgo en el resultado",
    "nexo causal y nexo de imputación",
    "autoría, coautoría, participación primaria o secundaria",
    "tentativa, consumación e iter criminis",
    "error de tipo o error de prohibición cuando resulte plausible",
    "principio de lesividad",
    "proporcionalidad y necesidad de medidas probatorias",
    "estándar de sospecha, probabilidad y suficiencia probatoria",
    "cadena de custodia, integridad, autenticidad y trazabilidad",
]

PROCEDURAL_CRIMINAL_LEXICON = [
    "denuncia penal y noticia criminis",
    "competencia material, territorial y federal u ordinaria",
    "intervención fiscal y dirección de la investigación",
    "medidas urgentes de preservación de evidencia digital",
    "oficios a bancos, billeteras virtuales, exchanges, plataformas y proveedores",
    "requerimiento de registros de conexión, IP, dispositivo, titularidad y movimientos",
    "secuestro, extracción forense y peritaje informático cuando corresponda",
    "resguardo de cadena de custodia, autenticidad, integridad y trazabilidad",
    "control de legalidad, proporcionalidad, necesidad y resguardo de garantías",
    "valoración probatoria preliminar sin prejuzgamiento de autoría",
]


def sync_official_sources(db) -> int:
    created_or_updated = 0
    for source in OFFICIAL_LEGAL_SOURCES:
        item = db.query(LegalSource).filter_by(title=source.title).first()
        payload = {
            "source_type": source.source_type,
            "citation": normalize_spanish(source.citation),
            "url": source.url,
            "content": normalize_spanish(source.content),
            "verified": source.verified,
        }
        if item:
            changed = False
            for key, value in payload.items():
                if getattr(item, key) != value:
                    setattr(item, key, value)
                    changed = True
            if changed:
                created_or_updated += 1
        else:
            db.add(LegalSource(title=source.title, **payload))
            created_or_updated += 1
    return created_or_updated


def legal_sources_context(sources: list[LegalSource]) -> str:
    verified = [item for item in sources if item.verified]
    if not verified:
        return "No hay fuentes oficiales verificadas cargadas; toda referencia normativa debe marcarse como Fuente pendiente de verificación."
    lines = [
        f"- {normalize_spanish(item.title)}: {normalize_spanish(item.citation)} URL: {item.url}"
        for item in verified
    ]
    return "\n".join(lines)


def dogmatic_context() -> str:
    return "\n".join(f"- {item}" for item in PENAL_DOGMATIC_LEXICON)


def procedural_context() -> str:
    return "\n".join(f"- {item}" for item in PROCEDURAL_CRIMINAL_LEXICON)

