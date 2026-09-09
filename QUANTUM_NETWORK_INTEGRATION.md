# Quantum Network Integration

> Quantum-Network Coordination Contract for the BHIV/QCG Hybrid Runtime

---

## 1. Purpose

The quantum network layer provides an **integration surface** for quantum communication between nodes. It is a coordination layer — it defines how quantum nodes declare capabilities, negotiate routes, and participate in distributed operations.

**Critical boundary**: The quantum network coordinates; it does NOT execute. A valid route contract means "communication CAN occur on this path." It does NOT mean "quantum computation has occurred."

---

## 2. Network Architecture

### 2.1 Node Model

Every quantum network participant must declare as a `QuantumNetworkNode`:

| Field | Type | Description |
|---|---|---|
| `node_id` | string | Unique node identifier |
| `capabilities` | list | `QKD`, `ENTANGLEMENT`, `TELEPORTATION`, etc. |
| `supported_protocols` | list | `BB84`, `E91`, `ENTANGLEMENT_SWAPPING`, `CLASSICAL_CONTROL` |
| `classical_control_endpoint` | string | HTTP endpoint for classical coordination |
| `network_status` | enum | `ACTIVE`, `DEGRADED`, `OFFLINE`, `UNKNOWN` |
| `max_entanglement_pairs` | int | Maximum simultaneous entangled pairs |
| `qubit_coherence_time_us` | float | Qubit coherence time in microseconds |

### 2.2 Route Model

Routes connect two nodes via a specific protocol:

| Field | Type | Description |
|---|---|---|
| `route_id` | string | UUID of this route |
| `source_node_id` | string | Sending node |
| `destination_node_id` | string | Receiving node |
| `protocol` | enum | BB84, E91, etc. |
| `status` | enum | `LIVE`, `LOCAL`, `SIMULATED`, `BLOCKED` |
| `classical_fallback_available` | bool | Whether classical fallback exists |
| `entanglement_fidelity` | float | Quality of entanglement [0, 1] |

---

## 3. Route Status Classification

| Status | Meaning | Current State |
|---|---|---|
| `LIVE` | Real quantum link established | Not yet available (no quantum network hardware) |
| `LOCAL` | Local simulation of quantum link | Default for active nodes |
| `SIMULATED` | Degraded simulation | Used when nodes are degraded |
| `BLOCKED` | Route cannot be established | Node offline or protocol incompatible |

---

## 4. Classical Control Plane

The classical control plane is **always available**. It provides:
- Node registration and discovery
- Route negotiation
- Protocol capability advertisement
- Network health monitoring

The classical control plane is the coordination layer that makes quantum operations possible. It does NOT replace quantum communication — it manages it.

---

## 5. Authority Boundary

**Quantum Network Contract OWNS:**
- Network node declaration and discovery
- Route request and validation
- Classical control plane management
- Network status reporting

**Quantum Network Contract does NOT OWN:**
- Quantum computation (→ QuantumProducer / RuntimeCore)
- Execution governance (→ GovernanceLayer)
- Trust/authentication (→ TrustChain / TrustProvider)
- Provider health (→ QuantumProviderRegistry)

---

## 6. Integration with QKD

The existing `QuantumTrustProviderInterface` in `quantum_trust_provider.py` provides BB84 and E91 protocol stubs. The network contract's route negotiation integrates with these protocols:

1. Two nodes declare with `BB84` protocol support
2. Route is negotiated via `request_route()`
3. Once route is established, QKD key exchange can occur via the trust provider
4. All operations flow through the classical control plane

**Current status**: All routes are classified as `LOCAL` since no live quantum network hardware exists. This is stated honestly — no simulation masquerades as live quantum networking.
