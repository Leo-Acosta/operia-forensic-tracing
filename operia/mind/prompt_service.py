from sqlalchemy import or_
from sqlalchemy.orm import Session

from operia.identity.dependencies import CurrentUser
from operia.mind.models import MindPrompt


class PromptService:
    def __init__(self, db: Session, current_user: CurrentUser):
        self.db = db
        self.current_user = current_user

    def list_prompts(self) -> list[MindPrompt]:
        query = self.db.query(MindPrompt)
        if self.current_user.organization_id:
            query = query.filter(
                or_(
                    MindPrompt.organization_id == self.current_user.organization_id,
                    MindPrompt.organization_id.is_(None),
                )
            )
        return query.order_by(MindPrompt.title).all()
