"""contracts/schemas.py — Unified Interface Schemas (v1.0)

Standards:
- SETU OS Architecture v6.0 (Enterprise Core)
- Governed Operational System (Gov-OS) Core Compliance (PARIKSHAK Evaluation Runtime)
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator


# ============================================================================
# PARIKSHAK Review Runtime Interface Schemas (Gov-OS Compliance)
# ============================================================================

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


# ============================================================================
# BHIV Enterprise Common Core Schemas (SETU OS Architecture v6.0)
# ============================================================================

class TaskPriorityEnum(str, Enum):
    P0 = "P0"
    P1 = "P1"
    P2 = "P2"


class TaskStatusEnum(str, Enum):
    INITIATED = "INITIATED"
    VALIDATED = "VALIDATED"
    EXECUTED = "EXECUTED"
    EVALUATED = "EVALUATED"
    GOVERNED = "GOVERNED"
    ASSIGNED = "ASSIGNED"
    REJECTED = "REJECTED"


class IntegrationBlockStatus(BaseModel):
    model_config = ConfigDict(extra="forbid")

    bhiv_core: bool = Field(True, description="BHIV Enterprise Common Core active")
    gc_shakti: bool = Field(True, description="GC Shakti governance intelligence verified")
    niyantran: bool = Field(True, description="Niyantran task lifecycle engine active")
    bucket: bool = Field(True, description="Bucket immutable audit storage synced")
    gov_os: bool = Field(True, description="Gov-OS cryptographic ledger connected")
    saarthi: bool = Field(True, description="Saarthi operational visibility active")


class TaskDefinition(BaseModel):
    """Canonical task definition schema adhering to SETU OS Architecture v6.0."""
    model_config = ConfigDict(extra="forbid")

    task_id: str = Field(..., min_length=3, max_length=64, description="Unique task identifier")
    target_product: str = Field(..., min_length=2, max_length=128, description="Target product module name")
    assigned_candidate: str = Field(..., min_length=2, max_length=128, description="Assigned candidate or agent name")
    calibrated_duration_minutes: int = Field(..., ge=15, le=1440, description="Task duration in minutes")
    difficulty_level: str = Field("BEGINNER", description="Complexity level")
    priority: TaskPriorityEnum = Field(TaskPriorityEnum.P0, description="Priority classification")
    objective: str = Field(..., min_length=10, description="Comprehensive operational objective")
    integration_block: IntegrationBlockStatus = Field(default_factory=IntegrationBlockStatus)
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Deterministic task metadata")

    @field_validator("task_id")
    @classmethod
    def validate_task_id(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("task_id must not be empty or blank")
        return v


class StateTransitionEvent(BaseModel):
    """Immutable audit record of a state transition."""
    model_config = ConfigDict(extra="forbid")

    transition_id: str = Field(..., description="Unique transition UUID")
    task_id: str = Field(..., description="Associated Task ID")
    from_status: TaskStatusEnum = Field(..., description="Prior state")
    to_status: TaskStatusEnum = Field(..., description="Resulting state")
    trigger: str = Field(..., description="Event or operation that caused the transition")
    actor: str = Field(..., description="Candidate or agent triggering the state change")
    timestamp_utc: str = Field(..., description="ISO-8601 UTC timestamp")
    payload: Dict[str, Any] = Field(default_factory=dict, description="Contextual execution evidence")


class TaskExecutionRecord(BaseModel):
    """Complete runtime state model for a governed task."""
    model_config = ConfigDict(extra="forbid")

    task_id: str = Field(...)
    execution_id: str = Field(...)
    status: TaskStatusEnum = Field(TaskStatusEnum.INITIATED)
    trace_id: str = Field(...)
    start_time_utc: str = Field(...)
    end_time_utc: Optional[str] = Field(None)
    transitions: List[StateTransitionEvent] = Field(default_factory=list)
    state_hash: str = Field("", description="Deterministic SHA-256 state hash")
    execution_metrics: Dict[str, Any] = Field(default_factory=dict)


class EvidencePacket(BaseModel):
    """Standard Evidence Exchange Schema v1.0 compatible with Bucket & Gov-OS."""
    model_config = ConfigDict(extra="forbid")

    artifact_id: str = Field(..., description="Globally unique artifact UUID")
    trace_id: str = Field(..., description="Ecosystem trace UUID")
    timestamp_utc: str = Field(..., description="ISO-8601 UTC timestamp")
    schema_version: str = Field("1.0.0", description="Strict schema version v1.0.0")
    source_module_id: str = Field("BHIV_ENTERPRISE_CORE", description="Publishing module identifier")
    artifact_type: str = Field("GOVERNED_REVIEW_PACKET", description="Category of evidence")
    parent_hash: str = Field(..., description="Continuity parent SHA-256 hash")
    payload: Dict[str, Any] = Field(..., description="Cryptographic payload")
    signature: str = Field(..., description="ECDSA / HMAC cryptographic attestation")


class NiyantranAssignmentPayload(BaseModel):
    """Zero-context-switch canonical task assignment payload for Niyantran."""
    model_config = ConfigDict(extra="forbid")

    assignment_id: str = Field(...)
    parent_task_id: str = Field(...)
    next_task_id: str = Field(...)
    assigned_candidate: str = Field(...)
    target_product: str = Field(...)
    calibrated_duration_minutes: int = Field(...)
    priority: TaskPriorityEnum = Field(TaskPriorityEnum.P0)
    canonical_specification: str = Field(..., min_length=20)
    dispatch_timestamp_utc: str = Field(...)
    gov_os_ledger_ref: str = Field(...)
    bucket_evidence_ref: str = Field(...)


class ReviewPacketPayload(BaseModel):
    """Review Packet data model for Parikshak evaluation."""
    model_config = ConfigDict(extra="forbid")

    review_id: str = Field(...)
    task_id: str = Field(...)
    evaluated_task_ref: str = Field(...)
    candidate_name: str = Field(...)
    score: int = Field(..., ge=0, le=100)
    verdict: str = Field(..., description="PASS or FAIL")
    architectural_standard: str = Field("SETU OS Architecture v6.0")
    test_pass_rate_percent: float = Field(..., ge=0.0, le=100.0)
    determinism_runs: int = Field(50, description="Number of consecutive determinism test runs")
    deterministic_state_hash: str = Field(..., min_length=64, max_length=64)
    next_task: NiyantranAssignmentPayload = Field(...)


class ValidationErrorResponse(BaseModel):
    """Fail-closed error response for 400/422 validation errors."""
    model_config = ConfigDict(extra="forbid")

    error_code: str = Field("VALIDATION_ERROR")
    message: str = Field(...)
    invalid_fields: List[str] = Field(default_factory=list)
    timestamp_utc: str = Field(...)


class ExecutionErrorResponse(BaseModel):
    """Clean error response for runtime boundary errors (preventing unhandled 500s)."""
    model_config = ConfigDict(extra="forbid")

    error_code: str = Field(...)
    message: str = Field(...)
    trace_id: str = Field(...)
    timestamp_utc: str = Field(...)


# ============================================================================
# Additional PARIKSHAK Rule Engine Schemas (Gov-OS)
# ============================================================================

class EvaluationRuleCategory(str, Enum):
    SCHEMA_COMPLIANCE = "SCHEMA_COMPLIANCE"
    TEST_PASS_RATE = "TEST_PASS_RATE"
    DETERMINISM_PROOF = "DETERMINISM_PROOF"
    ERROR_BOUNDARY_COVERAGE = "ERROR_BOUNDARY_COVERAGE"
    DEPENDENCY_PINNING = "DEPENDENCY_PINNING"


class EvaluationRuleItem(BaseModel):
    """Individual rule definition for evaluation."""
    model_config = ConfigDict(extra="forbid")

    rule_id: str = Field(..., description="Unique rule identifier")
    rule_name: str = Field(..., description="Descriptive rule name")
    category: EvaluationRuleCategory = Field(..., description="Governance rule category")
    weight: float = Field(..., ge=0.0, le=1.0, description="Normalized scoring weight")
    min_score_required: float = Field(0.0, ge=0.0, le=100.0, description="Minimum acceptable threshold")


class EvaluationCriteriaCheck(BaseModel):
    """Evaluation result for an individual criteria check."""
    model_config = ConfigDict(extra="forbid")

    criterion_id: str = Field(...)
    rule_id: str = Field(...)
    category: EvaluationRuleCategory = Field(...)
    passed: bool = Field(...)
    observed_value: Any = Field(...)
    score: float = Field(..., ge=0.0, le=100.0)
    message: str = Field(...)


class EvaluationRequest(BaseModel):
    """Evaluation request payload for PARIKSHAK Evaluation Engine."""
    model_config = ConfigDict(extra="forbid")

    evaluation_id: str = Field(..., description="Unique evaluation request ID")
    task_id: str = Field(..., description="Target task ID")
    candidate_name: str = Field(..., description="Assigned candidate or engineer")
    repository_target: str = Field(..., description="Target repository or module name")
    submission_evidence: Dict[str, Any] = Field(..., description="Verified runtime evidence payload")
    rules: Optional[List[EvaluationRuleItem]] = Field(None, description="Optional custom rule list")


class EvaluationVerdict(BaseModel):
    """Official cryptographic evaluation verdict issued by Parikshak."""
    model_config = ConfigDict(extra="forbid")

    verdict_id: str = Field(..., description="Unique verdict identifier")
    task_id: str = Field(..., description="Target task ID")
    candidate_name: str = Field(..., description="Assigned candidate name")
    total_score: float = Field(..., ge=0.0, le=100.0, description="Composite weighted evaluation score")
    verdict: str = Field(..., description="PASS or FAIL")
    compliance_standard: str = Field("Gov-OS Core Compliance", description="Applied standard")
    criteria_results: List[EvaluationCriteriaCheck] = Field(..., description="Granular rule results")
    deterministic_verdict_hash: str = Field(..., min_length=64, max_length=64, description="Canonical SHA-256 state hash")
    timestamp_utc: str = Field(...)
    next_task_recommendation: Optional[str] = Field(None)
