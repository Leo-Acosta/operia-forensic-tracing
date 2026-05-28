"""Compatibility exports for the legacy legal_report import path.

The canonical model ownership now lives in the platform modules:
identity, cases, evidence, reports, legal_knowledge, and audit.
"""

from operia.audit.models import AuditLog
from operia.cases.models import Case, CaseParticipant, DamageCalculation, DamageItem, Finding, Hypothesis, TechnicalData
from operia.evidence.models import Attachment, ChainOfCustodyAction, Evidence
from operia.identity.models import Membership, Organization, Role, User
from operia.legal_knowledge.models import LegalArticle, LegalCitation, LegalEvaluation, LegalMapping, LegalSource
from operia.reports.models import (
    Presentation,
    PresentationFragment,
    PresentationReview,
    PresentationSlide,
    PresentationVersion,
    Report,
    ReportReview,
    ReportSection,
    ReportVersion,
    Template,
)
