from __future__ import annotations

from dataclasses import dataclass

from operia.legal_report.models import LegalSource
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
        "CÃ³digo Penal argentino",
        "norma",
        "CÃ³digo Penal de la NaciÃ³n Argentina, texto actualizado. Fuente oficial Infoleg/Argentina.gob.ar.",
        "https://www.argentina.gob.ar/normativa/nacional/ley-11179-16546/actualizacion",
        "Base penal general: legalidad, tipicidad, autorÃ­a, participaciÃ³n, tentativa, dolo, culpa, delitos contra la propiedad, privacidad, sistemas y bienes jurÃ­dicos vinculados.",
    ),
    OfficialLegalSource(
        "Ley 26.388 de delitos informÃ¡ticos",
        "norma",
        "Ley 26.388. ModificaciÃ³n del CÃ³digo Penal en materia de criminalidad informÃ¡tica. Fuente oficial Infoleg/Argentina.gob.ar.",
        "https://www.argentina.gob.ar/normativa/nacional/ley-26388-141790/texto",
        "Incorpora y modifica figuras penales vinculadas con datos, sistemas, comunicaciones, privacidad, daÃ±o informÃ¡tico y conductas cometidas mediante tecnologÃ­as de la informaciÃ³n.",
    ),
    OfficialLegalSource(
        "CÃ³digo Procesal Penal de la NaciÃ³n",
        "norma procesal",
        "Ley 23.984. CÃ³digo Procesal Penal de la NaciÃ³n, texto actualizado. Fuente oficial Infoleg/Argentina.gob.ar.",
        "https://www.argentina.gob.ar/normativa/nacional/ley-23984-383/texto",
        "Marco procesal penal nacional para denuncia, investigaciÃ³n, medidas de prueba, intervenciÃ³n del Ministerio PÃºblico, valoraciÃ³n de evidencia, actos urgentes, secuestro, peritajes, oficios y resguardo de garantÃ­as.",
    ),
    OfficialLegalSource(
        "CÃ³digo Procesal Penal Federal",
        "norma procesal",
        "Ley 27.063. CÃ³digo Procesal Penal Federal, texto oficial. Fuente oficial Infoleg/Argentina.gob.ar.",
        "https://www.argentina.gob.ar/normativa/nacional/ley-27063-239340/texto",
        "Marco procesal federal de orientaciÃ³n acusatoria para investigaciÃ³n penal, actuaciÃ³n fiscal, medidas de investigaciÃ³n, evidencia digital, cooperaciÃ³n y tutela judicial efectiva, sujeto a implementaciÃ³n territorial.",
    ),
    OfficialLegalSource(
        "Ley 25.326 de ProtecciÃ³n de Datos Personales",
        "norma",
        "Ley 25.326. ProtecciÃ³n de Datos Personales. Fuente oficial Infoleg/Argentina.gob.ar.",
        "https://www.argentina.gob.ar/normativa/nacional/ley-25326-64790/texto",
        "Marco argentino de protecciÃ³n de datos personales, habeas data, tratamiento, confidencialidad, seguridad, derechos del titular y responsabilidades.",
    ),
    OfficialLegalSource(
        "Ley 24.240 de Defensa del Consumidor",
        "norma",
        "Ley 24.240. Defensa del Consumidor. Fuente oficial Infoleg/Argentina.gob.ar.",
        "https://www.argentina.gob.ar/normativa/nacional/ley-24240-638/texto",
        "Relaciones de consumo, deber de informaciÃ³n, seguridad, trato digno, responsabilidad de proveedores, plataformas, entidades financieras o servicios digitales.",
    ),
    OfficialLegalSource(
        "CÃ³digo Civil y Comercial de la NaciÃ³n",
        "norma",
        "CÃ³digo Civil y Comercial de la NaciÃ³n. Fuente oficial Infoleg/Argentina.gob.ar.",
        "https://www.argentina.gob.ar/normativa/nacional/ley-26994-235975/texto",
        "Responsabilidad civil, daÃ±o resarcible, nexo causal, factor de atribuciÃ³n, reparaciÃ³n plena, deber de prevenciÃ³n y cuantificaciÃ³n patrimonial.",
    ),
    OfficialLegalSource(
        "Ley 27.411 - Convenio de Budapest sobre Ciberdelito",
        "tratado",
        "Ley 27.411. AprobaciÃ³n del Convenio sobre Ciberdelito del Consejo de Europa. Fuente oficial Infoleg.",
        "https://www.argentina.gob.ar/normativa/nacional/ley-27411-304798/texto",
        "Marco internacional de cooperaciÃ³n, armonizaciÃ³n penal, investigaciÃ³n, preservaciÃ³n y obtenciÃ³n de evidencia electrÃ³nica transfronteriza.",
    ),
    OfficialLegalSource(
        "Convenio de Budapest sobre Ciberdelincuencia",
        "tratado internacional",
        "Council of Europe. Convention on Cybercrime, ETS No. 185.",
        "https://www.coe.int/en/web/cybercrime/the-budapest-convention",
        "EstÃ¡ndar internacional para criminalizaciÃ³n de conductas, poderes procesales, preservaciÃ³n de datos, cooperaciÃ³n internacional y evidencia electrÃ³nica.",
    ),
    OfficialLegalSource(
        "Segundo Protocolo Adicional al Convenio de Budapest",
        "tratado internacional",
        "Council of Europe. Second Additional Protocol to the Cybercrime Convention, CETS No. 224.",
        "https://www.coe.int/en/web/cybercrime/second-additional-protocol",
        "CooperaciÃ³n reforzada y divulgaciÃ³n de evidencia electrÃ³nica, con foco en acceso transfronterizo, proveedores de servicios y garantÃ­as.",
    ),
    OfficialLegalSource(
        "Normativa argentina de ciberseguridad",
        "fuente oficial",
        "Argentina.gob.ar. DirecciÃ³n Nacional de Ciberseguridad - Normativa.",
        "https://www.argentina.gob.ar/jefatura/innovacion-publica/direccion-nacional-ciberseguridad/normativa",
        "Repositorio oficial de normativa, polÃ­ticas, estrategias y lineamientos argentinos vinculados a ciberseguridad.",
    ),
    OfficialLegalSource(
        "PolÃ­tica criminal argentina sobre ciberdelitos",
        "fuente oficial",
        "Argentina.gob.ar. SubsecretarÃ­a de PolÃ­tica Criminal - Ciberdelitos.",
        "https://www.argentina.gob.ar/node/200726",
        "Lineamientos institucionales sobre prevenciÃ³n, investigaciÃ³n, persecuciÃ³n penal de ciberdelitos, evidencia digital, cooperaciÃ³n internacional y adecuaciÃ³n normativa.",
    ),
]


PENAL_DOGMATIC_LEXICON = [
    "principio de legalidad",
    "tipicidad objetiva y subjetiva",
    "bien jurÃ­dico protegido",
    "antijuridicidad",
    "culpabilidad",
    "dolo directo, eventual o eventualidad cognoscitiva",
    "culpa, imprudencia o negligencia cuando corresponda",
    "imputaciÃ³n objetiva del resultado",
    "creaciÃ³n o incremento de un riesgo jurÃ­dicamente desaprobado",
    "realizaciÃ³n del riesgo en el resultado",
    "nexo causal y nexo de imputaciÃ³n",
    "autorÃ­a, coautorÃ­a, participaciÃ³n primaria o secundaria",
    "tentativa, consumaciÃ³n e iter criminis",
    "error de tipo o error de prohibiciÃ³n cuando resulte plausible",
    "principio de lesividad",
    "proporcionalidad y necesidad de medidas probatorias",
    "estÃ¡ndar de sospecha, probabilidad y suficiencia probatoria",
    "cadena de custodia, integridad, autenticidad y trazabilidad",
]

PROCEDURAL_CRIMINAL_LEXICON = [
    "denuncia penal y noticia criminis",
    "competencia material, territorial y federal u ordinaria",
    "intervenciÃ³n fiscal y direcciÃ³n de la investigaciÃ³n",
    "medidas urgentes de preservaciÃ³n de evidencia digital",
    "oficios a bancos, billeteras virtuales, exchanges, plataformas y proveedores",
    "requerimiento de registros de conexiÃ³n, IP, dispositivo, titularidad y movimientos",
    "secuestro, extracciÃ³n forense y peritaje informÃ¡tico cuando corresponda",
    "resguardo de cadena de custodia, autenticidad, integridad y trazabilidad",
    "control de legalidad, proporcionalidad, necesidad y resguardo de garantÃ­as",
    "valoraciÃ³n probatoria preliminar sin prejuzgamiento de autorÃ­a",
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
        return "No hay fuentes oficiales verificadas cargadas; toda referencia normativa debe marcarse como Fuente pendiente de verificaciÃ³n."
    lines = [
        f"- {normalize_spanish(item.title)}: {normalize_spanish(item.citation)} URL: {item.url}"
        for item in verified
    ]
    return "\n".join(lines)


def dogmatic_context() -> str:
    return "\n".join(f"- {item}" for item in PENAL_DOGMATIC_LEXICON)


def procedural_context() -> str:
    return "\n".join(f"- {item}" for item in PROCEDURAL_CRIMINAL_LEXICON)

