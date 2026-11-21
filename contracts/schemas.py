"""
contracts/schemas.py — Parikshak Engineering Review Runtime Interface Schemas (v1.0)
Standard: Governed Operational System (Gov-OS) Core Compliance
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, ConfigDict
from enum import Enum
from datetime import datetime


class EvaluationState(str, Enum):
    INITIALIZED = "INITIALIZED"
    INPUT_VALIDATED = "INPUT_VALIDATED"
    GOV_OS_AUDIT = "GOV_OS_AUDIT"
    RULES_APPLIED = "RULES_APPLIED"
    HASH_COMPUTED = "HASH_COMPUTED"
    VERIFIED = "VERIFIED"
    COMPLETED = "COMPLETED"
    REJECTED = "REJECTED"


class VerdictEnum(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    CONDITIONAL = "CONDITIONAL"


class CriterionCategory(str, Enum):
    ARCHITECTURAL_MODULARITY = "Architectural Modularity"
    GOV_OS_COMPLIANCE = "Gov-OS Compliance & Security"
    TEST_VERIFICATION_MATRIX = "Test & Verification Matrix"
    RUNTIME_EVIDENCE_GROUNDING = "Runtime Evidence Grounding"


class CriterionInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., description="Criterion identifier or name", min_length=2)
    category: CriterionCategory = Field(..., description="Evaluation category")
    weight: float = Field(..., ge=0.0, le=100.0, description="Weight percentage (0-100)")
    score: float = Field(..., ge=0.0, le=100.0, description="Raw score achieved (0-100)")
    pass_threshold: float = Field(default=70.0, ge=0.0, le=100.0, description="Minimum score required to pass")
    details: Optional[str] = Field(default="", description="Detailed reviewer observation")
    artifacts: Optional[List[str]] = Field(default_factory=list, description="Referenced artifact file paths")


class AutomatedTestSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    total_tests: int = Field(..., ge=0)
    passed_tests: int = Field(..., ge=0)
    failed_tests: int = Field(default=0, ge=0)
    skipped_tests: int = Field(default=0, ge=0)
    pass_rate: float = Field(..., ge=0.0, le=100.0)


# Backward-compatible alias
TestSummary = AutomatedTestSummary


class ReviewSubmissionPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    task_id: str = Field(..., min_length=3, description="Canonical task identifier (e.g. T-GOV-002)")
    candidate_id: str = Field(..., min_length=2, description="Candidate unique identifier")
    candidate_name: str = Field(..., min_length=2, description="Full candidate name")
    target_product: str = Field(default="Parikshak Engineering Review Runtime", min_length=2)
    submission_timestamp: str = Field(..., description="ISO 8601 submission timestamp")
    review_packet_path: Optional[str] = Field(default="review_packets/REVIEW_PACKET.md")
    criteria: List[CriterionInput] = Field(..., min_length=1, description="Evaluation criteria matrix")
    test_summary: TestSummary = Field(..., description="Summary of automated test results")
    code_packets: Optional[List[Dict[str, Any]]] = Field(default_factory=list, description="Code packet components")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Metadata tags and governance context")


class CriterionResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    criterion_name: str
    category: str
    raw_score: float
    weight: float
    weighted_score: float
    passed: bool
    notes: str


class EvaluationVerdictPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = Field(default="1.0", description="Schema version identifier")
    evaluation_id: str = Field(..., description="Unique deterministic evaluation identifier")
    task_id: str = Field(..., description="Canonical task ID")
    candidate_id: str = Field(..., description="Candidate ID")
    candidate_name: str = Field(..., description="Candidate Name")
    verdict: VerdictEnum = Field(..., description="PASS or FAIL evaluation verdict")
    total_score: float = Field(..., ge=0.0, le=100.0, description="Normalized composite score (0-100)")
    score_breakdown: Dict[str, float] = Field(..., description="Score contributions by category")
    criteria_results: List[CriterionResult] = Field(..., description="Detailed criterion evaluation results")
    test_summary: AutomatedTestSummary = Field(..., description="Automated test metrics summary")
    state_machine_history: List[Dict[str, str]] = Field(..., description="Deterministic state transition trail")
    deterministic_state_hash: str = Field(..., min_length=64, max_length=64, description="SHA-256 state hash digest")
    governance_compliance: Dict[str, Any] = Field(..., description="Gov-OS core compliance audit verification")
    timestamp: str = Field(..., description="Evaluation completion timestamp")
    audit_ref: str = Field(..., description="Immutable audit record reference")


class NiyantranTaskAssignmentPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    assignment_id: str = Field(..., description="Unique assignment token")
    assigned_task_id: str = Field(..., description="Canonical next task identifier")
    target_product: str = Field(..., description="Target product runtime")
    candidate_id: str = Field(..., description="Assigned candidate ID")
    candidate_name: str = Field(..., description="Assigned candidate name")
    task_title: str = Field(..., description="Canonical task title")
    calibrated_duration: str = Field(..., description="Calibrated execution duration SLA")
    difficulty_level: str = Field(..., description="Calibrated task difficulty")
    phase_specifications: List[Dict[str, Any]] = Field(..., description="Multi-phase execution specifications")
    dod_matrix: List[Dict[str, str]] = Field(..., description="Definition of done verification matrix")
    governance_authority: str = Field(default="GC Shakti / Niyantran Task Orchestration")
    zero_context_switch_ready: bool = Field(default=True)
    assignment_timestamp: str = Field(..., description="Assignment issuance timestamp")


class VerificationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    verdict_payload: EvaluationVerdictPayload
    expected_state_hash: Optional[str] = None


class VerificationResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    verified: bool
    evaluation_id: str
    computed_hash: str
    expected_hash: str
    deterministic_match: bool
    gov_os_compliant: bool
    verification_timestamp: str
    audit_notes: List[str]


class ErrorEnvelope(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: str = "error"
    status_code: int
    error_type: str
    message: str
    details: Optional[List[Dict[str, Any]]] = None
    request_id: str
    timestamp: str
