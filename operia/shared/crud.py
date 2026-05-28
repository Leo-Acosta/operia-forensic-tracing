from fastapi import HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session


def get_or_404(db: Session, model, item_id: int):
    item = db.get(model, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Recurso no encontrado")
    return item


def update_from_payload(item, payload: BaseModel):
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(item, key, value)
    return item

