from operia.core.database import Base, SessionLocal, engine
from operia.legal_report.models import LegalSource, Template
from operia.legal_report.services.legal_knowledge_base import sync_official_sources


def init_legal_report_module() -> None:
    Base.metadata.create_all(bind=engine)

    template_names = [
        "Informe integral forense-juridico",
        "Informe tecnico preliminar",
        "Informe para denuncia penal",
        "Informe para reclamo civil",
        "Informe para defensa del consumidor",
        "Informe de dano economico",
        "Informe de evidencia digital",
        "Informe academico para competencia",
        "Informe de testimonio experto",
    ]
    legal_sources = [
        (
            "Codigo Penal argentino",
            "norma",
            "Fuente pendiente de verificacion",
            "Base penal comun y delitos incorporados por reformas sobre criminalidad informatica.",
        ),
        (
            "Ley 26.388 de delitos informaticos",
            "norma",
            "Fuente pendiente de verificacion",
            "Modificaciones al Codigo Penal argentino relacionadas con conductas informaticas.",
        ),
        (
            "Ley 25.326 de Proteccion de Datos Personales",
            "norma",
            "Fuente pendiente de verificacion",
            "Marco argentino de proteccion de datos personales y habeas data.",
        ),
        (
            "Ley 24.240 de Defensa del Consumidor",
            "norma",
            "Fuente pendiente de verificacion",
            "Relaciones de consumo, deber de informacion, seguridad y trato digno.",
        ),
        (
            "Codigo Civil y Comercial de la Nacion",
            "norma",
            "Fuente pendiente de verificacion",
            "Responsabilidad civil, dano, nexo causal y reparacion.",
        ),
        (
            "Ley 27.411 - Convenio de Budapest sobre Ciberdelito",
            "norma",
            "Fuente pendiente de verificacion",
            "Cooperacion y marco internacional en ciberdelito.",
        ),
        (
            "Protocolos argentinos de evidencia digital y cadena de custodia",
            "protocolo",
            "Fuente pendiente de verificacion",
            "Buenas practicas de preservacion, trazabilidad e integridad probatoria.",
        ),
    ]

    db = SessionLocal()
    try:
        for name in template_names:
            if not db.query(Template).filter_by(name=name).first():
                db.add(Template(name=name, content=f"Plantilla editable: {name}"))
        for title, source_type, citation, content in legal_sources:
            if not db.query(LegalSource).filter_by(title=title).first():
                db.add(
                    LegalSource(
                        title=title,
                        source_type=source_type,
                        citation=citation,
                        content=content,
                        verified=False,
                    )
                )
        sync_official_sources(db)
        db.commit()
    finally:
        db.close()

