from operia.core.database import SessionLocal
from operia.legal_knowledge.service import ensure_legal_articles


def init_legal_knowledge_module() -> None:
    db = SessionLocal()
    try:
        ensure_legal_articles(db)
        db.commit()
    finally:
        db.close()

