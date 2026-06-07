import json

from sqlalchemy.orm import Session

from operia.core.database import SessionLocal
from operia.mind.agents import BASE_AGENTS
from operia.mind.models import MindAgent, MindPrompt
from operia.mind.prompts import BASE_PROMPTS
from operia.mind.vault import ensure_vault, write_support_file


def init_mind_module() -> None:
    ensure_vault()
    db = SessionLocal()
    try:
        seed_prompts(db)
        seed_agents(db)
        db.commit()
    finally:
        db.close()


def seed_prompts(db: Session) -> None:
    for item in BASE_PROMPTS:
        existing = db.query(MindPrompt).filter(MindPrompt.key == item["key"]).first()
        relative_path = f"09_Prompts/{item['key']}.md"
        write_support_file(
            relative_path,
            f"# {item['title']}\n\n## Propósito\n\n{item['purpose']}\n\n## Prompt\n\n{item['prompt_text']}\n",
        )
        if existing:
            existing.title = item["title"]
            existing.purpose = item["purpose"]
            existing.prompt_text = item["prompt_text"]
            existing.output_format = item["output_format"]
            existing.vault_path = relative_path
            continue
        db.add(
            MindPrompt(
                key=item["key"],
                title=item["title"],
                purpose=item["purpose"],
                prompt_text=item["prompt_text"],
                output_format=item["output_format"],
                requires_review=True,
                vault_path=relative_path,
            )
        )


def seed_agents(db: Session) -> None:
    for item in BASE_AGENTS:
        existing = db.query(MindAgent).filter(MindAgent.key == item["key"]).first()
        relative_path = f"10_Agentes/{item['key']}.md"
        allowed = json.dumps(item["allowed_modules"], ensure_ascii=False)
        write_support_file(
            relative_path,
            (
                f"# {item['name']}\n\n"
                f"- Rol: {item['role']}\n"
                f"- Alcance: {item['scope']}\n"
                f"- Módulos permitidos: {', '.join(item['allowed_modules'])}\n"
                f"- Restricciones: {item['restrictions']}\n"
                f"- Prompt base: {item['base_prompt_key']}\n"
                f"- Riesgo: {item['risk_level']}\n"
            ),
        )
        if existing:
            existing.name = item["name"]
            existing.role = item["role"]
            existing.scope = item["scope"]
            existing.allowed_modules = allowed
            existing.restrictions = item["restrictions"]
            existing.base_prompt_key = item["base_prompt_key"]
            existing.risk_level = item["risk_level"]
            existing.vault_path = relative_path
            continue
        db.add(
            MindAgent(
                key=item["key"],
                name=item["name"],
                role=item["role"],
                scope=item["scope"],
                allowed_modules=allowed,
                restrictions=item["restrictions"],
                base_prompt_key=item["base_prompt_key"],
                output_format="markdown",
                risk_level=item["risk_level"],
                requires_human_review=True,
                vault_path=relative_path,
            )
        )
