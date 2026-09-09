"""
workload_router.py — Workload Suitability Assessment & Routing

Analyzes incoming workloads and determines whether they should be
routed to quantum or classical execution. Produces explicit routing
decisions with classification.

RESPONSIBILITY BOUNDARY
-----------------------
WorkloadRouter OWNS:
    - Workload suitability assessment
    - Routing decision production
    - Fallback determination
    - QUBO suitability detection

WorkloadRouter does NOT OWN:
    - Provider health              → QuantumProviderRegistry
    - Actual execution             → HybridRuntimeOrchestrator
    - Trust/governance decisions   → GovernanceLayer
    - Quantum circuit construction → QuantumProducer
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from execution_classification import (
    ExecutionClassification,
    ExecutionPath,
    ProviderStatus,
)
from quantum_provider_registry import QuantumProviderRegistry, QuantumProviderRecord

logger = logging.getLogger("qcg.workload_router")


# ---------------------------------------------------------------------------
# Workload Suitability
# ---------------------------------------------------------------------------

class WorkloadSuitability(str, Enum):
    """Assessment of whether a workload benefits from quantum execution."""
    QUANTUM_PREFERRED = "QUANTUM_PREFERRED"
    CLASSICAL_PREFERRED = "CLASSICAL_PREFERRED"
    HYBRID_REQUIRED = "HYBRID_REQUIRED"
    QUANTUM_REQUIRED = "QUANTUM_REQUIRED"


# ---------------------------------------------------------------------------
# Routing Decision
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class RoutingDecision:
    """
    Explicit routing decision for a workload.

    Contains the suitability assessment, recommended provider,
    whether fallback is available, and the reasoning.
    """
    workload_id: str
    suitability: str                                          # WorkloadSuitability value
    recommended_provider_id: str
    recommended_classification: str                           # ExecutionClassification value
    recommended_path: str                                     # ExecutionPath value
    fallback_available: bool
    fallback_provider_id: str = ""
    fallback_classification: str = ""
    reason: str = ""
    assessed_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> dict:
        from dataclasses import asdict
        return asdict(self)


# ---------------------------------------------------------------------------
# Workload Metadata
# ---------------------------------------------------------------------------

@dataclass
class WorkloadMetadata:
    """
    Metadata describing a workload for routing decisions.

    The router uses this to determine suitability and provider selection.
    """
    workload_id: str
    workload_type: str = "GENERAL"           # GENERAL | OPTIMIZATION | SIMULATION | COMMUNICATION
    problem_size: int = 0                     # Number of variables/qubits needed
    is_qubo_compatible: bool = False           # Can be formulated as QUBO
    requires_entanglement: bool = False        # Needs quantum entanglement
    requires_live_hardware: bool = False       # Must run on real quantum hardware
    max_acceptable_noise: float = 1.0          # Noise tolerance [0, 1]
    classical_fallback_acceptable: bool = True # Can fall back to classical
    constraints: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        from dataclasses import asdict
        return asdict(self)


# ---------------------------------------------------------------------------
# Workload Router
# ---------------------------------------------------------------------------

class WorkloadRouter:
    """
    Routes workloads to the appropriate execution provider based on
    suitability assessment and provider availability.

    The router NEVER executes workloads — it only produces routing decisions.
    """

    def __init__(self, provider_registry: QuantumProviderRegistry):
        self._registry = provider_registry

    def assess_suitability(self, metadata: WorkloadMetadata) -> WorkloadSuitability:
        """
        Assess whether a workload is suitable for quantum execution.

        Rules:
        1. QUBO-compatible → QUANTUM_PREFERRED
        2. Requires entanglement → QUANTUM_REQUIRED
        3. Requires live hardware → QUANTUM_REQUIRED
        4. Small problem (< 3 variables) → CLASSICAL_PREFERRED
        5. Large optimization (> 100 variables on current NISQ) → HYBRID_REQUIRED
        6. Default → CLASSICAL_PREFERRED
        """
        if metadata.requires_live_hardware or metadata.requires_entanglement:
            return WorkloadSuitability.QUANTUM_REQUIRED

        if metadata.is_qubo_compatible:
            if metadata.problem_size > 100:
                # Too large for current NISQ devices, needs hybrid approach
                return WorkloadSuitability.HYBRID_REQUIRED
            elif metadata.problem_size >= 3:
                return WorkloadSuitability.QUANTUM_PREFERRED
            else:
                # Trivially small — classical is more efficient
                return WorkloadSuitability.CLASSICAL_PREFERRED

        if metadata.workload_type == "SIMULATION" and metadata.problem_size >= 5:
            return WorkloadSuitability.QUANTUM_PREFERRED

        return WorkloadSuitability.CLASSICAL_PREFERRED

    def route(self, metadata: WorkloadMetadata) -> RoutingDecision:
        """
        Produce a routing decision for the given workload.

        This is the main entry point. It assesses suitability, checks
        provider availability, and returns an explicit decision.
        """
        suitability = self.assess_suitability(metadata)

        # Get available providers
        available = self._registry.list_available_providers()
        best_provider = self._registry.get_best_provider(
            min_qubits=metadata.problem_size,
            prefer_live=metadata.requires_live_hardware,
        )

        # Determine routing based on suitability + availability
        if suitability == WorkloadSuitability.CLASSICAL_PREFERRED:
            return self._route_classical(metadata, suitability, best_provider)

        if suitability == WorkloadSuitability.QUANTUM_REQUIRED:
            return self._route_quantum_required(metadata, suitability, best_provider)

        if suitability in (WorkloadSuitability.QUANTUM_PREFERRED, WorkloadSuitability.HYBRID_REQUIRED):
            return self._route_quantum_preferred(metadata, suitability, best_provider)

        # Fallback
        return self._route_classical(metadata, suitability, best_provider)

    # -- Internal routing strategies ----------------------------------------

    def _route_classical(
        self,
        metadata: WorkloadMetadata,
        suitability: WorkloadSuitability,
        best_provider: Optional[QuantumProviderRecord],
    ) -> RoutingDecision:
        """Route to classical execution."""
        return RoutingDecision(
            workload_id=metadata.workload_id,
            suitability=suitability.value,
            recommended_provider_id="CLASSICAL_RUNTIME",
            recommended_classification=ExecutionClassification.CLASSICAL.value,
            recommended_path=ExecutionPath.LOCAL.value,
            fallback_available=False,
            reason="Workload assessed as classical-preferred",
        )

    def _route_quantum_required(
        self,
        metadata: WorkloadMetadata,
        suitability: WorkloadSuitability,
        best_provider: Optional[QuantumProviderRecord],
    ) -> RoutingDecision:
        """Route quantum-required workloads. Block if no provider available."""
        if best_provider is None:
            # No quantum provider available — check if fallback acceptable
            if metadata.classical_fallback_acceptable:
                return RoutingDecision(
                    workload_id=metadata.workload_id,
                    suitability=suitability.value,
                    recommended_provider_id="CLASSICAL_FALLBACK",
                    recommended_classification=ExecutionClassification.CLASSICAL.value,
                    recommended_path=ExecutionPath.FALLBACK.value,
                    fallback_available=True,
                    reason="Quantum required but no provider available; falling back to classical",
                )
            else:
                return RoutingDecision(
                    workload_id=metadata.workload_id,
                    suitability=suitability.value,
                    recommended_provider_id="NONE",
                    recommended_classification=ExecutionClassification.CLASSICAL.value,
                    recommended_path=ExecutionPath.BLOCKED.value,
                    fallback_available=False,
                    reason="Quantum required but no provider available and fallback not acceptable",
                )

        cls = best_provider.get_execution_classification()
        path = ExecutionPath.LIVE if best_provider.is_live_hardware else (
            ExecutionPath.SIMULATED if best_provider.is_remote_simulator else ExecutionPath.LOCAL
        )

        return RoutingDecision(
            workload_id=metadata.workload_id,
            suitability=suitability.value,
            recommended_provider_id=best_provider.provider_id,
            recommended_classification=cls.value,
            recommended_path=path.value,
            fallback_available=metadata.classical_fallback_acceptable,
            fallback_provider_id="CLASSICAL_RUNTIME" if metadata.classical_fallback_acceptable else "",
            fallback_classification=ExecutionClassification.CLASSICAL.value if metadata.classical_fallback_acceptable else "",
            reason=f"Routed to {best_provider.provider_name} ({best_provider.provider_type})",
        )

    def _route_quantum_preferred(
        self,
        metadata: WorkloadMetadata,
        suitability: WorkloadSuitability,
        best_provider: Optional[QuantumProviderRecord],
    ) -> RoutingDecision:
        """Route quantum-preferred workloads with classical fallback."""
        if best_provider is None:
            return RoutingDecision(
                workload_id=metadata.workload_id,
                suitability=suitability.value,
                recommended_provider_id="CLASSICAL_FALLBACK",
                recommended_classification=ExecutionClassification.CLASSICAL.value,
                recommended_path=ExecutionPath.FALLBACK.value,
                fallback_available=True,
                reason="Quantum preferred but no provider available; falling back to classical",
            )

        cls = best_provider.get_execution_classification()
        path = ExecutionPath.LIVE if best_provider.is_live_hardware else (
            ExecutionPath.SIMULATED if best_provider.is_remote_simulator else ExecutionPath.LOCAL
        )

        return RoutingDecision(
            workload_id=metadata.workload_id,
            suitability=suitability.value,
            recommended_provider_id=best_provider.provider_id,
            recommended_classification=cls.value,
            recommended_path=path.value,
            fallback_available=True,
            fallback_provider_id="CLASSICAL_RUNTIME",
            fallback_classification=ExecutionClassification.CLASSICAL.value,
            reason=f"Quantum preferred; routed to {best_provider.provider_name} ({best_provider.provider_type})",
        )
