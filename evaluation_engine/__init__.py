"""
evaluation_engine/__init__.py — Parikshak Evaluation Engine Subsystem
"""

from .rule_engine import EvaluationEngine
from .schemas import (
    ReviewSubmissionPayload,
    EvaluationVerdictPayload,
    NiyantranTaskAssignmentPayload,
    VerificationRequest,
    VerificationResponse,
    ErrorEnvelope,
    CriterionInput,
    CriterionResult,
    VerdictEnum,
    EvaluationState,
)

__all__ = [
    "EvaluationEngine",
    "ReviewSubmissionPayload",
    "EvaluationVerdictPayload",
    "NiyantranTaskAssignmentPayload",
    "VerificationRequest",
    "VerificationResponse",
    "ErrorEnvelope",
    "CriterionInput",
    "CriterionResult",
    "VerdictEnum",
    "EvaluationState",
]
