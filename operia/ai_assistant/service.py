from sqlalchemy.orm import Session

from operia.cases.models import Case
from operia.legal_knowledge.service import recommend_articles_for_incident, search_articles


def legal_context_for_prompt(db: Session, query: str) -> str:
    recommended = recommend_articles_for_incident(db, query, limit=6)
    article_ids = [item["article_id"] for item in recommended]
    articles = []
    if article_ids:
        from operia.legal_knowledge.models import LegalArticle

        articles = db.query(LegalArticle).filter(LegalArticle.id.in_(article_ids)).all()
    if not articles:
        articles = search_articles(db, query, limit=6)
    lines = []
    for article in articles:
        lines.append(
            "\n".join(
                [
                    f"- {article.code} art. {article.article_number}{' inc. ' + article.subsection if article.subsection else ''}: {article.title}",
                    f"  Texto resumido: {article.text}",
                    f"  Elementos objetivos: {article.objective_elements}",
                    f"  Elementos subjetivos: {article.subjective_elements}",
                    f"  Evidencia requerida: {article.evidentiary_requirements}",
                    f"  Fuente: {article.official_url}",
                ]
            )
        )
    return "\n".join(lines)


def case_context_for_prompt(case: Case | None) -> str:
    if not case:
        return ""
    evidence = "; ".join(item.description for item in case.evidence[:8])
    findings = "; ".join(f"{item.title}: {item.technical_finding}" for item in case.findings[:8])
    return "\n".join(
        [
            f"Caso: {case.case_code} - {case.title}",
            f"Tipo: {case.incident_type}",
            f"Descripcion: {case.description}",
            f"Observaciones: {case.general_observations}",
            f"Evidencia: {evidence or 'sin evidencia registrada'}",
            f"Hallazgos: {findings or 'sin hallazgos registrados'}",
        ]
    )
