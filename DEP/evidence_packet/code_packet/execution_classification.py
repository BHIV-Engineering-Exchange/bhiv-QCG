"""
execution_classification.py — Execution Classification System

Defines the canonical taxonomy for execution paths in the BHIV/QCG
hybrid quantum-classical runtime. Every execution result MUST carry
its classification and path.

CLASSIFICATION TAXONOMY
-----------------------
CLASSICAL           — Pure classical computation, no quantum involvement.
QUANTUM_LOCAL       — Quantum execution on a local simulator (e.g., Qiskit Aer).
QUANTUM_SIMULATED   — Quantum execution on a remote/cloud simulator.
QUANTUM_LIVE        — Quantum execution on real quantum hardware.
HYBRID              — Combined quantum + classical execution.

EXECUTION PATH
--------------
LIVE       — Executed on a live, declared provider.
LOCAL      — Executed on the local machine.
SIMULATED  — Executed on a simulator (local or remote).
FALLBACK   — Quantum unavailable; fell back to classical.
BLOCKED    — Execution could not proceed (validation failure, provider down, etc.)

AUTHORITY BOUNDARY
------------------
This module OWNS:
    - Classification enums and taxonomy
    - ClassifiedResult construction
    - Classification logic from provider state

This module does NOT OWN:
    - Provider health checking       → QuantumProviderRegistry
    - Workload routing decisions     → WorkloadRouter
    - Trust/governance decisions     → GovernanceLayer
    - Replay authority               → CanonicalReplayAuthority
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional


# ---------------------------------------------------------------------------
# Execution Classification Enum
# ---------------------------------------------------------------------------

class ExecutionClassification(str, Enum):
    """Canonical execution classification for the hybrid runtime."""
    CLASSICAL = "CLASSICAL"
    QUANTUM_LOCAL = "QUANTUM_LOCAL"
    QUANTUM_SIMULATED = "QUANTUM_SIMULATED"
    QUANTUM_LIVE = "QUANTUM_LIVE"
    HYBRID = "HYBRID"


class ExecutionPath(str, Enum):
    """Describes HOW the execution was carried out."""
    LIVE = "LIVE"
    LOCAL = "LOCAL"
    SIMULATED = "SIMULATED"
    FALLBACK = "FALLBACK"
    BLOCKED = "BLOCKED"


class ProviderStatus(str, Enum):
    """Health status of a quantum provider."""
    AVAILABLE = "AVAILABLE"
    DEGRADED = "DEGRADED"
    UNAVAILABLE = "UNAVAILABLE"
    UNKNOWN = "UNKNOWN"


# ---------------------------------------------------------------------------
# Classified Result — every execution output MUST be wrapped in this
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ClassifiedResult:
    """
    Wraps any execution result with explicit classification metadata.

    Every result flowing through the hybrid runtime MUST be wrapped in
    a ClassifiedResult. This ensures the consumer always knows:
      - What type of execution was performed
      - Whether it was live, local, simulated, fallback, or blocked
      - Which provider handled it
      - Evidence hash for provenance

    Fields marked DETERMINISTIC produce identical outputs for identical inputs.
    Fields marked OBSERVABILITY are for audit/tracing and may vary between runs.
    """
    # --- DETERMINISTIC fields ---
    trace_id: str                                                    # DETERMINISTIC
    classification: str                                              # DETERMINISTIC
    execution_path: str                                              # DETERMINISTIC
    provider_id: str                                                 # DETERMINISTIC
    result_payload: Dict[str, Any]                                   # DETERMINISTIC
    confidence: float                                                # DETERMINISTIC
    result_hash: str = ""                                            # DETERMINISTIC (auto-computed)

    # --- PROVENANCE fields ---
    fallback_reason: str = ""                                        # PROVENANCE
    blocked_reason: str = ""                                         # PROVENANCE
    original_classification: str = ""                                # PROVENANCE (before fallback)

    # --- OBSERVABILITY fields ---
    timestamp: str = field(                                          # OBSERVABILITY
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def __post_init__(self):
        if not self.result_hash:
            raw = json.dumps({
                "trace_id": self.trace_id,
                "classification": self.classification,
                "execution_path": self.execution_path,
                "provider_id": self.provider_id,
                "result_payload": self.result_payload,
                "confidence": self.confidence,
            }, sort_keys=True, default=str)
            object.__setattr__(
                self, "result_hash",
                hashlib.sha256(raw.encode()).hexdigest()
            )

    def to_dict(self) -> dict:
        return asdict(self)

    @property
    def is_quantum(self) -> bool:
        return self.classification in (
            ExecutionClassification.QUANTUM_LOCAL.value,
            ExecutionClassification.QUANTUM_SIMULATED.value,
            ExecutionClassification.QUANTUM_LIVE.value,
            ExecutionClassification.HYBRID.value,
        )

    @property
    def is_fallback(self) -> bool:
        return self.execution_path == ExecutionPath.FALLBACK.value

    @property
    def is_blocked(self) -> bool:
        return self.execution_path == ExecutionPath.BLOCKED.value


# ---------------------------------------------------------------------------
# Classification Logic
# ---------------------------------------------------------------------------

def classify_execution(
    provider_id: str,
    provider_status: str,
    is_local_simulator: bool,
    is_remote_simulator: bool,
    is_live_hardware: bool,
    has_classical_component: bool = False,
) -> tuple[ExecutionClassification, ExecutionPath]:
    """
    Determine execution classification and path from provider state.

    Returns (classification, execution_path).

    Rules:
    1. If provider is UNAVAILABLE → (original_classification, BLOCKED)
    2. If live hardware → (QUANTUM_LIVE, LIVE)
    3. If remote simulator → (QUANTUM_SIMULATED, SIMULATED)
    4. If local simulator → (QUANTUM_LOCAL, LOCAL)
    5. If has_classical_component and any quantum → (HYBRID, path)
    6. Otherwise → (CLASSICAL, LOCAL)
    """
    if provider_status == ProviderStatus.UNAVAILABLE.value:
        return ExecutionClassification.CLASSICAL, ExecutionPath.BLOCKED

    if is_live_hardware:
        cls = ExecutionClassification.QUANTUM_LIVE
        path = ExecutionPath.LIVE
    elif is_remote_simulator:
        cls = ExecutionClassification.QUANTUM_SIMULATED
        path = ExecutionPath.SIMULATED
    elif is_local_simulator:
        cls = ExecutionClassification.QUANTUM_LOCAL
        path = ExecutionPath.LOCAL
    else:
        cls = ExecutionClassification.CLASSICAL
        path = ExecutionPath.LOCAL

    if has_classical_component and cls in (
        ExecutionClassification.QUANTUM_LIVE,
        ExecutionClassification.QUANTUM_SIMULATED,
        ExecutionClassification.QUANTUM_LOCAL,
    ):
        cls = ExecutionClassification.HYBRID

    return cls, path


def build_classified_result(
    trace_id: str,
    classification: ExecutionClassification,
    execution_path: ExecutionPath,
    provider_id: str,
    result_payload: Dict[str, Any],
    confidence: float,
    fallback_reason: str = "",
    blocked_reason: str = "",
    original_classification: str = "",
) -> ClassifiedResult:
    """Factory function to build a ClassifiedResult with proper defaults."""
    return ClassifiedResult(
        trace_id=trace_id,
        classification=classification.value,
        execution_path=execution_path.value,
        provider_id=provider_id,
        result_payload=result_payload,
        confidence=confidence,
        fallback_reason=fallback_reason,
        blocked_reason=blocked_reason,
        original_classification=original_classification,
    )


def build_blocked_result(
    trace_id: str,
    blocked_reason: str,
    original_classification: str = "",
) -> ClassifiedResult:
    """Build a BLOCKED result when execution cannot proceed."""
    return ClassifiedResult(
        trace_id=trace_id,
        classification=ExecutionClassification.CLASSICAL.value,
        execution_path=ExecutionPath.BLOCKED.value,
        provider_id="NONE",
        result_payload={"status": "BLOCKED", "reason": blocked_reason},
        confidence=0.0,
        blocked_reason=blocked_reason,
        original_classification=original_classification,
    )


def build_fallback_result(
    trace_id: str,
    result_payload: Dict[str, Any],
    confidence: float,
    fallback_reason: str,
    original_classification: str,
) -> ClassifiedResult:
    """Build a FALLBACK result when quantum execution falls back to classical."""
    return ClassifiedResult(
        trace_id=trace_id,
        classification=ExecutionClassification.CLASSICAL.value,
        execution_path=ExecutionPath.FALLBACK.value,
        provider_id="CLASSICAL_FALLBACK",
        result_payload=result_payload,
        confidence=confidence,
        fallback_reason=fallback_reason,
        original_classification=original_classification,
    )
