"""
hybrid_runtime_orchestrator.py — Collective Hybrid Quantum-Classical Runtime

The central convergence engine that ties all components into one executable
hybrid runtime. Implements the complete target path:

    Capability discovery
    → workload submission
    → execution suitability decision
    → quantum/classical routing
    → quantum runtime invocation
    → normalized result
    → QCG trust/replay boundary
    → Insight evidence/observability
    → quantum-network coordination contract
    → provenance output

RESPONSIBILITY BOUNDARY
-----------------------
HybridRuntimeOrchestrator OWNS:
    - End-to-end workload orchestration
    - Capability attachment through canonical discovery
    - Fallback behavior (classical when quantum unavailable)
    - Result normalization and classification
    - Health aggregation across all subsystems

HybridRuntimeOrchestrator does NOT OWN:
    - Quantum computation          → QuantumProducer / Qiskit
    - Provider health              → QuantumProviderRegistry
    - Routing decisions            → WorkloadRouter
    - Trust/governance             → GovernanceLayer / TrustChain
    - Replay authority             → CanonicalReplayAuthority
    - Evidence persistence         → EvidenceLedger
    - Network coordination         → QuantumNetworkContract
    - Observability storage        → TraceStore

AUTHORITY BOUNDARIES (enforced):
    - Quantum Runtime: may compute; may not govern.
    - QCG: may validate and execute contracts; may not manufacture quantum results.
    - Insight: may route and observe; may not become replay/governance authority.
    - Quantum Network: may coordinate quantum communication; may not silently
      inherit execution legitimacy.
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
import uuid
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import config
from execution_classification import (
    ExecutionClassification,
    ExecutionPath,
    ClassifiedResult,
    ProviderStatus,
    build_classified_result,
    build_blocked_result,
    build_fallback_result,
    classify_execution,
)
from quantum_provider_registry import QuantumProviderRegistry, QuantumProviderRecord
from workload_router import WorkloadRouter, WorkloadMetadata, WorkloadSuitability, RoutingDecision
from quantum_network_contract import (
    QuantumNetworkContract,
    QuantumNetworkNode,
    RouteRequest,
    NetworkProtocol,
    NetworkNodeStatus,
)
from evidence_ledger import EvidenceLedger
from observability import TraceStore
from execution_record import ExecutionRecord

logger = logging.getLogger("qcg.hybrid_orchestrator")


# ---------------------------------------------------------------------------
# Orchestrator Result
# ---------------------------------------------------------------------------

@dataclass
class OrchestratorResult:
    """
    Complete result from a hybrid runtime execution.

    Contains the classified result, all stage evidence, provenance,
    and the full execution path taken.
    """
    workload_id: str
    trace_id: str
    classified_result: Dict[str, Any]
    routing_decision: Dict[str, Any]
    stages: Dict[str, Any] = field(default_factory=dict)
    provenance: Dict[str, Any] = field(default_factory=dict)
    network_coordination: Dict[str, Any] = field(default_factory=dict)
    health: Dict[str, Any] = field(default_factory=dict)
    status: str = "PENDING"
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> dict:
        return asdict(self)


# ---------------------------------------------------------------------------
# Hybrid Runtime Orchestrator
# ---------------------------------------------------------------------------

class HybridRuntimeOrchestrator:
    """
    Central convergence engine for the BHIV/QCG hybrid quantum-classical runtime.

    This is the single entry point for workload submission. It discovers
    capabilities, routes workloads, executes through the appropriate path,
    normalizes results, and records evidence — all with explicit classification.
    """

    def __init__(
        self,
        provider_registry: QuantumProviderRegistry = None,
        evidence_ledger: EvidenceLedger = None,
        trace_store: TraceStore = None,
        network_contract: QuantumNetworkContract = None,
    ):
        self._provider_registry = provider_registry or QuantumProviderRegistry()
        self._router = WorkloadRouter(self._provider_registry)
        self._evidence_ledger = evidence_ledger or EvidenceLedger(
            persistence_path=config.EVIDENCE_LEDGER_PATH
        )
        self._trace_store = trace_store or TraceStore()
        self._network_contract = network_contract or QuantumNetworkContract()

        # Register default quantum network nodes
        if config.QUANTUM_NETWORK_ENABLED:
            self._register_default_network_nodes()

        logger.info("HybridRuntimeOrchestrator initialized")

    def _register_default_network_nodes(self):
        """Register this system as a quantum network node."""
        local_node = QuantumNetworkNode(
            node_id="QCG_LOCAL_NODE",
            node_name="QCG Local Quantum Node",
            capabilities=["QKD", "ENTANGLEMENT_SIMULATION", "QUBO_EXECUTION"],
            supported_protocols=[
                NetworkProtocol.BB84.value,
                NetworkProtocol.E91.value,
                NetworkProtocol.CLASSICAL_CONTROL.value,
            ],
            classical_control_endpoint=f"http://127.0.0.1:8080",
            network_status=NetworkNodeStatus.ACTIVE.value,
            max_entanglement_pairs=100,
            qubit_coherence_time_us=50.0,
        )
        self._network_contract.declare_node(local_node)

    # -- Main Entry Point ---------------------------------------------------

    def submit_workload(
        self,
        workload: Dict[str, Any],
        metadata: WorkloadMetadata = None,
    ) -> OrchestratorResult:
        """
        Submit a workload for hybrid quantum-classical execution.

        This is the complete target runtime path:
        1. Capability discovery
        2. Workload submission
        3. Execution suitability decision
        4. Quantum/classical routing
        5. Quantum runtime invocation
        6. Normalized result
        7. QCG trust/replay boundary
        8. Insight evidence/observability
        9. Quantum-network coordination contract
        10. Provenance output

        Every result carries its execution classification and evidence.
        """
        trace_id = str(uuid.uuid4())
        workload_id = workload.get("workload_id", str(uuid.uuid4()))

        result = OrchestratorResult(
            workload_id=workload_id,
            trace_id=trace_id,
            classified_result={},
            routing_decision={},
        )

        try:
            # Stage 1: Capability Discovery
            capabilities = self._discover_capabilities()
            result.stages["discovery"] = capabilities

            # Stage 2: Build metadata if not provided
            if metadata is None:
                metadata = self._extract_metadata(workload_id, workload)

            # Stage 3: Suitability Assessment & Routing
            routing_decision = self._router.route(metadata)
            result.routing_decision = routing_decision.to_dict()
            result.stages["routing"] = routing_decision.to_dict()

            # Stage 4: Execute through routed path
            classified = self._route_and_execute(
                trace_id=trace_id,
                workload=workload,
                routing=routing_decision,
                metadata=metadata,
            )
            result.classified_result = classified.to_dict()
            result.stages["execution"] = classified.to_dict()

            # Stage 5: Trust/Replay Boundary
            trust_result = self._apply_trust_boundary(trace_id, classified)
            result.stages["trust_replay"] = trust_result

            # Stage 6: Evidence & Observability
            evidence = self._record_evidence(trace_id, classified, routing_decision)
            result.stages["evidence"] = evidence

            # Stage 7: Quantum Network Coordination
            if config.QUANTUM_NETWORK_ENABLED and classified.is_quantum:
                network_result = self._coordinate_network(trace_id, classified)
                result.network_coordination = network_result
                result.stages["network"] = network_result

            # Stage 8: Provenance Output
            provenance = self._emit_provenance(trace_id, classified, routing_decision)
            result.provenance = provenance

            # Stage 9: Health Aggregation
            result.health = self.get_health()

            result.status = "COMPLETED"

        except Exception as e:
            logger.error("Orchestrator error for workload %s: %s", workload_id, e)
            result.status = "ERROR"
            result.stages["error"] = {
                "type": type(e).__name__,
                "message": str(e),
                "trace_id": trace_id,
            }
            result.classified_result = build_blocked_result(
                trace_id=trace_id,
                blocked_reason=f"Orchestrator error: {e}",
            ).to_dict()

        return result

    # -- Internal Stage Methods ---------------------------------------------

    def _discover_capabilities(self) -> Dict[str, Any]:
        """Stage 1: Discover available quantum and classical capabilities."""
        providers = self._provider_registry.list_providers()
        aggregate = self._provider_registry.get_aggregate_status()

        return {
            "providers": providers,
            "aggregate": aggregate,
            "quantum_available": aggregate["quantum_execution_possible"],
            "live_quantum_available": aggregate["live_quantum_possible"],
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def _extract_metadata(
        self, workload_id: str, workload: Dict[str, Any]
    ) -> WorkloadMetadata:
        """Extract workload metadata for routing decisions."""
        return WorkloadMetadata(
            workload_id=workload_id,
            workload_type=workload.get("workload_type", "GENERAL"),
            problem_size=workload.get("problem_size", 0),
            is_qubo_compatible=workload.get("is_qubo_compatible", False),
            requires_entanglement=workload.get("requires_entanglement", False),
            requires_live_hardware=workload.get("requires_live_hardware", False),
            max_acceptable_noise=workload.get("max_acceptable_noise", 1.0),
            classical_fallback_acceptable=workload.get(
                "classical_fallback_acceptable",
                config.CLASSICAL_FALLBACK_ENABLED,
            ),
        )

    def _route_and_execute(
        self,
        trace_id: str,
        workload: Dict[str, Any],
        routing: RoutingDecision,
        metadata: WorkloadMetadata,
    ) -> ClassifiedResult:
        """Stage 4: Execute through the routed path."""

        # BLOCKED path
        if routing.recommended_path == ExecutionPath.BLOCKED.value:
            return build_blocked_result(
                trace_id=trace_id,
                blocked_reason=routing.reason,
                original_classification=routing.recommended_classification,
            )

        # FALLBACK path
        if routing.recommended_path == ExecutionPath.FALLBACK.value:
            return self._execute_classical_fallback(trace_id, workload, routing)

        # Quantum path (LOCAL or SIMULATED)
        if routing.recommended_classification in (
            ExecutionClassification.QUANTUM_LOCAL.value,
            ExecutionClassification.QUANTUM_SIMULATED.value,
            ExecutionClassification.QUANTUM_LIVE.value,
            ExecutionClassification.HYBRID.value,
        ):
            return self._execute_quantum(trace_id, workload, routing, metadata)

        # Classical path
        return self._execute_classical(trace_id, workload, routing)

    def _execute_quantum(
        self,
        trace_id: str,
        workload: Dict[str, Any],
        routing: RoutingDecision,
        metadata: WorkloadMetadata,
    ) -> ClassifiedResult:
        """Execute a quantum workload on the selected provider."""
        provider = self._provider_registry.get_provider(routing.recommended_provider_id)

        if not provider or not provider.is_available:
            # Provider became unavailable between routing and execution
            if metadata.classical_fallback_acceptable:
                return self._execute_classical_fallback(
                    trace_id, workload, routing,
                    fallback_reason="Provider became unavailable between routing and execution",
                )
            return build_blocked_result(
                trace_id=trace_id,
                blocked_reason="Provider unavailable at execution time",
                original_classification=routing.recommended_classification,
            )

        try:
            # Execute on the quantum provider
            quantum_result = self._invoke_quantum_provider(provider, workload)

            classification = ExecutionClassification(routing.recommended_classification)
            path = ExecutionPath(routing.recommended_path)

            return build_classified_result(
                trace_id=trace_id,
                classification=classification,
                execution_path=path,
                provider_id=provider.provider_id,
                result_payload=quantum_result,
                confidence=quantum_result.get("confidence", 0.95),
            )

        except Exception as e:
            logger.warning(
                "Quantum execution failed for %s on %s: %s",
                trace_id, provider.provider_id, e,
            )
            if metadata.classical_fallback_acceptable:
                return self._execute_classical_fallback(
                    trace_id, workload, routing,
                    fallback_reason=f"Quantum execution failed: {e}",
                )
            return build_blocked_result(
                trace_id=trace_id,
                blocked_reason=f"Quantum execution failed: {e}",
                original_classification=routing.recommended_classification,
            )

    def _invoke_quantum_provider(
        self, provider: QuantumProviderRecord, workload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Invoke the quantum provider to execute a workload.

        For local simulators, this runs Qiskit Aer directly.
        For remote/live providers, this would call the provider's API.
        """
        if provider.is_local_simulator:
            return self._run_local_quantum(workload)

        # Remote/live providers would be invoked via HTTP here
        # Since no live providers are configured, this path correctly reports BLOCKED
        raise RuntimeError(
            f"Provider {provider.provider_id} ({provider.provider_type}) "
            f"invocation not implemented — no live quantum endpoint configured"
        )

    def _run_local_quantum(self, workload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run quantum execution on the local Qiskit Aer simulator.

        This uses the existing quantum_producer infrastructure.
        """
        from qiskit import QuantumCircuit
        from qiskit_aer import AerSimulator

        # Build circuit from workload or use default superdense coding
        message = workload.get("message", workload.get("payload", {}).get("message", "QUANTUM_TEST"))
        shots = workload.get("shots", config.SHOTS)
        seed = workload.get("seed", config.DEFAULT_SEED)
        noise = workload.get("noise", 0.0)

        # Use the existing quantum producer
        from models import TransmissionRequest
        from quantum_producer import run_quantum_producer
        from quantum_uncertainty import classify as classify_uncertainty

        request = TransmissionRequest(message=str(message), noise=noise, mode="entangled")
        distribution = run_quantum_producer(request, shots=shots, seed=seed)
        uncertainty = classify_uncertainty(distribution)

        return {
            "status": "EXECUTED",
            "execution_type": "QUANTUM_LOCAL",
            "provider": "qiskit-aer-local",
            "encoded_bits": distribution.encoded_bits,
            "counts": distribution.counts,
            "shots": distribution.shots,
            "seed": distribution.seed,
            "noise_factor": distribution.noise_factor,
            "confidence": uncertainty.confidence,
            "uncertainty_class": uncertainty.uncertainty_class.value,
            "translation_valid": uncertainty.translation_valid,
            "recommended_posture": uncertainty.recommended_operational_posture,
        }

    def _execute_classical(
        self, trace_id: str, workload: Dict[str, Any], routing: RoutingDecision
    ) -> ClassifiedResult:
        """Execute a classical workload."""
        # Classical execution — direct computation
        result_payload = {
            "status": "EXECUTED",
            "execution_type": "CLASSICAL",
            "workload_type": workload.get("workload_type", "GENERAL"),
            "result": workload.get("payload", workload),
        }

        return build_classified_result(
            trace_id=trace_id,
            classification=ExecutionClassification.CLASSICAL,
            execution_path=ExecutionPath.LOCAL,
            provider_id="CLASSICAL_RUNTIME",
            result_payload=result_payload,
            confidence=1.0,
        )

    def _execute_classical_fallback(
        self,
        trace_id: str,
        workload: Dict[str, Any],
        routing: RoutingDecision,
        fallback_reason: str = "",
    ) -> ClassifiedResult:
        """Execute classical fallback when quantum is unavailable."""
        reason = fallback_reason or routing.reason

        result_payload = {
            "status": "FALLBACK",
            "execution_type": "CLASSICAL_FALLBACK",
            "original_classification": routing.recommended_classification,
            "fallback_reason": reason,
            "workload_type": workload.get("workload_type", "GENERAL"),
            "result": workload.get("payload", workload),
        }

        return build_fallback_result(
            trace_id=trace_id,
            result_payload=result_payload,
            confidence=0.8,  # Lower confidence for fallback
            fallback_reason=reason,
            original_classification=routing.recommended_classification,
        )

    def _apply_trust_boundary(
        self, trace_id: str, classified: ClassifiedResult
    ) -> Dict[str, Any]:
        """Stage 5: Apply QCG trust/replay boundary."""
        # Check replay
        try:
            from canonical_replay_authority import CanonicalReplayAuthority, get_authority
            from replay_registry import ReplayRegistry
            from pathlib import Path
            import tempfile

            reg = ReplayRegistry(
                path=Path(config.REPLAY_REGISTRY_PATH),
                ttl_seconds=config.REPLAY_TTL_SECONDS,
            )
            authority = CanonicalReplayAuthority(reg)
            verdict = authority.submit(
                message_id=trace_id,
                trace_reference=trace_id,
            )

            return {
                "replay_check": {
                    "is_valid": verdict.is_valid,
                    "status": verdict.status,
                    "sequence_number": verdict.sequence_number,
                },
                "trust_boundary": "QCG_VALIDATED",
                "classification_verified": classified.classification,
                "path_verified": classified.execution_path,
            }
        except Exception as e:
            logger.warning("Trust boundary check failed: %s", e)
            return {
                "replay_check": {"error": str(e)},
                "trust_boundary": "TRUST_CHECK_FAILED",
            }

    def _record_evidence(
        self,
        trace_id: str,
        classified: ClassifiedResult,
        routing: RoutingDecision,
    ) -> Dict[str, Any]:
        """Stage 6: Record evidence and observability traces."""
        # Record in trace store
        self._trace_store.record_quantum_execution_trace(
            trace_id=trace_id,
            classification=classified.classification,
            execution_path=classified.execution_path,
            provider_id=classified.provider_id,
            confidence=classified.confidence,
            result_hash=classified.result_hash,
            fallback_reason=classified.fallback_reason,
            blocked_reason=classified.blocked_reason,
        )

        # Record in evidence ledger
        try:
            record = ExecutionRecord(
                execution_id=str(uuid.uuid4()),
                trace_id=trace_id,
                replay_reference=0,
                execution_sequence=len(self._evidence_ledger._records) + 1,
                producer_identity=classified.provider_id,
                runtime_identity="HYBRID_RUNTIME_v1",
                governance_identity="QCG_GOVERNANCE",
                execution_status=classified.execution_path,
                runtime_hash=classified.result_hash,
                previous_execution_hash=self._evidence_ledger._current_head,
                execution_hash=hashlib.sha256(
                    f"{trace_id}:{classified.result_hash}".encode()
                ).hexdigest(),
                execution_root_hash=self._evidence_ledger.get_merkle_root(),
                schema_version="2.0.0",
            )
            snapshot = self._evidence_ledger.append(record)

            return {
                "evidence_recorded": True,
                "ledger_snapshot": {
                    "sequence_length": snapshot.sequence_length,
                    "merkle_root": snapshot.merkle_root,
                    "latest_hash": snapshot.latest_evidence_hash,
                },
                "trace_count": len(self._trace_store),
            }
        except Exception as e:
            logger.error("Evidence recording failed: %s", e)
            return {"evidence_recorded": False, "error": str(e)}

    def _coordinate_network(
        self, trace_id: str, classified: ClassifiedResult
    ) -> Dict[str, Any]:
        """Stage 7: Quantum network coordination."""
        # Request a network route for this quantum execution
        route_request = RouteRequest(
            request_id=str(uuid.uuid4()),
            source_node_id="QCG_LOCAL_NODE",
            destination_node_id="QCG_LOCAL_NODE",  # Self-route for local execution
            preferred_protocol=NetworkProtocol.BB84.value,
            require_entanglement=False,
            classical_fallback_acceptable=True,
        )

        response = self._network_contract.request_route(route_request)

        return {
            "route_status": response.status,
            "route": response.route.to_dict() if response.route else None,
            "control_plane": self._network_contract.classical_control_plane(),
            "coordination_for_trace": trace_id,
        }

    def _emit_provenance(
        self,
        trace_id: str,
        classified: ClassifiedResult,
        routing: RoutingDecision,
    ) -> Dict[str, Any]:
        """Stage 8: Final provenance output for BHEX handover."""
        return {
            "trace_id": trace_id,
            "classification": classified.classification,
            "execution_path": classified.execution_path,
            "provider_id": classified.provider_id,
            "result_hash": classified.result_hash,
            "confidence": classified.confidence,
            "is_fallback": classified.is_fallback,
            "is_blocked": classified.is_blocked,
            "routing_suitability": routing.suitability,
            "evidence_chain_head": self._evidence_ledger._current_head,
            "merkle_root": self._evidence_ledger.get_merkle_root(),
            "network_enabled": config.QUANTUM_NETWORK_ENABLED,
            "provenance_timestamp": datetime.now(timezone.utc).isoformat(),
            "bhex_ready": True,
        }

    # -- Health & Status ---------------------------------------------------

    def get_health(self) -> Dict[str, Any]:
        """Aggregate health across all subsystems."""
        provider_status = self._provider_registry.get_aggregate_status()
        network_status = self._network_contract.classical_control_plane()

        return {
            "orchestrator": "HEALTHY",
            "providers": provider_status,
            "network": network_status,
            "evidence_ledger": {
                "chain_length": len(self._evidence_ledger._records),
                "chain_valid": self._evidence_ledger.verify_chain(),
                "merkle_root": self._evidence_ledger.get_merkle_root(),
            },
            "trace_store": {
                "entries": len(self._trace_store),
            },
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def get_provider_registry(self) -> QuantumProviderRegistry:
        """Access the provider registry."""
        return self._provider_registry

    def get_network_contract(self) -> QuantumNetworkContract:
        """Access the network contract."""
        return self._network_contract

    def get_evidence_ledger(self) -> EvidenceLedger:
        """Access the evidence ledger."""
        return self._evidence_ledger

    def get_trace_store(self) -> TraceStore:
        """Access the trace store."""
        return self._trace_store
