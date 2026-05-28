"""Compatibility schema exports for the legacy legal_report namespace.

Canonical schemas now live beside their owning modules.
"""

from operia.cases.schemas import (
    CaseCreate,
    CaseParticipantCreate,
    CaseParticipantRead,
    CaseRead,
    DamageItemCreate,
    DamageItemRead,
    FindingCreate,
    FindingRead,
    HypothesisCreate,
    HypothesisRead,
    TechnicalDataCreate,
    TechnicalDataRead,
)
from operia.evidence.schemas import CustodyActionCreate, CustodyActionRead, EvidenceCreate, EvidenceRead
from operia.legal_knowledge.schemas import LegalMappingCreate, LegalMappingRead, LegalSourceCreate, LegalSourceRead
from operia.reports.schemas import (
    CaseEvaluationResult,
    DashboardRead,
    PresentationRead,
    PresentationReviewResult,
    PresentationSlideRead,
    PresentationSlideUpdate,
    ReportRead,
    ReportUpdate,
    ReviewResult,
)
from operia.shared.schemas import ORMModel

__all__ = [
    "CaseCreate",
    "CaseParticipantCreate",
    "CaseParticipantRead",
    "CaseEvaluationResult",
    "CaseRead",
    "CustodyActionCreate",
    "CustodyActionRead",
    "DamageItemCreate",
    "DamageItemRead",
    "DashboardRead",
    "EvidenceCreate",
    "EvidenceRead",
    "FindingCreate",
    "FindingRead",
    "HypothesisCreate",
    "HypothesisRead",
    "LegalMappingCreate",
    "LegalMappingRead",
    "LegalSourceCreate",
    "LegalSourceRead",
    "ORMModel",
    "PresentationRead",
    "PresentationReviewResult",
    "PresentationSlideRead",
    "PresentationSlideUpdate",
    "ReportRead",
    "ReportUpdate",
    "ReviewResult",
    "TechnicalDataCreate",
    "TechnicalDataRead",
]
