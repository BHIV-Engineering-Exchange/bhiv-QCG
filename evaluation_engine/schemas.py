"""
evaluation_engine/schemas.py — Re-export from contracts/schemas.py for interface consistency
"""

from contracts.schemas import (
    EvaluationState,
    VerdictEnum,
    CriterionCategory,
    CriterionInput,
    TestSummary,
    ReviewSubmissionPayload,
    CriterionResult,
    EvaluationVerdictPayload,
    NiyantranTaskAssignmentPayload,
    VerificationRequest,
    VerificationResponse,
    ErrorEnvelope,
)

__all__ = [
    "EvaluationState",
    "VerdictEnum",
    "CriterionCategory",
    "CriterionInput",
    "TestSummary",
    "ReviewSubmissionPayload",
    "CriterionResult",
    "EvaluationVerdictPayload",
    "NiyantranTaskAssignmentPayload",
    "VerificationRequest",
    "VerificationResponse",
    "ErrorEnvelope",
]
