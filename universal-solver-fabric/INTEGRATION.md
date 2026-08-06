# Universal Solver Fabric — Integration Mapping

This document classifies the Universal Solver Fabric within the TANTRA canonical ecosystem, defining its boundaries, dependencies, runtime position, and all upstream/downstream participant relationships.

## Classification

* **Primary Domain**: Sovereign Optimization
* **Capability**: Universal Solver Fabric
* **Capability ID**: `bhiv.capabilities.solver_fabric`
* **Platform Service**: `Optimization.SolverFabric.v1`
* **Runtime ID**: `TANTRA-PSR-USF-001`
* **Runtime Position**: Platform Service Layer / Agnostic Execution Layer

## Upstream Participants

| Participant                      | Interaction                                       | Protocol   |
|----------------------------------|---------------------------------------------------|------------|
| TANTRA Product Layer             | Submits optimization requests                     | HTTP/REST  |
| Platform Service Router          | Routes requests to fabric endpoint                | HTTP/REST  |
| GovernanceLayer                  | Pre-execution policy enforcement                  | In-process |
| PlatformServiceRegistry          | Service registration and lifecycle management     | In-process |
| CapabilityRegistry               | Capability discovery and registration             | HTTP/REST  |

## Downstream Participants

| Participant                      | Interaction                                       | Protocol   |
|----------------------------------|---------------------------------------------------|------------|
| Solver Adapters (OR-Tools, etc.) | Execution delegation via BaseSolverAdapter        | In-process |
| Quantum Runtime (Qiskit)         | Quantum solver execution via QuantumProducer      | In-process |
| Communication Gateway            | Result routing via CommunicationRequest pipeline  | In-process |
| Observability / TraceStore       | Telemetry and trace emission                      | In-process |
| Replay Registry                  | Replay enforcement and sequence tracking          | In-process |
| Heartbeat Manager                | Lease-based liveness protocol                     | In-process |

## Runtime APIs

| Endpoint               | Method | Purpose                                             |
|------------------------|--------|-----------------------------------------------------|
| `/capabilities`        | GET    | Discover available solvers matching query criteria   |
| `/execute`             | POST   | Submit optimization problem for deterministic solve  |
| `/health`              | GET    | Runtime health status                                |
| `/solvers/{id}`        | GET    | Retrieve specific solver metadata                    |
| `/solvers/{id}/status` | GET    | Solver health status                                 |

## Event Contracts

| Event Name                            | Trigger                              |
|---------------------------------------|--------------------------------------|
| `solver_fabric.solver_registered`     | Solver passes contract validation    |
| `solver_fabric.solver_disabled`       | Health check failure or manual       |
| `solver_fabric.execution_started`     | Problem bound to solver              |
| `solver_fabric.execution_completed`   | Solver returns result                |
| `solver_fabric.execution_failed`      | Solver throws or times out           |
| `solver_fabric.registration_completed`| All registries registered            |
| `solver_fabric.health_check`          | Periodic health validation           |

## Registry Participation

| Registry                 | Registration ID                               | Status |
|--------------------------|-----------------------------------------------|--------|
| Capability Registry      | `bhiv.capabilities.solver_fabric`             | ACTIVE |
| Runtime Registry         | `TANTRA-PSR-USF-001`                          | ACTIVE |
| Replay Registry          | `USF-REPLAY-REGISTRATION-1.0.0`              | ACTIVE |
| Build Registry           | `USF-BUILD-1.0.0-{hash}`                     | ACTIVE |
| Review Registry          | `USF-REVIEW-CONSTITUTIONAL-INTEGRATION`       | ACTIVE |

## Authority Boundaries

* **Explicit authority boundaries**: 
  - Strictly decouples domain formulation from deterministic execution.
  - Acts solely as a participant and execution fabric, not an orchestrator.
  - Enforces governed capability contracts for solver registration and discovery.
  - Generates replay-safe evidence packages for every execution.
  - Negotiates attachment modes (LOCAL/REMOTE/HYBRID) and versions.
* **Components explicitly NOT owned**: 
  - Optimization modeling, problem formulation, or business logic.
  - Orchestration of external workflows.
  - Master Directive definitions.
  - BCAB/BCAES architecture definitions.
  - Replay detection (→ CanonicalReplayAuthority).
  - Governance policy (→ GovernanceLayer).

## SDK Integration

Consumers access the fabric via:
```python
from platform_capability_sdk import PlatformCapabilitySDK

sdk = PlatformCapabilitySDK()
result = sdk.invoke_capability("TANTRA-PSR-USF-001", "execute_optimization", payload)
```
