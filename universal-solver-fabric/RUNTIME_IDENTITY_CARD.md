# Runtime Identity Card — Universal Solver Fabric

> **Classification**: PERMANENT CONSTITUTIONAL DOCUMENT
> **Last Updated**: 2026-08-06
> **Authority**: BHIV Sovereign Optimization Domain

---

## 1. Constitutional Layer

**Platform Service Layer / Agnostic Execution Layer**

The Universal Solver Fabric operates within the Platform Service Layer of the TANTRA canonical ecosystem. It is positioned as an agnostic execution participant that decouples domain formulation from deterministic solver execution.

## 2. Permanent Identity

**`Optimization.SolverFabric.v1`**

## 3. Capability ID

**`bhiv.capabilities.solver_fabric`**

## 4. Runtime ID

**`TANTRA-PSR-USF-001`**

## 5. Owner

| Field     | Value                                     |
|-----------|-------------------------------------------|
| Team      | BHIV Sovereign Optimization               |
| Contact   | solver-fabric@bhiv.internal               |
| Domain    | Sovereign Optimization                    |

## 6. Purpose

Provide a unified, governed execution environment for heterogeneous optimization solvers (Classical, Quantum, Heuristic, Evolutionary) with deterministic routing, selection, and replay capabilities. The fabric acts as a **participant and execution layer**, never an orchestrator.

## 7. Authority Owned

| Authority                                         | Scope                                    |
|---------------------------------------------------|------------------------------------------|
| Solver Capability Contract enforcement            | Schema validation of solver registration |
| Deterministic Solver Selection                    | Problem-to-solver ranking and matching   |
| Execution Adapter lifecycle                       | Bind, execute, evidence generation       |
| Solver health tracking                            | Enable/disable/health-check of solvers   |
| Evidence package generation                       | Trace IDs, replay IDs, provenance        |
| Attachment mode negotiation                       | LOCAL / REMOTE / HYBRID                  |
| Solver Registry management                        | Registration, deregistration, lookup     |

## 8. Authority Explicitly NOT Owned

| Authority                                         | Owned By                                 |
|---------------------------------------------------|------------------------------------------|
| Problem formulation / modeling                    | Domain Applications                      |
| Business logic execution                          | Product Layer                            |
| Orchestration of external workflows               | Platform Orchestrator                    |
| Master Directive definitions                      | BCAB / Governance Authority              |
| Budget / cost approval                            | Product Layer                            |
| Data storage / persistence                        | Infrastructure Services                  |
| Replay detection (primary)                        | CanonicalReplayAuthority                 |
| Governance policy enforcement                     | GovernanceLayer                          |
| Service registration                              | PlatformServiceRegistry                  |
| Certificate authority                             | ServiceCertificateAuthority              |
| Federation protocol                               | FederatedRegistryNode                    |

## 9. Upstream Participants

| Participant                      | Interaction                                       |
|----------------------------------|---------------------------------------------------|
| TANTRA Product Layer             | Submits optimization requests                     |
| Platform Service Router          | Routes requests to fabric endpoint                |
| GovernanceLayer                  | Pre-execution policy enforcement                  |
| PlatformServiceRegistry          | Service registration and lifecycle management     |
| CapabilityRegistry               | Capability discovery and registration             |

## 10. Downstream Participants

| Participant                      | Interaction                                       |
|----------------------------------|---------------------------------------------------|
| Solver Adapters (OR-Tools, etc.) | Execution delegation via BaseSolverAdapter        |
| Quantum Runtime (Qiskit)         | Quantum solver execution via QuantumProducer      |
| Communication Gateway            | Result routing via CommunicationRequest pipeline  |
| Observability / TraceStore       | Telemetry emission                                |
| Replay Registry                  | Replay enforcement and sequence tracking          |

## 11. Runtime APIs

| Endpoint               | Method | Purpose                                             |
|------------------------|--------|-----------------------------------------------------|
| `/capabilities`        | GET    | Discover available solvers matching query criteria   |
| `/execute`             | POST   | Submit optimization problem for deterministic solve  |
| `/health`              | GET    | Runtime health status                                |
| `/solvers/{id}`        | GET    | Retrieve specific solver metadata                    |
| `/solvers/{id}/status` | GET    | Solver health status                                 |

## 12. Event Contracts

| Event Name                       | Trigger                              | Payload                              |
|----------------------------------|--------------------------------------|--------------------------------------|
| `solver_fabric.solver_registered`| Solver passes contract validation    | solver_id, version, capabilities     |
| `solver_fabric.solver_disabled`  | Health check failure or manual       | solver_id, reason, timestamp         |
| `solver_fabric.execution_started`| Problem bound to solver              | trace_id, solver_id, problem_type    |
| `solver_fabric.execution_completed`| Solver returns result             | trace_id, replay_id, status, duration|
| `solver_fabric.execution_failed` | Solver throws or times out          | trace_id, error_code, error_message  |

## 13. SDK Attachment Contracts

| Attachment Mode | Description                                                  |
|-----------------|--------------------------------------------------------------|
| `LOCAL`         | Direct in-process invocation (default for CPU solvers)       |
| `REMOTE`        | Dispatch to remote compute cluster (QPU, HPC)                |
| `HYBRID`        | Split execution across classical + quantum (e.g., QAOA loop) |

**SDK Integration**: Consumers access the fabric via `PlatformCapabilitySDK.invoke_capability()` using service ID `TANTRA-PSR-USF-001`.

## 14. Registry Participation

| Registry                 | Registration Status | Record ID                        |
|--------------------------|---------------------|----------------------------------|
| Capability Registry      | ACTIVE              | `bhiv.capabilities.solver_fabric`|
| Runtime Registry         | ACTIVE              | `TANTRA-PSR-USF-001`            |
| Replay Registry          | ACTIVE              | Sequence-tracked per execution   |
| Build Registry           | ACTIVE              | `USF-BUILD-{version}-{hash}`    |
| Review Registry          | ACTIVE              | `USF-REVIEW-{sprint}`           |

## 15. Evidence Produced

| Evidence Type                    | Format   | Persistence                          |
|----------------------------------|----------|--------------------------------------|
| Execution Evidence Package       | JSON     | Per-execution, replay-safe           |
| Trace ID                         | UUID v4  | Per-execution                        |
| Replay ID                        | UUID v4  | Per-execution                        |
| Provenance Metadata              | JSON     | Embedded in evidence package         |
| Registration Evidence            | JSON     | Per-registration event               |
| Capability Hash                  | SHA-256  | Per-registration                     |
| Evidence Chain                   | SHA-256  | Append-only hash chain               |

## 16. Replay Participation

- **Replay Model**: Every execution produces a complete replay-safe evidence package containing deterministic inputs, provenance metadata, and cryptographic hashes.
- **Cross-Participant Replay**: Replay chains span Solver Fabric → Gateway → Replay Registry.
- **Determinism**: Solver Selection Engine produces deterministic ordering given the same inputs. Classical solvers with fixed seeds produce identical outputs.
- **Replay Registry Integration**: All execution replay IDs are submitted to the platform Replay Registry with TTL enforcement and sequence ordering.

## 17. Observability Model

| Metric                           | Type      | Collection                           |
|----------------------------------|-----------|--------------------------------------|
| `solver_fabric.executions_total` | Counter   | Per execution                        |
| `solver_fabric.execution_duration_ms` | Histogram | Per execution                   |
| `solver_fabric.failures_total`   | Counter   | Per failed execution                 |
| `solver_fabric.solvers_registered` | Gauge   | Current solver count                 |
| `solver_fabric.selection_time_ms`| Histogram | Per selection operation               |

**Trace Integration**: All execution traces are emitted to the platform `TraceStore` via `observability.py` using `trace_type = "solver_fabric_execution"`.

## 18. Knowledge Contribution

- Execution results and confidence scores feed into solver ranking heuristics for future selections.
- Failure patterns (repeated solver crashes, timeout frequency) drive automatic confidence adjustments.
- Solver capability metadata is available for platform-wide capability discovery.

## 19. Runtime Health Model

| Health State  | Condition                                                   |
|---------------|-------------------------------------------------------------|
| `HEALTHY`     | ≥1 solver registered, last execution <5min, no critical errors |
| `DEGRADED`    | All solvers disabled OR failure rate >50% in last 10 executions |
| `UNHEALTHY`   | Registry unavailable OR no solvers registered                |

**Heartbeat**: Participates in the platform heartbeat protocol via `HeartbeatManager` with configurable TTL (default 30s).

## 20. Version Compatibility

| Fabric Version | Schema Version | API Version | Status       |
|----------------|----------------|-------------|--------------|
| 1.0.0          | 1.0.0          | v1          | ACTIVE       |
| 0.9.x          | 1.0.0          | v1          | DEPRECATED   |
| <0.9.0         | <1.0.0         | —           | UNSUPPORTED  |

**Negotiation**: Version compatibility is enforced via `PlatformServiceRegistry.negotiate_version()` with semantic versioning rules.

## 21. Production Certification Status

| Certification              | Status     | Date       |
|----------------------------|------------|------------|
| Schema Validation          | ✅ PASSED  | 2026-08-06 |
| Deterministic Execution    | ✅ PASSED  | 2026-08-06 |
| Replay Evidence            | ✅ PASSED  | 2026-08-06 |
| Registry Participation     | ✅ PASSED  | 2026-08-06 |
| Gateway Integration        | ✅ PASSED  | 2026-08-06 |
| Production Readiness       | ✅ PASSED  | 2026-08-06 |
