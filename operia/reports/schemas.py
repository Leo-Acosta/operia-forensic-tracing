from datetime import datetime
from typing import Any

from pydantic import BaseModel

from operia.cases.schemas import CaseRead
from operia.evidence.schemas import CustodyActionRead
from operia.shared.schemas import ORMModel


class ReportRead(ORMModel):
    id: int
    case_id: int
    title: str
    version: str
    author: str
    status: str
    template_used: str
    observations: str
    markdown_content: str
    review_score: int
    created_at: datetime
    updated_at: datetime


class ReportUpdate(BaseModel):
    title: str | None = None
    markdown_content: str | None = None
    status: str | None = None
    observations: str | None = None
    author: str | None = None


class ExecutiveSummaryUpdate(BaseModel):
    executive_summary: str
    author: str | None = None


class ReviewResult(BaseModel):
    score: int
    status: str
    critical_errors: list[str]
    warnings: list[str]
    suggestions: list[str]
    incomplete_sections: list[str]
    unused_evidence: list[str] = []
    unsupported_conclusions: list[str] = []
    drafting_recommendations: list[str] = []


class CaseEvaluationResult(BaseModel):
    overall_score: int
    status: str
    evidence_score: int
    finding_score: int
    hypothesis_score: int
    legal_score: int
    economic_score: int
    custody_score: int
    report_score: int
    case_theory: str
    legal_justification: str
    dogmatic_assessment: str
    procedural_assessment: str
    evidentiary_assessment: str
    economic_assessment: str
    strengths: list[str]
    weaknesses: list[str]
    next_steps: list[str]
    defensible_conclusion: str
    legal_classification: list[str]
    competence: list[str]


class PresentationRead(ORMModel):
    id: int
    case_id: int
    source_report_id: int | None
    title: str
    presentation_type: str
    version: str
    status: str
    author: str
    selected_fragments: str
    review_score: int
    exported_file: str
    created_at: datetime
    updated_at: datetime


class PresentationSlideRead(ORMModel):
    id: int
    presentation_id: int
    slide_number: int
    title: str
    content_type: str
    text: str
    speaker_notes: str
    confidentiality_level: str


class PresentationSlideUpdate(BaseModel):
    slide_number: int | None = None
    title: str | None = None
    content_type: str | None = None
    text: str | None = None
    speaker_notes: str | None = None
    confidentiality_level: str | None = None


class PresentationReviewResult(BaseModel):
    score: int
    status: str = ""
    clarity: int
    evidentiary_strength: int
    narrative_coherence: int
    legal_solidity: int
    visual_quality: int
    critical_errors: list[str] = []
    warnings: list[str] = []
    oral_exposure_risks: list[str]
    recommendations: list[str]
    page_recommendations: list[str] = []


class DashboardRead(BaseModel):
    metrics: dict[str, Any]
    recent_cases: list[CaseRead]
    recent_actions: list[CustodyActionRead]
