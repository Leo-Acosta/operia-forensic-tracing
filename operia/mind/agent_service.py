from sqlalchemy import or_
from sqlalchemy.orm import Session

from operia.identity.dependencies import CurrentUser
from operia.mind.models import MindAgent


class AgentService:
    def __init__(self, db: Session, current_user: CurrentUser):
        self.db = db
        self.current_user = current_user

    def list_agents(self) -> list[MindAgent]:
        query = self.db.query(MindAgent)
        if self.current_user.organization_id:
            query = query.filter(
                or_(
                    MindAgent.organization_id == self.current_user.organization_id,
                    MindAgent.organization_id.is_(None),
                )
            )
        return query.order_by(MindAgent.name).all()
