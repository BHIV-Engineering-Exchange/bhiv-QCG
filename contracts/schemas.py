"""v1.0 Interface Schemas for BHIV Enterprise Operating System Common Core.

Standard: SETU OS Architecture v6.0
Integration Block: BHIV Core, GC Shakti, Niyantran, Bucket, Gov-OS, Saarthi
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator


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
    payload: Dict[str, Any] = Field(..., description="Cryptographic payload payload")
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
