"""
constitutional_runtime_contract.py — Constitutional Runtime Participant Contract

Codifies the Universal Solver Fabric's permanent constitutional position within
the BHIV Living Organism.  Every authority boundary, runtime contract, API contract,
event contract, and guarantee is defined here as executable, testable code.

RESPONSIBILITY BOUNDARY
-----------------------
This module OWNS:
    - Authority Matrix declaration
    - Runtime Contract lifecycle (register/discover/execute/deregister)
    - API Contract definitions
    - Event Contract definitions
    - Attachment Contract definitions
    - Version Negotiation rules
    - Consumer/Producer Compatibility validation
    - Failure Behaviour specifications
    - Deterministic Runtime Guarantees
    - Replay Guarantees
    - Evidence Guarantees

This module does NOT OWN:
    - Solver algorithm execution         → solver_interfaces/
    - Platform service registration      → PlatformServiceRegistry
    - Replay detection                   → CanonicalReplayAuthority
    - Governance policy                  → GovernanceLayer
    - Certificate authority              → ServiceCertificateAuthority
"""

from __future__ import annotations

import hashlib
import json
import re
import time
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

FABRIC_VERSION = "1.0.0"
SCHEMA_VERSION = "1.0.0"
API_VERSION = "v1"
RUNTIME_ID = "TANTRA-PSR-USF-001"
CAPABILITY_ID = "bhiv.capabilities.solver_fabric"
PERMANENT_IDENTITY = "Optimization.SolverFabric.v1"
CONSTITUTIONAL_LAYER = "Platform Service Layer / Agnostic Execution Layer"


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class VersionCompatibility(Enum):
    COMPATIBLE = "COMPATIBLE"
    DEPRECATED = "DEPRECATED"
    UNSUPPORTED = "UNSUPPORTED"


class AttachmentMode(Enum):
    LOCAL = "LOCAL"
    REMOTE = "REMOTE"
    HYBRID = "HYBRID"


class LifecycleState(Enum):
    REGISTERED = "REGISTERED"
    DISCOVERED = "DISCOVERED"
    EXECUTING = "EXECUTING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    DISABLED = "DISABLED"
    DEREGISTERED = "DEREGISTERED"


class FailureCode(Enum):
    VALIDATION_ERROR = "HALT:VALIDATION_ERROR"
    CAPABILITY_MISMATCH = "HALT:CAPABILITY_MISMATCH"
    RESOURCE_EXHAUSTED = "HALT:RESOURCE_EXHAUSTED"
    ENGINE_CRASH = "HALT:ENGINE_CRASH"
    TIMEOUT = "HALT:TIMEOUT"
    UNAUTHORIZED = "HALT:UNAUTHORIZED"
    CONTRACT_VIOLATION = "HALT:CONTRACT_VIOLATION"
    REPLAY_DETECTED = "HALT:REPLAY_DETECTED"


class EventType(Enum):
    SOLVER_REGISTERED = "solver_fabric.solver_registered"
    SOLVER_DISABLED = "solver_fabric.solver_disabled"
    SOLVER_ENABLED = "solver_fabric.solver_enabled"
    EXECUTION_STARTED = "solver_fabric.execution_started"
    EXECUTION_COMPLETED = "solver_fabric.execution_completed"
    EXECUTION_FAILED = "solver_fabric.execution_failed"
    REGISTRATION_COMPLETED = "solver_fabric.registration_completed"
    HEALTH_CHECK = "solver_fabric.health_check"


# ---------------------------------------------------------------------------
# Authority Matrix
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class AuthorityMatrix:
    """
    Defines what the Universal Solver Fabric owns, delegates, and explicitly
    does NOT own.  This is the constitutional boundary declaration.
    """

    owns: Tuple[str, ...] = (
        "Solver Capability Contract enforcement",
        "Deterministic Solver Selection",
        "Execution Adapter lifecycle",
        "Solver health tracking",
        "Evidence package generation",
        "Attachment mode negotiation",
        "Solver Registry management",
    )

    does_not_own: Tuple[str, ...] = (
        "Problem formulation / modeling",
        "Business logic execution",
        "Orchestration of external workflows",
        "Master Directive definitions",
        "Budget / cost approval",
        "Data storage / persistence",
        "Replay detection (primary)",
        "Governance policy enforcement",
        "Service registration",
        "Certificate authority",
        "Federation protocol",
    )

    delegates_to: Dict[str, str] = field(default_factory=lambda: {
        "PlatformServiceRegistry": "Service registration and lifecycle",
        "CanonicalReplayAuthority": "Replay detection and enforcement",
        "GovernanceLayer": "Pre-execution governance policy",
        "HeartbeatManager": "Lease-based liveness protocol",
        "TraceStore": "Observability trace storage",
    })

    def validate_authority(self, action: str) -> bool:
        """Check if an action falls within owned authority."""
        return any(action.lower() in owned.lower() for owned in self.owns)

    def is_explicitly_forbidden(self, action: str) -> bool:
        """Check if an action is explicitly outside authority."""
        return any(action.lower() in forbidden.lower() for forbidden in self.does_not_own)


AUTHORITY_MATRIX = AuthorityMatrix()


# ---------------------------------------------------------------------------
# Version Negotiation
# ---------------------------------------------------------------------------

def parse_semver(version_str: str) -> Tuple[int, int, int]:
    """Parse a semantic version string into (major, minor, patch)."""
    match = re.match(r'^(\d+)\.(\d+)\.(\d+)', version_str)
    if not match:
        raise ValueError(f"Invalid semantic version: {version_str}")
    return int(match.group(1)), int(match.group(2)), int(match.group(3))


def negotiate_version(
    requested_version: str,
    supported_versions: List[str] = None,
) -> Tuple[VersionCompatibility, str]:
    """
    Negotiate version compatibility for the Solver Fabric.

    Rules:
        - Same major version, same or higher minor → COMPATIBLE
        - Same major, lower minor → DEPRECATED (backward compatible)
        - Different major → UNSUPPORTED
    """
    if supported_versions is None:
        supported_versions = [FABRIC_VERSION]

    try:
        req_major, req_minor, req_patch = parse_semver(requested_version)
    except ValueError:
        return VersionCompatibility.UNSUPPORTED, FABRIC_VERSION

    best_match = None
    best_status = VersionCompatibility.UNSUPPORTED

    for sv in supported_versions:
        try:
            sv_major, sv_minor, sv_patch = parse_semver(sv)
        except ValueError:
            continue

        if sv_major != req_major:
            continue

        if sv_minor >= req_minor:
            if best_match is None or sv < best_match:
                best_match = sv
                best_status = VersionCompatibility.COMPATIBLE
        elif sv_minor < req_minor:
            if best_status != VersionCompatibility.COMPATIBLE:
                best_match = sv
                best_status = VersionCompatibility.DEPRECATED

    if best_match is None:
        return VersionCompatibility.UNSUPPORTED, FABRIC_VERSION

    return best_status, best_match


# ---------------------------------------------------------------------------
# Runtime Contract
# ---------------------------------------------------------------------------

@dataclass
class RuntimeContract:
    """
    Defines the runtime lifecycle contract for the Solver Fabric.
    """
    runtime_id: str = RUNTIME_ID
    capability_id: str = CAPABILITY_ID
    permanent_identity: str = PERMANENT_IDENTITY
    constitutional_layer: str = CONSTITUTIONAL_LAYER
    fabric_version: str = FABRIC_VERSION
    schema_version: str = SCHEMA_VERSION
    api_version: str = API_VERSION

    valid_states: Tuple[str, ...] = field(default_factory=lambda: tuple(s.value for s in LifecycleState))

    valid_transitions: Dict[str, List[str]] = field(default_factory=lambda: {
        "REGISTERED": ["DISCOVERED", "DISABLED", "DEREGISTERED"],
        "DISCOVERED": ["EXECUTING", "DISABLED"],
        "EXECUTING": ["COMPLETED", "FAILED"],
        "COMPLETED": ["DISCOVERED", "DISABLED"],
        "FAILED": ["DISCOVERED", "DISABLED"],
        "DISABLED": ["REGISTERED"],
        "DEREGISTERED": [],
    })

    def validate_transition(self, from_state: str, to_state: str) -> bool:
        """Check if a state transition is valid."""
        allowed = self.valid_transitions.get(from_state, [])
        return to_state in allowed

    def to_dict(self) -> Dict[str, Any]:
        return {
            "runtime_id": self.runtime_id,
            "capability_id": self.capability_id,
            "permanent_identity": self.permanent_identity,
            "constitutional_layer": self.constitutional_layer,
            "fabric_version": self.fabric_version,
            "schema_version": self.schema_version,
            "api_version": self.api_version,
            "valid_states": list(self.valid_states),
            "valid_transitions": self.valid_transitions,
        }


# ---------------------------------------------------------------------------
# API Contract
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class APIEndpoint:
    """Definition of a single API endpoint."""
    path: str
    method: str
    description: str
    input_contract: Dict[str, Any] = field(default_factory=dict)
    output_contract: Dict[str, Any] = field(default_factory=dict)
    error_codes: Tuple[str, ...] = ()


@dataclass
class APIContract:
    """
    Complete API contract for the Solver Fabric platform service.
    """
    base_url: str = "https://api.bhiv.internal/platform/v1/optimization/solver-fabric"
    api_version: str = API_VERSION

    endpoints: List[APIEndpoint] = field(default_factory=lambda: [
        APIEndpoint(
            path="/capabilities",
            method="GET",
            description="Discover available solvers matching query criteria",
            input_contract={"query_params": ["problem_type", "solver_type", "deterministic"]},
            output_contract={"solvers": "List[SolverCapability]"},
            error_codes=("400",),
        ),
        APIEndpoint(
            path="/execute",
            method="POST",
            description="Submit optimization problem for deterministic execution",
            input_contract={
                "required": ["problem_schema"],
                "properties": {
                    "problem_schema": {"problem_type": "string", "required_constraints": "List[str]"},
                    "payload": {"variables": "List", "constraints": "List", "objective": "List"},
                    "execution_constraints": {"max_time_ms": "int", "max_memory_mb": "int"},
                },
            },
            output_contract={
                "execution_id": "string",
                "selected_solver": "string",
                "status": "string",
                "solution": "dict",
                "telemetry": "dict",
                "replay_metadata": "dict",
                "confidence_score": "float",
            },
            error_codes=("400", "422", "429", "500", "504"),
        ),
        APIEndpoint(
            path="/health",
            method="GET",
            description="Runtime health status",
            output_contract={"status": "string", "solvers_registered": "int", "uptime_seconds": "float"},
        ),
        APIEndpoint(
            path="/solvers/{id}",
            method="GET",
            description="Retrieve specific solver metadata",
            output_contract={"solver": "SolverCapability"},
            error_codes=("404",),
        ),
        APIEndpoint(
            path="/solvers/{id}/status",
            method="GET",
            description="Solver health status",
            output_contract={"status": "string"},
            error_codes=("404",),
        ),
    ])

    def get_endpoint(self, path: str) -> Optional[APIEndpoint]:
        for ep in self.endpoints:
            if ep.path == path:
                return ep
        return None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "base_url": self.base_url,
            "api_version": self.api_version,
            "endpoints": [
                {
                    "path": ep.path,
                    "method": ep.method,
                    "description": ep.description,
                    "input_contract": ep.input_contract,
                    "output_contract": ep.output_contract,
                    "error_codes": list(ep.error_codes),
                }
                for ep in self.endpoints
            ],
        }


# ---------------------------------------------------------------------------
# Event Contract
# ---------------------------------------------------------------------------

@dataclass
class RuntimeEvent:
    """A single runtime event emitted by the Solver Fabric."""
    event_type: str
    trace_id: str
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    payload: Dict[str, Any] = field(default_factory=dict)
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "trace_id": self.trace_id,
            "timestamp": self.timestamp,
            "payload": self.payload,
        }


class EventContract:
    """
    Manages the event contract for the Solver Fabric.
    Events are emitted but NOT persisted here — that is the TraceStore's job.
    """

    VALID_EVENTS = tuple(e.value for e in EventType)

    def __init__(self):
        self._listeners: List[Any] = []
        self._event_log: List[RuntimeEvent] = []

    def emit(self, event_type: str, trace_id: str, payload: Dict[str, Any] = None) -> RuntimeEvent:
        """Emit a runtime event."""
        if event_type not in self.VALID_EVENTS:
            raise ValueError(f"Invalid event type: {event_type}. Valid: {self.VALID_EVENTS}")

        event = RuntimeEvent(
            event_type=event_type,
            trace_id=trace_id,
            payload=payload or {},
        )
        self._event_log.append(event)

        for listener in self._listeners:
            try:
                listener(event)
            except Exception:
                pass  # Listeners must not crash the fabric

        return event

    def register_listener(self, listener) -> None:
        self._listeners.append(listener)

    def get_events(self, event_type: str = None, trace_id: str = None) -> List[RuntimeEvent]:
        """Query events by type and/or trace_id."""
        result = self._event_log
        if event_type:
            result = [e for e in result if e.event_type == event_type]
        if trace_id:
            result = [e for e in result if e.trace_id == trace_id]
        return result

    @property
    def event_count(self) -> int:
        return len(self._event_log)


# ---------------------------------------------------------------------------
# Attachment Contract
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class AttachmentContract:
    """
    Defines how consumers bind to the Solver Fabric.
    """
    supported_modes: Tuple[str, ...] = ("LOCAL", "REMOTE", "HYBRID")
    default_mode: str = "LOCAL"
    negotiation_header: str = "X-Attachment-Mode"

    def validate_mode(self, mode: str) -> bool:
        return mode.upper() in self.supported_modes

    def negotiate(self, requested_mode: str) -> str:
        """Negotiate attachment mode. Falls back to default if unsupported."""
        if self.validate_mode(requested_mode):
            return requested_mode.upper()
        return self.default_mode


ATTACHMENT_CONTRACT = AttachmentContract()


# ---------------------------------------------------------------------------
# Consumer / Producer Compatibility
# ---------------------------------------------------------------------------

@dataclass
class ConsumerCompatibility:
    """Validates that a consumer request meets the fabric's input contract."""

    required_fields: Tuple[str, ...] = ("problem_type",)
    optional_fields: Tuple[str, ...] = (
        "required_constraints", "require_deterministic", "require_replay",
        "require_explainability", "available_memory_mb", "available_cores",
        "max_variables", "max_constraints", "required_objective",
    )

    def validate(self, request: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validate consumer request. Returns (valid, errors)."""
        errors = []
        for field_name in self.required_fields:
            if field_name not in request:
                errors.append(f"Missing required field: {field_name}")
        return len(errors) == 0, errors


@dataclass
class ProducerCompatibility:
    """Validates that execution output meets the fabric's output contract."""

    required_output_fields: Tuple[str, ...] = (
        "trace_id", "replay_id", "status", "provenance", "result",
    )

    def validate(self, output: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validate producer output. Returns (valid, errors)."""
        errors = []
        for field_name in self.required_output_fields:
            if field_name not in output:
                errors.append(f"Missing required output field: {field_name}")
        return len(errors) == 0, errors


CONSUMER_COMPAT = ConsumerCompatibility()
PRODUCER_COMPAT = ProducerCompatibility()


# ---------------------------------------------------------------------------
# Failure Behaviour
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class FailureBehaviour:
    """
    Deterministic failure handling specification.
    The fabric always returns structured failure evidence — it never raises
    unhandled exceptions to consumers.
    """

    failure_codes: Dict[str, str] = field(default_factory=lambda: {
        fc.name: fc.value for fc in FailureCode
    })

    def create_failure_evidence(
        self,
        failure_code: FailureCode,
        trace_id: str,
        detail: str = "",
    ) -> Dict[str, Any]:
        """Create a deterministic failure evidence package."""
        return {
            "trace_id": trace_id,
            "replay_id": str(uuid.uuid4()),
            "status": "FAILED",
            "failure_code": failure_code.value,
            "detail": detail,
            "provenance": {
                "timestamp_ms": int(time.time() * 1000),
                "fabric_version": FABRIC_VERSION,
                "runtime_id": RUNTIME_ID,
            },
            "result": {},
        }


FAILURE_BEHAVIOUR = FailureBehaviour()


# ---------------------------------------------------------------------------
# Replay Guarantees
# ---------------------------------------------------------------------------

@dataclass
class ReplayGuarantee:
    """
    Documents and enforces replay guarantees for the Solver Fabric.
    """

    guarantees: Tuple[str, ...] = (
        "Every execution produces a unique replay_id (UUID v4)",
        "Every execution produces a unique trace_id (UUID v4)",
        "Deterministic inputs are captured in the evidence package",
        "Provenance metadata (timestamps, versions, solver info) is captured",
        "Replay IDs are submitted to the platform Replay Registry",
        "Cross-participant replay chains span Fabric → Gateway → Registry",
    )

    def validate_evidence(self, evidence: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validate that an evidence package meets replay guarantees."""
        errors = []
        if "trace_id" not in evidence:
            errors.append("Missing trace_id")
        if "replay_id" not in evidence:
            errors.append("Missing replay_id")
        if "deterministic_inputs" not in evidence:
            errors.append("Missing deterministic_inputs")
        if "provenance" not in evidence:
            errors.append("Missing provenance")
        else:
            prov = evidence["provenance"]
            for pfield in ("fabric_version", "solver_id", "solver_version"):
                if pfield not in prov:
                    errors.append(f"Missing provenance field: {pfield}")
        return len(errors) == 0, errors


REPLAY_GUARANTEE = ReplayGuarantee()


# ---------------------------------------------------------------------------
# Evidence Guarantees
# ---------------------------------------------------------------------------

class EvidenceChain:
    """
    Append-only hash chain for execution evidence.
    Each evidence record is chained to the previous one via SHA-256.
    """

    GENESIS_HASH = hashlib.sha256(b"USF_EVIDENCE_GENESIS").hexdigest()

    def __init__(self):
        self._chain: List[Dict[str, Any]] = []
        self._head_hash: str = self.GENESIS_HASH

    def append(self, evidence: Dict[str, Any]) -> Dict[str, Any]:
        """Append an evidence record to the chain."""
        evidence["previous_evidence_hash"] = self._head_hash

        hash_input = json.dumps({
            "trace_id": evidence.get("trace_id", ""),
            "replay_id": evidence.get("replay_id", ""),
            "status": evidence.get("status", ""),
            "previous_hash": self._head_hash,
        }, sort_keys=True)

        evidence["evidence_hash"] = hashlib.sha256(hash_input.encode()).hexdigest()
        self._chain.append(evidence)
        self._head_hash = evidence["evidence_hash"]
        return evidence

    def verify(self) -> bool:
        """Verify the integrity of the entire evidence chain."""
        head = self.GENESIS_HASH
        for record in self._chain:
            if record.get("previous_evidence_hash") != head:
                return False

            hash_input = json.dumps({
                "trace_id": record.get("trace_id", ""),
                "replay_id": record.get("replay_id", ""),
                "status": record.get("status", ""),
                "previous_hash": head,
            }, sort_keys=True)

            expected = hashlib.sha256(hash_input.encode()).hexdigest()
            if record.get("evidence_hash") != expected:
                return False

            head = record["evidence_hash"]

        return head == self._head_hash

    @property
    def chain_length(self) -> int:
        return len(self._chain)

    @property
    def head_hash(self) -> str:
        return self._head_hash

    def get_all(self) -> List[Dict[str, Any]]:
        return list(self._chain)


# ---------------------------------------------------------------------------
# Deterministic Runtime Guarantees
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class DeterministicGuarantees:
    """
    Documents the deterministic guarantees provided by the Solver Fabric.
    """

    guarantees: Tuple[str, ...] = (
        "Solver Selection Engine produces identical ordering for identical inputs",
        "Evidence packages contain all state required for replay",
        "Failure codes are deterministic and structured",
        "State transitions follow the defined lifecycle FSM",
        "Version negotiation is deterministic given the same inputs",
        "Evidence chain hashes are deterministic and verifiable",
    )

    non_deterministic_fields: Tuple[str, ...] = (
        "timestamp (observability only, not used for replay ordering)",
        "execution_duration_ms (depends on runtime environment)",
        "uuid generation (unique per execution, not reproducible)",
    )


DETERMINISTIC_GUARANTEES = DeterministicGuarantees()


# ---------------------------------------------------------------------------
# Composite Contract
# ---------------------------------------------------------------------------

class ConstitutionalRuntimeContract:
    """
    The complete Constitutional Runtime Participant Contract for the
    Universal Solver Fabric.

    Aggregates all sub-contracts into a single testable entry point.
    """

    def __init__(self):
        self.authority = AUTHORITY_MATRIX
        self.runtime = RuntimeContract()
        self.api = APIContract()
        self.events = EventContract()
        self.attachment = ATTACHMENT_CONTRACT
        self.consumer_compat = CONSUMER_COMPAT
        self.producer_compat = PRODUCER_COMPAT
        self.failure = FAILURE_BEHAVIOUR
        self.replay = REPLAY_GUARANTEE
        self.evidence_chain = EvidenceChain()
        self.deterministic = DETERMINISTIC_GUARANTEES

    def get_identity(self) -> Dict[str, Any]:
        """Return the fabric's constitutional identity."""
        return {
            "runtime_id": self.runtime.runtime_id,
            "capability_id": self.runtime.capability_id,
            "permanent_identity": self.runtime.permanent_identity,
            "constitutional_layer": self.runtime.constitutional_layer,
            "fabric_version": self.runtime.fabric_version,
            "schema_version": self.runtime.schema_version,
            "api_version": self.runtime.api_version,
        }

    def validate_consumer_request(self, request: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validate a consumer request against the input contract."""
        return self.consumer_compat.validate(request)

    def validate_execution_output(self, output: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validate execution output against the output contract."""
        return self.producer_compat.validate(output)

    def negotiate_version(self, requested: str) -> Tuple[VersionCompatibility, str]:
        """Negotiate version compatibility."""
        return negotiate_version(requested)

    def negotiate_attachment(self, requested_mode: str) -> str:
        """Negotiate attachment mode."""
        return self.attachment.negotiate(requested_mode)

    def record_evidence(self, evidence: Dict[str, Any]) -> Dict[str, Any]:
        """Record evidence in the hash chain."""
        return self.evidence_chain.append(evidence)

    def verify_evidence_chain(self) -> bool:
        """Verify the evidence chain integrity."""
        return self.evidence_chain.verify()

    def emit_event(self, event_type: str, trace_id: str, payload: Dict[str, Any] = None) -> RuntimeEvent:
        """Emit a runtime event."""
        return self.events.emit(event_type, trace_id, payload)

    def create_failure(self, code: FailureCode, trace_id: str, detail: str = "") -> Dict[str, Any]:
        """Create a failure evidence package."""
        return self.failure.create_failure_evidence(code, trace_id, detail)

    def to_manifest(self) -> Dict[str, Any]:
        """Export the full contract as a manifest dictionary."""
        return {
            "identity": self.get_identity(),
            "authority_matrix": {
                "owns": list(self.authority.owns),
                "does_not_own": list(self.authority.does_not_own),
                "delegates_to": self.authority.delegates_to,
            },
            "runtime_contract": self.runtime.to_dict(),
            "api_contract": self.api.to_dict(),
            "attachment_contract": {
                "supported_modes": list(self.attachment.supported_modes),
                "default_mode": self.attachment.default_mode,
            },
            "event_contract": {
                "valid_events": list(EventContract.VALID_EVENTS),
            },
            "version_negotiation": {
                "current_version": FABRIC_VERSION,
                "schema_version": SCHEMA_VERSION,
                "api_version": API_VERSION,
            },
            "replay_guarantees": list(self.replay.guarantees),
            "deterministic_guarantees": list(self.deterministic.guarantees),
            "evidence_chain_head": self.evidence_chain.head_hash,
        }
