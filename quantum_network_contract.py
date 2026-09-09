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
