"""
quantum_provider_registry.py — Quantum Provider Registry & Health Monitoring

Canonical registry for quantum execution providers. Every quantum provider
must register here before it can receive workloads. The registry tracks
provider health, capabilities, and execution classification.

RESPONSIBILITY BOUNDARY
-----------------------
QuantumProviderRegistry OWNS:
    - Provider registration and deregistration
    - Provider health checking and status tracking
    - Provider capability discovery
    - Best-provider selection for a given workload
    - Provider classification (local simulator vs remote vs live hardware)

QuantumProviderRegistry does NOT OWN:
    - Workload suitability decisions       → WorkloadRouter
    - Execution routing                    → HybridRuntimeOrchestrator
    - Trust/governance                     → GovernanceLayer
    - Quantum execution itself             → Provider implementations
"""

from __future__ import annotations

import hashlib
import json
import logging
import threading
import time
import uuid
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from execution_classification import (
    ExecutionClassification,
    ExecutionPath,
    ProviderStatus,
)

logger = logging.getLogger("qcg.quantum_provider_registry")


# ---------------------------------------------------------------------------
# Provider Record
# ---------------------------------------------------------------------------

@dataclass
class QuantumProviderRecord:
    """
    Describes a registered quantum execution provider.

    Each provider declares its type (local simulator, remote simulator,
    live hardware), capabilities, health endpoint, and current status.
    """
    provider_id: str
    provider_name: str
    provider_type: str                      # LOCAL_SIMULATOR | REMOTE_SIMULATOR | LIVE_HARDWARE
    status: str = ProviderStatus.UNKNOWN.value
    capabilities: Dict[str, Any] = field(default_factory=dict)
    health_endpoint: str = ""
    max_qubits: int = 0
    supported_gates: List[str] = field(default_factory=list)
    noise_model: str = ""
    backend_name: str = ""
    last_health_check: str = ""
    last_health_result: str = ""
    registered_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> dict:
        return asdict(self)

    @property
    def is_local_simulator(self) -> bool:
        return self.provider_type == "LOCAL_SIMULATOR"

    @property
    def is_remote_simulator(self) -> bool:
        return self.provider_type == "REMOTE_SIMULATOR"

    @property
    def is_live_hardware(self) -> bool:
        return self.provider_type == "LIVE_HARDWARE"

    @property
    def is_available(self) -> bool:
        return self.status in (ProviderStatus.AVAILABLE.value, ProviderStatus.DEGRADED.value)

    def get_execution_classification(self) -> ExecutionClassification:
        """Map provider type to execution classification."""
        if self.is_live_hardware:
            return ExecutionClassification.QUANTUM_LIVE
        elif self.is_remote_simulator:
            return ExecutionClassification.QUANTUM_SIMULATED
        elif self.is_local_simulator:
            return ExecutionClassification.QUANTUM_LOCAL
        return ExecutionClassification.CLASSICAL


# ---------------------------------------------------------------------------
# Provider Registry
# ---------------------------------------------------------------------------

class QuantumProviderRegistry:
    """
    Thread-safe registry of quantum execution providers.

    Providers register with their capabilities and type. The registry
    monitors health and provides discovery for workload routing.
    """

    def __init__(self):
        self._providers: Dict[str, QuantumProviderRecord] = {}
        self._lock = threading.Lock()
        self._health_history: List[Dict[str, Any]] = []

        # Auto-register the default local Qiskit Aer simulator
        self._register_default_local_simulator()

    def _register_default_local_simulator(self):
        """Register the built-in Qiskit Aer local simulator."""
        try:
            from qiskit_aer import AerSimulator
            record = QuantumProviderRecord(
                provider_id="qiskit-aer-local",
                provider_name="Qiskit Aer Local Simulator",
                provider_type="LOCAL_SIMULATOR",
                status=ProviderStatus.AVAILABLE.value,
                capabilities={
                    "simulation_methods": ["statevector", "density_matrix", "stabilizer"],
                    "noise_support": True,
                    "max_shots": 100_000,
                },
                max_qubits=30,
                supported_gates=["h", "x", "y", "z", "cx", "cz", "ccx", "swap", "rx", "ry", "rz"],
                noise_model="configurable",
                backend_name="aer_simulator",
            )
            self._providers[record.provider_id] = record
            logger.info("Registered default local simulator: %s", record.provider_id)
        except ImportError:
            logger.warning("Qiskit Aer not available — no default local simulator registered")

    # -- Registration -------------------------------------------------------

    def register_provider(self, record: QuantumProviderRecord) -> bool:
        """
        Register a quantum provider. Returns True if newly registered,
        False if updated an existing registration.
        """
        with self._lock:
            is_new = record.provider_id not in self._providers
            self._providers[record.provider_id] = record
            logger.info(
                "%s quantum provider: %s (%s)",
                "Registered" if is_new else "Updated",
                record.provider_id,
                record.provider_type,
            )
            return is_new

    def deregister_provider(self, provider_id: str) -> bool:
        """Remove a provider from the registry."""
        with self._lock:
            if provider_id in self._providers:
                del self._providers[provider_id]
                logger.info("Deregistered provider: %s", provider_id)
                return True
            return False

    # -- Discovery ----------------------------------------------------------

    def get_provider(self, provider_id: str) -> Optional[QuantumProviderRecord]:
        """Get a specific provider by ID."""
        with self._lock:
            return self._providers.get(provider_id)

    def list_providers(self) -> List[Dict[str, Any]]:
        """List all registered providers."""
        with self._lock:
            return [p.to_dict() for p in self._providers.values()]

    def list_available_providers(self) -> List[QuantumProviderRecord]:
        """List only available (healthy) providers."""
        with self._lock:
            return [p for p in self._providers.values() if p.is_available]

    def get_best_provider(
        self,
        min_qubits: int = 0,
        prefer_live: bool = True,
    ) -> Optional[QuantumProviderRecord]:
        """
        Select the best available provider for a workload.

        Priority order (when prefer_live=True):
          1. LIVE_HARDWARE (AVAILABLE)
          2. REMOTE_SIMULATOR (AVAILABLE)
          3. LOCAL_SIMULATOR (AVAILABLE)
          4. Any DEGRADED provider
          5. None (all unavailable)

        When prefer_live=False, local simulators are preferred.
        """
        with self._lock:
            available = [
                p for p in self._providers.values()
                if p.is_available and p.max_qubits >= min_qubits
            ]

        if not available:
            return None

        # Sort by preference
        type_priority = {
            "LIVE_HARDWARE": 0 if prefer_live else 2,
            "REMOTE_SIMULATOR": 1,
            "LOCAL_SIMULATOR": 2 if prefer_live else 0,
        }
        status_priority = {
            ProviderStatus.AVAILABLE.value: 0,
            ProviderStatus.DEGRADED.value: 1,
        }

        available.sort(key=lambda p: (
            type_priority.get(p.provider_type, 99),
            status_priority.get(p.status, 99),
        ))

        return available[0] if available else None

    # -- Health Checking ----------------------------------------------------

    def check_provider_health(self, provider_id: str) -> Dict[str, Any]:
        """
        Check health of a specific provider.

        For local simulators, this verifies the import is available.
        For remote/live providers, this would check the health endpoint.
        """
        provider = self.get_provider(provider_id)
        if not provider:
            return {
                "provider_id": provider_id,
                "status": ProviderStatus.UNKNOWN.value,
                "error": "Provider not registered",
            }

        health_result = {
            "provider_id": provider_id,
            "checked_at": datetime.now(timezone.utc).isoformat(),
        }

        if provider.is_local_simulator:
            try:
                from qiskit_aer import AerSimulator
                health_result["status"] = ProviderStatus.AVAILABLE.value
                health_result["detail"] = "Local Aer simulator available"
            except ImportError:
                health_result["status"] = ProviderStatus.UNAVAILABLE.value
                health_result["detail"] = "Qiskit Aer not installed"
        elif provider.health_endpoint:
            # For remote providers, attempt HTTP health check
            try:
                import urllib.request
                with urllib.request.urlopen(provider.health_endpoint, timeout=5) as resp:
                    if resp.status == 200:
                        health_result["status"] = ProviderStatus.AVAILABLE.value
                        health_result["detail"] = "Health endpoint returned 200"
                    else:
                        health_result["status"] = ProviderStatus.DEGRADED.value
                        health_result["detail"] = f"Health endpoint returned {resp.status}"
            except Exception as e:
                health_result["status"] = ProviderStatus.UNAVAILABLE.value
                health_result["detail"] = f"Health check failed: {e}"
        else:
            health_result["status"] = ProviderStatus.UNKNOWN.value
            health_result["detail"] = "No health endpoint configured"

        # Update provider status
        with self._lock:
            if provider_id in self._providers:
                self._providers[provider_id].status = health_result["status"]
                self._providers[provider_id].last_health_check = health_result["checked_at"]
                self._providers[provider_id].last_health_result = health_result["status"]

        self._health_history.append(health_result)
        return health_result

    def check_all_health(self) -> List[Dict[str, Any]]:
        """Check health of all registered providers."""
        with self._lock:
            provider_ids = list(self._providers.keys())
        return [self.check_provider_health(pid) for pid in provider_ids]

    # -- Aggregate Status ---------------------------------------------------

    def get_aggregate_status(self) -> Dict[str, Any]:
        """Get aggregate status of the quantum provider ecosystem."""
        with self._lock:
            providers = list(self._providers.values())

        total = len(providers)
        available = sum(1 for p in providers if p.status == ProviderStatus.AVAILABLE.value)
        degraded = sum(1 for p in providers if p.status == ProviderStatus.DEGRADED.value)
        unavailable = sum(1 for p in providers if p.status == ProviderStatus.UNAVAILABLE.value)
        unknown = sum(1 for p in providers if p.status == ProviderStatus.UNKNOWN.value)
        live_hw = sum(1 for p in providers if p.is_live_hardware and p.is_available)

        return {
            "total_providers": total,
            "available": available,
            "degraded": degraded,
            "unavailable": unavailable,
            "unknown": unknown,
            "live_hardware_available": live_hw,
            "quantum_execution_possible": available > 0,
            "live_quantum_possible": live_hw > 0,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
