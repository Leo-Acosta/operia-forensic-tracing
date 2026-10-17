from sqlalchemy.orm import Session

from operia.cases.models import Case
from operia.legal_knowledge.service import recommend_articles_for_incident, search_articles


def excerpt(value, limit=600):
    text = str(value or "")
    return text[:limit] + (" [extracto]" if len(text) > limit else "")


def bounded_context(text, maximum):
    raw = text.encode("utf-8")
    if len(raw) <= maximum: return text
    return raw[:maximum - 64].decode("utf-8", errors="ignore") + "\n[Contexto limitado; revisar fuentes completas en el expediente]"


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
                    f"- {excerpt(article.code, 80)} art. {excerpt(article.article_number, 40)}{' inc. ' + excerpt(article.subsection, 40) if article.subsection else ''}: {excerpt(article.title, 200)}",
                    f"  Texto resumido: {excerpt(article.text)}",
                    f"  Elementos objetivos: {excerpt(article.objective_elements, 300)}",
                    f"  Elementos subjetivos: {excerpt(article.subjective_elements, 300)}",
                    f"  Evidencia requerida: {excerpt(article.evidentiary_requirements, 300)}",
                    f"  Fuente: {excerpt(article.official_url, 300)}",
                ]
            )
        )
    return bounded_context("\n".join(lines), 16 * 1024)


def case_context_for_prompt(case: Case | None, db: Session | None = None) -> str:
    if not case:
        return ""
    if db is not None:
        from sqlalchemy import func, or_
        from operia.evidence.models import Evidence
        from operia.cases.models import Finding
        evidence_rows = db.query(func.substr(Evidence.description, 1, 500)).filter(Evidence.case_id == case.id,
            or_(Evidence.organization_id == case.organization_id, Evidence.organization_id.is_(None))).order_by(Evidence.id).limit(8).all()
        finding_rows = db.query(func.substr(Finding.title, 1, 160), func.substr(Finding.technical_finding, 1, 600)).filter(Finding.case_id == case.id,
            or_(Finding.organization_id == case.organization_id, Finding.organization_id.is_(None))).order_by(Finding.id).limit(8).all()
        evidence = "; ".join(row[0] or "" for row in evidence_rows)
        findings = "; ".join(f"{row[0]}: {row[1]}" for row in finding_rows)
    else:
        evidence = "; ".join(excerpt(item.description, 500) for item in case.evidence[:8])
        findings = "; ".join(f"{excerpt(item.title, 160)}: {excerpt(item.technical_finding)}" for item in case.findings[:8])
    return bounded_context("\n".join(
        [
            f"Caso: {excerpt(case.case_code, 120)} - {excerpt(case.title, 200)}",
            f"Tipo: {excerpt(case.incident_type, 200)}",
            f"Descripcion: {excerpt(case.description, 2000)}",
            f"Observaciones: {excerpt(case.general_observations, 1000)}",
            f"Evidencia (hasta 8 extractos): {evidence or 'sin evidencia registrada'}",
            f"Hallazgos (hasta 8 extractos): {findings or 'sin hallazgos registrados'}",
        ]
    ), 8 * 1024)
