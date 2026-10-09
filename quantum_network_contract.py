"""
quantum_network_contract.py — Quantum Network Coordination Contract

Defines the integration surface for quantum-network participation.
This module provides protocol-ready contracts for quantum node
coordination, route negotiation, and distributed quantum communication.

This is a COORDINATION layer, not a simulation of quantum physics.
It defines how quantum nodes declare capabilities, negotiate routes,
and participate in distributed quantum operations through explicit
contracts.

RESPONSIBILITY BOUNDARY
-----------------------
QuantumNetworkContract OWNS:
    - Network node declaration and discovery
    - Route request and validation
    - Classical control plane for quantum operations
    - Network status reporting
    - Protocol capability advertisement

QuantumNetworkContract does NOT OWN:
    - Quantum computation            → QuantumProducer / RuntimeCore
    - Execution governance           → GovernanceLayer
    - Trust/authentication           → TrustChain / TrustProvider
    - Provider health                → QuantumProviderRegistry
    - Entanglement physics           → Future quantum hardware drivers

CRITICAL RULE: The quantum network layer coordinates; it does NOT
silently inherit execution legitimacy. A network contract proving
a route exists does NOT prove an execution occurred on that route.
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
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger("qcg.quantum_network")


# ---------------------------------------------------------------------------
# Network Node Status
# ---------------------------------------------------------------------------

class NetworkNodeStatus(str, Enum):
    """Status of a quantum network node."""
    ACTIVE = "ACTIVE"
    DEGRADED = "DEGRADED"
    OFFLINE = "OFFLINE"
    UNKNOWN = "UNKNOWN"


class NetworkRouteStatus(str, Enum):
    """Status of a quantum network route."""
    LIVE = "LIVE"               # Real quantum link established
    LOCAL = "LOCAL"             # Local simulation of quantum link
    SIMULATED = "SIMULATED"    # Full simulation (no quantum hardware)
    BLOCKED = "BLOCKED"        # Route cannot be established
    NEGOTIATING = "NEGOTIATING"  # Route negotiation in progress


class NetworkProtocol(str, Enum):
    """Supported quantum network protocols."""
    BB84 = "BB84"
    E91 = "E91"
    ENTANGLEMENT_SWAPPING = "ENTANGLEMENT_SWAPPING"
    CLASSICAL_CONTROL = "CLASSICAL_CONTROL"


# ---------------------------------------------------------------------------
# Network Node
# ---------------------------------------------------------------------------

@dataclass
class QuantumNetworkNode:
    """
    Represents a participant in the quantum network.

    Each node declares its quantum capabilities, classical control
    endpoint, and network status. Nodes must register before they
    can participate in route negotiation.
    """
    node_id: str
    node_name: str
    capabilities: List[str] = field(default_factory=list)  # e.g., ["QKD", "ENTANGLEMENT", "TELEPORTATION"]
    supported_protocols: List[str] = field(default_factory=list)
    classical_control_endpoint: str = ""
    network_status: str = NetworkNodeStatus.UNKNOWN.value
    max_entanglement_pairs: int = 0
    qubit_coherence_time_us: float = 0.0   # microseconds
    registered_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> dict:
        return asdict(self)


# ---------------------------------------------------------------------------
# Network Route
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class QuantumNetworkRoute:
    """
    Describes a quantum communication route between two nodes.

    Each route carries its status (LIVE/LOCAL/SIMULATED/BLOCKED),
    the protocol used, and whether a classical fallback exists.
    """
    route_id: str
    source_node_id: str
    destination_node_id: str
    protocol: str
    status: str
    classical_fallback_available: bool = True
    entanglement_fidelity: float = 0.0     # 0.0 to 1.0
    estimated_latency_ms: float = 0.0
    route_hash: str = ""
    established_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def __post_init__(self):
        if not self.route_hash:
            raw = json.dumps({
                "route_id": self.route_id,
                "source": self.source_node_id,
                "destination": self.destination_node_id,
                "protocol": self.protocol,
                "status": self.status,
            }, sort_keys=True)
            object.__setattr__(
                self, "route_hash",
                hashlib.sha256(raw.encode()).hexdigest()
            )

    def to_dict(self) -> dict:
        return asdict(self)


# ---------------------------------------------------------------------------
# Route Request / Response
# ---------------------------------------------------------------------------

@dataclass
class RouteRequest:
    """Request to establish a quantum network route."""
    request_id: str
    source_node_id: str
    destination_node_id: str
    preferred_protocol: str = NetworkProtocol.BB84.value
    require_entanglement: bool = False
    min_fidelity: float = 0.0
    classical_fallback_acceptable: bool = True

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class RouteResponse:
    """Response to a route request."""
    request_id: str
    route: Optional[QuantumNetworkRoute] = None
    status: str = "PENDING"
    reason: str = ""
    alternatives: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict:
        result = {
            "request_id": self.request_id,
            "status": self.status,
            "reason": self.reason,
            "alternatives": self.alternatives,
        }
        if self.route:
            result["route"] = self.route.to_dict()
        return result


# ---------------------------------------------------------------------------
# Quantum Network Contract
# ---------------------------------------------------------------------------

class QuantumNetworkContract:
    """
    Coordination contract for quantum network operations.

    This is the central integration surface for quantum networking.
    It manages node registration, route negotiation, and provides
    the classical control plane for quantum communication operations.

    IMPORTANT: This module coordinates; it does NOT execute.
    A valid route contract means "communication CAN occur on this path."
    It does NOT mean "quantum computation has occurred."
    """

    def __init__(self):
        self._nodes: Dict[str, QuantumNetworkNode] = {}
        self._routes: Dict[str, QuantumNetworkRoute] = {}
        self._lock = threading.Lock()
        self._route_history: List[Dict[str, Any]] = []

    # -- Node Management ----------------------------------------------------

    def declare_node(self, node: QuantumNetworkNode) -> Dict[str, Any]:
        """
        Register a quantum network participant.

        Every node must declare before participating in route negotiation.
        """
        with self._lock:
            is_new = node.node_id not in self._nodes
            self._nodes[node.node_id] = node

        logger.info(
            "%s network node: %s (capabilities: %s)",
            "Declared" if is_new else "Updated",
            node.node_id,
            node.capabilities,
        )
        return {
            "status": "DECLARED" if is_new else "UPDATED",
            "node_id": node.node_id,
            "network_status": node.network_status,
        }

    def get_node(self, node_id: str) -> Optional[QuantumNetworkNode]:
        """Look up a node by ID."""
        with self._lock:
            return self._nodes.get(node_id)

    def list_nodes(self) -> List[Dict[str, Any]]:
        """List all declared nodes."""
        with self._lock:
            return [n.to_dict() for n in self._nodes.values()]

    # -- Route Negotiation --------------------------------------------------

    def request_route(self, request: RouteRequest) -> RouteResponse:
        """
        Request a quantum communication route between two nodes.

        The contract validates both nodes exist, checks capabilities,
        and determines the route status (LIVE/LOCAL/SIMULATED/BLOCKED).
        """
        with self._lock:
            source = self._nodes.get(request.source_node_id)
            destination = self._nodes.get(request.destination_node_id)

        # Validate nodes exist
        if not source:
            return RouteResponse(
                request_id=request.request_id,
                status="BLOCKED",
                reason=f"Source node '{request.source_node_id}' not declared",
            )

        if not destination:
            return RouteResponse(
                request_id=request.request_id,
                status="BLOCKED",
                reason=f"Destination node '{request.destination_node_id}' not declared",
            )

        # Check node status
        if source.network_status == NetworkNodeStatus.OFFLINE.value:
            return RouteResponse(
                request_id=request.request_id,
                status="BLOCKED",
                reason=f"Source node '{source.node_id}' is OFFLINE",
            )

        if destination.network_status == NetworkNodeStatus.OFFLINE.value:
            return RouteResponse(
                request_id=request.request_id,
                status="BLOCKED",
                reason=f"Destination node '{destination.node_id}' is OFFLINE",
            )

        # Check protocol compatibility
        if request.preferred_protocol not in source.supported_protocols:
            if request.classical_fallback_acceptable:
                return self._create_classical_fallback_route(request, source, destination)
            return RouteResponse(
                request_id=request.request_id,
                status="BLOCKED",
                reason=f"Source node does not support protocol '{request.preferred_protocol}'",
            )

        if request.preferred_protocol not in destination.supported_protocols:
            if request.classical_fallback_acceptable:
                return self._create_classical_fallback_route(request, source, destination)
            return RouteResponse(
                request_id=request.request_id,
                status="BLOCKED",
                reason=f"Destination node does not support protocol '{request.preferred_protocol}'",
            )

        # Determine route status based on node capabilities
        route_status = self._determine_route_status(source, destination, request)

        route = QuantumNetworkRoute(
            route_id=str(uuid.uuid4()),
            source_node_id=source.node_id,
            destination_node_id=destination.node_id,
            protocol=request.preferred_protocol,
            status=route_status.value,
            classical_fallback_available=request.classical_fallback_acceptable,
            entanglement_fidelity=min(
                source.qubit_coherence_time_us / 1000.0,  # normalized
                1.0,
            ) if source.qubit_coherence_time_us > 0 else 0.5,
        )

        with self._lock:
            self._routes[route.route_id] = route
            self._route_history.append({
                "request": request.to_dict(),
                "route": route.to_dict(),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })

        return RouteResponse(
            request_id=request.request_id,
            route=route,
            status=route_status.value,
            reason=f"Route established via {request.preferred_protocol}",
        )

    def validate_route(self, route_id: str) -> Dict[str, Any]:
        """
        Validate that an established route is still viable.
        """
        with self._lock:
            route = self._routes.get(route_id)

        if not route:
            return {"valid": False, "reason": "Route not found"}

        source = self.get_node(route.source_node_id)
        destination = self.get_node(route.destination_node_id)

        if not source or source.network_status == NetworkNodeStatus.OFFLINE.value:
            return {"valid": False, "reason": "Source node offline or removed"}

        if not destination or destination.network_status == NetworkNodeStatus.OFFLINE.value:
            return {"valid": False, "reason": "Destination node offline or removed"}

        return {
            "valid": True,
            "route_id": route_id,
            "status": route.status,
            "source": route.source_node_id,
            "destination": route.destination_node_id,
        }

    def get_route_status(self, route_id: str) -> str:
        """Get the current status of a route."""
        with self._lock:
            route = self._routes.get(route_id)
        return route.status if route else NetworkRouteStatus.BLOCKED.value

    # -- Classical Control Plane --------------------------------------------

    def classical_control_plane(self) -> Dict[str, Any]:
        """
        Return the classical control plane status.

        The classical control plane is always available — it's the
        coordination layer that manages quantum operations.
        """
        with self._lock:
            active_nodes = sum(
                1 for n in self._nodes.values()
                if n.network_status == NetworkNodeStatus.ACTIVE.value
            )
            active_routes = sum(
                1 for r in self._routes.values()
                if r.status in (NetworkRouteStatus.LIVE.value, NetworkRouteStatus.LOCAL.value)
            )

        return {
            "status": "ACTIVE",
            "total_nodes": len(self._nodes),
            "active_nodes": active_nodes,
            "total_routes": len(self._routes),
            "active_routes": active_routes,
            "protocols_available": [p.value for p in NetworkProtocol],
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    # -- Network Status -----------------------------------------------------

    def get_network_status(self) -> Dict[str, Any]:
        """
        Comprehensive network status including all nodes and routes.
        """
        control = self.classical_control_plane()
        with self._lock:
            nodes = [n.to_dict() for n in self._nodes.values()]
            routes = [r.to_dict() for r in self._routes.values()]

        return {
            "control_plane": control,
            "nodes": nodes,
            "routes": routes,
            "route_history_length": len(self._route_history),
        }

    # -- Internal -----------------------------------------------------------

    def _determine_route_status(
        self,
        source: QuantumNetworkNode,
        destination: QuantumNetworkNode,
        request: RouteRequest,
    ) -> NetworkRouteStatus:
        """
        Determine the status of a route based on node capabilities.

        Since we have no live quantum network hardware, all routes are
        classified honestly:
        - Both nodes ACTIVE with quantum capabilities → LOCAL (local simulation)
        - Any node DEGRADED → SIMULATED
        - Otherwise → BLOCKED
        """
        if (source.network_status == NetworkNodeStatus.ACTIVE.value and
                destination.network_status == NetworkNodeStatus.ACTIVE.value):
            # Both active — we can simulate locally
            return NetworkRouteStatus.LOCAL

        if (source.network_status == NetworkNodeStatus.DEGRADED.value or
                destination.network_status == NetworkNodeStatus.DEGRADED.value):
            return NetworkRouteStatus.SIMULATED

        return NetworkRouteStatus.BLOCKED

    def _create_classical_fallback_route(
        self,
        request: RouteRequest,
        source: QuantumNetworkNode,
        destination: QuantumNetworkNode,
    ) -> RouteResponse:
        """Create a classical fallback route when quantum is not possible."""
        route = QuantumNetworkRoute(
            route_id=str(uuid.uuid4()),
            source_node_id=source.node_id,
            destination_node_id=destination.node_id,
            protocol=NetworkProtocol.CLASSICAL_CONTROL.value,
            status=NetworkRouteStatus.LOCAL.value,
            classical_fallback_available=True,
        )

        with self._lock:
            self._routes[route.route_id] = route

        return RouteResponse(
            request_id=request.request_id,
            route=route,
            status="FALLBACK",
            reason="Quantum protocol not supported; using classical control plane",
        )


# ---------------------------------------------------------------------------
# Entanglement Resource Management (Phase 4: Quantum Networking)
# ---------------------------------------------------------------------------

@dataclass
class EntanglementPair:
    """
    Represents an EPR / Bell pair established between two network nodes.

    Includes initial fidelity, exponential decoherence decay modeling,
    and consumption tracking.
    """
    pair_id: str
    node_a: str
    node_b: str
    initial_fidelity: float = 0.98
    created_at_timestamp: float = field(default_factory=lambda: time.time())
    coherence_time_ms: float = 150.0  # coherence window in milliseconds
    is_consumed: bool = False
    consumed_at: Optional[float] = None

    def get_current_fidelity(self, now: Optional[float] = None) -> float:
        """
        Calculate current entanglement fidelity under exponential decoherence decay.
        F(t) = 0.5 + (F_0 - 0.5) * exp(-dt / tau)  (approaches maximally mixed state 0.5).
        """
        if self.is_consumed:
            return 0.0
        current_time = now if now is not None else time.time()
        elapsed_ms = (current_time - self.created_at_timestamp) * 1000.0
        if elapsed_ms <= 0:
            return self.initial_fidelity
        if self.coherence_time_ms <= 0:
            return 0.5
        
        import math
        decay = math.exp(-elapsed_ms / self.coherence_time_ms)
        fidelity = 0.5 + (self.initial_fidelity - 0.5) * decay
        return max(0.5, min(1.0, fidelity))

    def is_expired(self, min_fidelity: float = 0.70, now: Optional[float] = None) -> bool:
        """Check if fidelity has decayed below threshold or pair is consumed."""
        if self.is_consumed:
            return True
        return self.get_current_fidelity(now) < min_fidelity

    def consume(self) -> bool:
        """Mark the entanglement pair as consumed."""
        if self.is_consumed:
            return False
        self.is_consumed = True
        self.consumed_at = time.time()
        return True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "pair_id": self.pair_id,
            "node_a": self.node_a,
            "node_b": self.node_b,
            "initial_fidelity": self.initial_fidelity,
            "current_fidelity": round(self.get_current_fidelity(), 4),
            "coherence_time_ms": self.coherence_time_ms,
            "is_consumed": self.is_consumed,
            "is_expired": self.is_expired(),
        }


class EntanglementPoolManager:
    """
    Manages pools of distributed entanglement pairs across network nodes.
    Supports allocation, reservation, consumption, and decoherence purging.
    """

    def __init__(self):
        self._pairs: Dict[str, EntanglementPair] = {}
        self._lock = threading.Lock()

    def generate_pairs(
        self,
        node_a: str,
        node_b: str,
        count: int = 1,
        initial_fidelity: float = 0.98,
        coherence_time_ms: float = 150.0,
    ) -> List[EntanglementPair]:
        """Generate and register Bell pairs between two nodes."""
        created = []
        with self._lock:
            for _ in range(count):
                pair = EntanglementPair(
                    pair_id=f"epr-{uuid.uuid4().hex[:12]}",
                    node_a=node_a,
                    node_b=node_b,
                    initial_fidelity=initial_fidelity,
                    created_at_timestamp=time.time(),
                    coherence_time_ms=coherence_time_ms,
                )
                self._pairs[pair.pair_id] = pair
                created.append(pair)
        return created

    def reserve_pair(
        self,
        node_a: str,
        node_b: str,
        min_fidelity: float = 0.70,
    ) -> Optional[EntanglementPair]:
        """Find and reserve a valid, unexpired pair between node_a and node_b."""
        with self._lock:
            now = time.time()
            candidates = [
                p for p in self._pairs.values()
                if not p.is_consumed
                and not p.is_expired(min_fidelity=min_fidelity, now=now)
                and ((p.node_a == node_a and p.node_b == node_b) or
                     (p.node_a == node_b and p.node_b == node_a))
            ]
            if not candidates:
                return None
            # Choose highest current fidelity
            candidates.sort(key=lambda p: p.get_current_fidelity(now), reverse=True)
            chosen = candidates[0]
            chosen.consume()
            return chosen

    def purge_expired(self, min_fidelity: float = 0.70) -> int:
        """Purge consumed and decohered pairs from memory."""
        with self._lock:
            now = time.time()
            to_remove = [
                pid for pid, p in self._pairs.items()
                if p.is_consumed or p.is_expired(min_fidelity, now)
            ]
            for pid in to_remove:
                del self._pairs[pid]
            return len(to_remove)

    def get_status(self) -> Dict[str, Any]:
        """Aggregate entanglement pool status."""
        with self._lock:
            total = len(self._pairs)
            available = sum(1 for p in self._pairs.values() if not p.is_consumed and not p.is_expired())
            consumed = sum(1 for p in self._pairs.values() if p.is_consumed)
            expired = total - available - consumed
            return {
                "total_pairs_tracked": total,
                "available_pairs": available,
                "consumed_pairs": consumed,
                "expired_pairs": max(0, expired),
            }


# ---------------------------------------------------------------------------
# Distributed Quantum Workloads & Measurement Aggregation
# ---------------------------------------------------------------------------

@dataclass
class DistributedQuantumWorkload:
    """Specification of a multi-node distributed quantum workload."""
    workload_id: str
    participating_nodes: List[str]
    protocol: str = NetworkProtocol.ENTANGLEMENT_SWAPPING.value
    sub_tasks: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    min_fidelity: float = 0.70
    max_latency_ms: float = 100.0
    classical_fallback_acceptable: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class DistributedMeasurementAggregator:
    """
    Combines distributed measurement histograms and partial bitstrings
    across multiple quantum network nodes into joint probability distributions.
    """

    @staticmethod
    def aggregate(
        measurements_per_node: Dict[str, Dict[str, int]],
        fidelity_weights: Optional[Dict[str, float]] = None,
    ) -> Dict[str, Any]:
        """
        Aggregate node-level measurement dictionaries:
        e.g., Node1: {"0": 500, "1": 500}, Node2: {"0": 480, "1": 520}
        Produces joint distribution {"00": ..., "01": ..., "10": ..., "11": ...}
        with normalized probabilities and Shannon entropy.
        """
        import math

        if not measurements_per_node:
            return {
                "joint_counts": {},
                "joint_probabilities": {},
                "total_shots": 0,
                "shannon_entropy": 0.0,
            }

        node_keys = list(measurements_per_node.keys())
        total_shots_per_node = {
            node: sum(counts.values()) or 1
            for node, counts in measurements_per_node.items()
        }

        # Calculate joint outcomes by Cartesian product of measurements
        joint_probabilities: Dict[str, float] = {}

        def _combine_probabilities(idx: int, prefix: str, current_prob: float):
            if idx == len(node_keys):
                joint_probabilities[prefix] = joint_probabilities.get(prefix, 0.0) + current_prob
                return
            node = node_keys[idx]
            counts = measurements_per_node[node]
            tot = total_shots_per_node[node]
            for bit, c in counts.items():
                p = c / tot
                _combine_probabilities(idx + 1, prefix + bit, current_prob * p)

        _combine_probabilities(0, "", 1.0)

        # Normalize probabilities and compute Shannon entropy
        prob_sum = sum(joint_probabilities.values()) or 1.0
        normalized = {k: round(v / prob_sum, 6) for k, v in joint_probabilities.items()}

        entropy = 0.0
        for p in normalized.values():
            if p > 0.0:
                entropy -= p * math.log2(p)

        representative_shots = min(total_shots_per_node.values()) if total_shots_per_node else 0
        joint_counts = {k: int(round(p * representative_shots)) for k, p in normalized.items()}

        return {
            "joint_counts": joint_counts,
            "joint_probabilities": normalized,
            "total_shots": representative_shots,
            "shannon_entropy": round(entropy, 4),
            "participating_nodes": node_keys,
        }


# Attach Entanglement Pool and Multi-Node Coordination to QuantumNetworkContract
def _contract_init_extension(original_init):
    def new_init(self, *args, **kwargs):
        original_init(self, *args, **kwargs)
        self._entanglement_pool = EntanglementPoolManager()
    return new_init

QuantumNetworkContract.__init__ = _contract_init_extension(QuantumNetworkContract.__init__)


def allocate_entanglement(
    self: QuantumNetworkContract,
    node_a: str,
    node_b: str,
    count: int = 1,
    initial_fidelity: float = 0.98,
    coherence_time_ms: float = 150.0,
) -> List[EntanglementPair]:
    """Generate entanglement pairs between two declared network nodes."""
    return self._entanglement_pool.generate_pairs(
        node_a=node_a,
        node_b=node_b,
        count=count,
        initial_fidelity=initial_fidelity,
        coherence_time_ms=coherence_time_ms,
    )

QuantumNetworkContract.allocate_entanglement = allocate_entanglement


def get_entanglement_status(self: QuantumNetworkContract) -> Dict[str, Any]:
    """Retrieve current entanglement pool metrics."""
    return self._entanglement_pool.get_status()

QuantumNetworkContract.get_entanglement_status = get_entanglement_status


def coordinate_distributed_workload(
    self: QuantumNetworkContract,
    workload: DistributedQuantumWorkload,
) -> Dict[str, Any]:
    """
    Coordinate a multi-node distributed quantum workload.
    Validates participating nodes, establishes pairwise quantum routes,
    reserves entanglement pairs (if protocol requires it), computes
    network latency, and aggregates distributed measurement outcomes.
    """
    trace_id = str(uuid.uuid4())
    nodes = workload.participating_nodes

    if len(nodes) < 2:
        return {
            "trace_id": trace_id,
            "workload_id": workload.workload_id,
            "status": "BLOCKED",
            "reason": "Multi-node workload requires at least 2 declared nodes",
        }

    # 1. Validate all nodes exist and are ACTIVE
    for nid in nodes:
        node = self.get_node(nid)
        if not node:
            return {
                "trace_id": trace_id,
                "workload_id": workload.workload_id,
                "status": "BLOCKED",
                "reason": f"Participating node '{nid}' not found in quantum network",
            }
        if node.network_status == NetworkNodeStatus.OFFLINE.value:
            return {
                "trace_id": trace_id,
                "workload_id": workload.workload_id,
                "status": "BLOCKED",
                "reason": f"Participating node '{nid}' is OFFLINE",
            }

    # 2. Establish pairwise routes between adjacent node hops
    established_routes: List[QuantumNetworkRoute] = []
    total_latency_ms = 0.0

    for i in range(len(nodes) - 1):
        src, dst = nodes[i], nodes[i + 1]
        req = RouteRequest(
            request_id=f"route-{uuid.uuid4().hex[:8]}",
            source_node_id=src,
            destination_node_id=dst,
            preferred_protocol=workload.protocol,
            require_entanglement=workload.protocol in (
                NetworkProtocol.E91.value,
                NetworkProtocol.ENTANGLEMENT_SWAPPING.value,
            ),
            min_fidelity=workload.min_fidelity,
            classical_fallback_acceptable=workload.classical_fallback_acceptable,
        )
        resp = self.request_route(req)
        if resp.status == "BLOCKED":
            return {
                "trace_id": trace_id,
                "workload_id": workload.workload_id,
                "status": "BLOCKED",
                "reason": f"Route negotiation between '{src}' and '{dst}' blocked: {resp.reason}",
            }
        if resp.route:
            established_routes.append(resp.route)
            total_latency_ms += resp.route.estimated_latency_ms or 5.0

    # 3. Check network latency limits
    if total_latency_ms > workload.max_latency_ms:
        if not workload.classical_fallback_acceptable:
            return {
                "trace_id": trace_id,
                "workload_id": workload.workload_id,
                "status": "BLOCKED",
                "reason": f"Accumulated latency {total_latency_ms}ms exceeds maximum limit {workload.max_latency_ms}ms",
            }

    # 4. Handle Entanglement if protocol requires it
    reserved_pairs: List[Dict[str, Any]] = []
    requires_entanglement = workload.protocol in (
        NetworkProtocol.E91.value,
        NetworkProtocol.ENTANGLEMENT_SWAPPING.value,
    )
    if requires_entanglement:
        for i in range(len(nodes) - 1):
            src, dst = nodes[i], nodes[i + 1]
            pair = self._entanglement_pool.reserve_pair(src, dst, min_fidelity=workload.min_fidelity)
            if not pair:
                if workload.classical_fallback_acceptable:
                    logger.warning(
                        "Entanglement pool empty between %s and %s; falling back to CLASSICAL_CONTROL",
                        src, dst
                    )
                    break
                return {
                    "trace_id": trace_id,
                    "workload_id": workload.workload_id,
                    "status": "BLOCKED",
                    "reason": f"Insufficient entanglement fidelity/pairs between '{src}' and '{dst}'",
                }
            reserved_pairs.append(pair.to_dict())

    # 5. Simulate Distributed Measurement Collection across nodes
    measurements: Dict[str, Dict[str, int]] = {}
    for idx, nid in enumerate(nodes):
        sub_task = workload.sub_tasks.get(nid, {})
        raw_counts = sub_task.get("measurements")
        if not raw_counts:
            # Deterministic simulated Bell measurement
            raw_counts = {"0": 512, "1": 512}
        measurements[nid] = raw_counts

    aggregated = DistributedMeasurementAggregator.aggregate(measurements)

    # 6. Compute Coordination Provenance Hash
    hasher = hashlib.sha256()
    hasher.update(workload.workload_id.encode())
    hasher.update(str(sorted(nodes)).encode())
    hasher.update(str(aggregated["shannon_entropy"]).encode())
    coordination_hash = hasher.hexdigest()

    return {
        "trace_id": trace_id,
        "workload_id": workload.workload_id,
        "status": "COMPLETED",
        "protocol": workload.protocol,
        "participating_nodes": nodes,
        "routes": [r.to_dict() for r in established_routes],
        "entanglement_pairs_used": reserved_pairs,
        "total_latency_ms": round(total_latency_ms, 2),
        "aggregated_results": aggregated,
        "coordination_hash": coordination_hash,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

QuantumNetworkContract.coordinate_distributed_workload = coordinate_distributed_workload

