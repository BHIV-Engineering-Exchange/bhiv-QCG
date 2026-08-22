"""
fabric_observability.py — Solver Fabric Observability, Evidence & Replay

Complete runtime proof generation for the Universal Solver Fabric.
Integrates with the platform's observability layer (observability.py)
and produces comprehensive execution evidence.

RESPONSIBILITY BOUNDARY
-----------------------
This module OWNS:
    - Solver-specific trace generation
    - Runtime health metric collection
    - Consumer invocation logging
    - Failure scenario evidence
    - Compatibility validation evidence
    - Cross-participant replay chain construction
    - Evidence export for proof packets

This module does NOT OWN:
    - Platform TraceStore internals    → observability.py
    - Replay enforcement              → replay_registry.py
    - Evidence chain hashing           → constitutional_runtime_contract.py
"""

from __future__ import annotations

import hashlib
import json
import logging
import sys
import os
import time
import uuid
from collections import deque
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from constitutional_runtime_contract import (
    ConstitutionalRuntimeContract,
    EventType,
    RUNTIME_ID,
    CAPABILITY_ID,
    FABRIC_VERSION,
)

logger = logging.getLogger("solver_fabric.observability")

_MAX_ENTRIES = 10_000


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------

@dataclass
class FabricMetrics:
    """Runtime metrics for the Solver Fabric."""
    executions_total: int = 0
    executions_successful: int = 0
    executions_failed: int = 0
    solvers_registered: int = 0
    total_execution_time_ms: float = 0.0
    total_selection_time_ms: float = 0.0
    startup_timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    last_execution_timestamp: str = ""
    consumer_invocations: int = 0
    replay_submissions: int = 0
    evidence_records: int = 0

    @property
    def avg_execution_time_ms(self) -> float:
        if self.executions_total == 0:
            return 0.0
        return self.total_execution_time_ms / self.executions_total

    @property
    def failure_rate(self) -> float:
        if self.executions_total == 0:
            return 0.0
        return self.executions_failed / self.executions_total

    @property
    def uptime_seconds(self) -> float:
        start = datetime.fromisoformat(self.startup_timestamp)
        now = datetime.now(timezone.utc)
        return (now - start).total_seconds()

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["avg_execution_time_ms"] = self.avg_execution_time_ms
        d["failure_rate"] = self.failure_rate
        d["uptime_seconds"] = self.uptime_seconds
        return d


# ---------------------------------------------------------------------------
# Execution Trace
# ---------------------------------------------------------------------------

@dataclass
class ExecutionTrace:
    """Complete trace record for a single solver execution."""
    trace_id: str
    replay_id: str
    solver_id: str
    problem_type: str
    status: str
    execution_duration_ms: float
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    sequence: int = 0
    solver_version: str = ""
    attachment_mode: str = "LOCAL"
    confidence: float = 0.0
    failure_code: str = ""
    failure_detail: str = ""
    evidence_hash: str = ""
    gateway_bridge_id: str = ""
    replay_registry_seq: int = 0
    consumer_id: str = ""

    def __post_init__(self):
        if not self.evidence_hash:
            raw = json.dumps({
                "trace_id": self.trace_id,
                "replay_id": self.replay_id,
                "solver_id": self.solver_id,
                "status": self.status,
                "sequence": self.sequence,
            }, sort_keys=True)
            self.evidence_hash = hashlib.sha256(raw.encode()).hexdigest()

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Consumer Invocation Log
# ---------------------------------------------------------------------------

@dataclass
class ConsumerInvocation:
    """Log entry for a consumer invocation of the fabric."""
    invocation_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    consumer_id: str = ""
    operation: str = ""
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    request_hash: str = ""
    response_status: str = ""
    duration_ms: float = 0.0
    trace_id: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Failure Evidence
# ---------------------------------------------------------------------------

@dataclass
class FailureEvidence:
    """Structured evidence for a failure scenario."""
    failure_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    trace_id: str = ""
    failure_code: str = ""
    failure_detail: str = ""
    solver_id: str = ""
    problem_type: str = ""
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    recovery_action: str = ""
    evidence_hash: str = ""

    def __post_init__(self):
        if not self.evidence_hash:
            raw = json.dumps({
                "failure_id": self.failure_id,
                "trace_id": self.trace_id,
                "failure_code": self.failure_code,
            }, sort_keys=True)
            self.evidence_hash = hashlib.sha256(raw.encode()).hexdigest()

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Solver Fabric Observability
# ---------------------------------------------------------------------------

class SolverFabricObservability:
    """
    Complete observability layer for the Universal Solver Fabric.

    Collects:
        - Execution traces with evidence hashes
        - Runtime metrics (counters, histograms)
        - Consumer invocation logs
        - Failure evidence
        - Compatibility validation results
        - Cross-participant replay chains

    Integrates with:
        - Platform TraceStore (observability.py)
        - Constitutional evidence chain
        - Replay Registry
    """

    def __init__(
        self,
        contract: ConstitutionalRuntimeContract = None,
    ):
        self._contract = contract or ConstitutionalRuntimeContract()
        self._metrics = FabricMetrics()
        self._traces: deque = deque(maxlen=_MAX_ENTRIES)
        self._consumer_log: deque = deque(maxlen=_MAX_ENTRIES)
        self._failure_log: deque = deque(maxlen=_MAX_ENTRIES)
        self._sequence_counter = 0
        self._compatibility_results: List[Dict[str, Any]] = []
        self._replay_chain: List[Dict[str, Any]] = []

    # -- Execution Tracing -------------------------------------------------

    def record_execution(
        self,
        trace_id: str,
        replay_id: str,
        solver_id: str,
        problem_type: str,
        status: str,
        execution_duration_ms: float,
        solver_version: str = "",
        attachment_mode: str = "LOCAL",
        confidence: float = 0.0,
        failure_code: str = "",
        failure_detail: str = "",
        gateway_bridge_id: str = "",
        consumer_id: str = "",
    ) -> ExecutionTrace:
        """Record an execution trace."""
        self._sequence_counter += 1

        trace = ExecutionTrace(
            trace_id=trace_id,
            replay_id=replay_id,
            solver_id=solver_id,
            problem_type=problem_type,
            status=status,
            execution_duration_ms=execution_duration_ms,
            sequence=self._sequence_counter,
            solver_version=solver_version,
            attachment_mode=attachment_mode,
            confidence=confidence,
            failure_code=failure_code,
            failure_detail=failure_detail,
            gateway_bridge_id=gateway_bridge_id,
            consumer_id=consumer_id,
        )
        self._traces.append(trace)

        # Update metrics
        self._metrics.executions_total += 1
        self._metrics.total_execution_time_ms += execution_duration_ms
        self._metrics.last_execution_timestamp = trace.timestamp
        self._metrics.evidence_records += 1

        if status == "COMPLETED":
            self._metrics.executions_successful += 1
        else:
            self._metrics.executions_failed += 1

        # Record in evidence chain
        self._contract.record_evidence({
            "trace_id": trace_id,
            "replay_id": replay_id,
            "status": status,
            "solver_id": solver_id,
            "sequence": self._sequence_counter,
        })

        # Add to replay chain
        self._replay_chain.append({
            "trace_id": trace_id,
            "replay_id": replay_id,
            "sequence": self._sequence_counter,
            "participant": RUNTIME_ID,
            "gateway_bridge_id": gateway_bridge_id,
        })

        # Emit to platform TraceStore if available
        self._emit_to_platform_tracestore(trace)

        return trace

    def _emit_to_platform_tracestore(self, trace: ExecutionTrace):
        """Emit trace to platform observability layer."""
        try:
            from observability import TraceStore, TraceEntry
            store = TraceStore.get_instance()
            store.record(
                trace_id=trace.trace_id,
                trace_type="solver_fabric_execution",
                data={
                    "solver_id": trace.solver_id,
                    "problem_type": trace.problem_type,
                    "status": trace.status,
                    "execution_duration_ms": trace.execution_duration_ms,
                    "replay_id": trace.replay_id,
                    "runtime_id": RUNTIME_ID,
                    "evidence_hash": trace.evidence_hash,
                },
            )
        except Exception:
            pass  # Platform TraceStore not available; traces still stored locally

    # -- Consumer Logging --------------------------------------------------

    def log_consumer_invocation(
        self,
        consumer_id: str,
        operation: str,
        request_payload: Dict[str, Any],
        response_status: str,
        duration_ms: float,
        trace_id: str = "",
    ) -> ConsumerInvocation:
        """Log a consumer invocation of the fabric."""
        request_hash = hashlib.sha256(
            json.dumps(request_payload, sort_keys=True, default=str).encode()
        ).hexdigest()

        invocation = ConsumerInvocation(
            consumer_id=consumer_id,
            operation=operation,
            request_hash=request_hash,
            response_status=response_status,
            duration_ms=duration_ms,
            trace_id=trace_id,
        )
        self._consumer_log.append(invocation)
        self._metrics.consumer_invocations += 1
        return invocation

    # -- Failure Evidence --------------------------------------------------

    def record_failure(
        self,
        trace_id: str,
        failure_code: str,
        failure_detail: str,
        solver_id: str = "",
        problem_type: str = "",
        recovery_action: str = "GRACEFUL_DEGRADATION",
    ) -> FailureEvidence:
        """Record a failure scenario with evidence."""
        failure = FailureEvidence(
            trace_id=trace_id,
            failure_code=failure_code,
            failure_detail=failure_detail,
            solver_id=solver_id,
            problem_type=problem_type,
            recovery_action=recovery_action,
        )
        self._failure_log.append(failure)
        return failure

    # -- Compatibility Validation ------------------------------------------

    def record_compatibility_validation(
        self,
        consumer_version: str,
        fabric_version: str,
        result: str,
        details: str = "",
    ) -> Dict[str, Any]:
        """Record a version compatibility validation."""
        record = {
            "validation_id": str(uuid.uuid4()),
            "consumer_version": consumer_version,
            "fabric_version": fabric_version,
            "result": result,
            "details": details,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self._compatibility_results.append(record)
        return record

    # -- Health & Metrics --------------------------------------------------

    def get_health(self) -> Dict[str, Any]:
        """Get runtime health status."""
        status = "HEALTHY"
        if self._metrics.solvers_registered == 0:
            status = "UNHEALTHY"
        elif self._metrics.failure_rate > 0.5:
            status = "DEGRADED"

        return {
            "status": status,
            "runtime_id": RUNTIME_ID,
            "capability_id": CAPABILITY_ID,
            "fabric_version": FABRIC_VERSION,
            "uptime_seconds": self._metrics.uptime_seconds,
            "solvers_registered": self._metrics.solvers_registered,
            "executions_total": self._metrics.executions_total,
            "failure_rate": self._metrics.failure_rate,
            "avg_execution_time_ms": self._metrics.avg_execution_time_ms,
        }

    def get_metrics(self) -> Dict[str, Any]:
        """Get full runtime metrics."""
        return self._metrics.to_dict()

    def update_solver_count(self, count: int):
        """Update registered solver count metric."""
        self._metrics.solvers_registered = count

    # -- Evidence Export ---------------------------------------------------

    def export_execution_evidence(self) -> List[Dict[str, Any]]:
        """Export all execution traces as evidence."""
        return [t.to_dict() for t in self._traces]

    def export_consumer_log(self) -> List[Dict[str, Any]]:
        """Export consumer invocation logs."""
        return [c.to_dict() for c in self._consumer_log]

    def export_failure_log(self) -> List[Dict[str, Any]]:
        """Export failure evidence."""
        return [f.to_dict() for f in self._failure_log]

    def export_replay_chain(self) -> List[Dict[str, Any]]:
        """Export cross-participant replay chain."""
        return list(self._replay_chain)

    def export_compatibility_validations(self) -> List[Dict[str, Any]]:
        """Export compatibility validation results."""
        return list(self._compatibility_results)

    def export_full_proof(self) -> Dict[str, Any]:
        """
        Export the complete observability proof package.

        This is the master evidence document that demonstrates:
            - trace IDs, replay IDs, execution evidence
            - capability registration
            - runtime health
            - observability metrics
            - consumer invocation logs
            - failure scenarios
            - compatibility validation
            - replay across multiple runtime participants
        """
        return {
            "proof_id": str(uuid.uuid4()),
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "runtime_id": RUNTIME_ID,
            "capability_id": CAPABILITY_ID,
            "fabric_version": FABRIC_VERSION,
            "health": self.get_health(),
            "metrics": self.get_metrics(),
            "execution_traces": self.export_execution_evidence(),
            "consumer_invocations": self.export_consumer_log(),
            "failure_scenarios": self.export_failure_log(),
            "compatibility_validations": self.export_compatibility_validations(),
            "replay_chain": self.export_replay_chain(),
            "evidence_chain": {
                "length": self._contract.evidence_chain.chain_length,
                "head_hash": self._contract.evidence_chain.head_hash,
                "valid": self._contract.verify_evidence_chain(),
                "records": self._contract.evidence_chain.get_all(),
            },
        }

    # -- Summary Stats -----------------------------------------------------

    @property
    def trace_count(self) -> int:
        return len(self._traces)

    @property
    def failure_count(self) -> int:
        return len(self._failure_log)

    @property
    def consumer_count(self) -> int:
        return len(self._consumer_log)
