from datetime import datetime
from typing import Any

from pydantic import BaseModel

from operia.shared.schemas import ORMModel


class RubricSection(BaseModel):
    key: str
    label: str
    weight: int
    criteria: list[str]
    expected_components: list[str]
    minimum_fields: list[str]
    status: str = "incompleto"
    estimated_score: int = 0
    max_score: int = 0
    completion_ratio: float = 0
    missing: list[str] = []
    recommendations: list[str] = []
    evidence: dict[str, Any] = {}


class RubricDefinition(BaseModel):
    key: str
    title: str
    max_score: int
    sections: list[RubricSection]


class RubricEvaluationRead(ORMModel):
    id: int
    case_id: int
    rubric_key: str
    rubric_title: str
    total_score: int
    max_score: int
    percentage: int
    status: str
    sections: list[RubricSection]
    missing: list[str]
    recommendations: list[str]
    summary: str
    evaluated_by: str
    created_at: datetime
    updated_at: datetime

