# Authority Boundaries

> Who owns what. Who does not own what. No exceptions.

---

## 1. Component Authority Matrix

| Component | OWNS | Does NOT Own |
|---|---|---|
| **Quantum Runtime** (QuantumProducer, Qiskit Aer) | Quantum circuit construction, simulation execution, shot counting, noise modeling | Governance, routing decisions, trust verification, replay authority |
| **QCG Runtime Core** (RuntimeCore) | Blind contract execution, ACK generation, runtime hash | Producer routing, governance policy, replay state, quantum result fabrication |
| **Hybrid Orchestrator** (HybridRuntimeOrchestrator) | End-to-end workflow, capability attachment, fallback behavior, result normalization | Quantum computation, governance, trust, replay |
| **Workload Router** (WorkloadRouter) | Suitability assessment, routing decisions, fallback determination | Execution, provider health, trust |
| **Provider Registry** (QuantumProviderRegistry) | Provider registration, health checking, discovery, best-provider selection | Execution, routing decisions, trust |
| **Quantum Network** (QuantumNetworkContract) | Node declaration, route negotiation, classical control plane | Execution, trust, governance, execution legitimacy |
| **Trust Chain** (TrustChain, TrustProvider) | Key generation, signing, verification, key exchange | Certificate management, service registration, federation |
| **Replay Authority** (CanonicalReplayAuthority) | Replay detection, sequence tracking, persistence, lineage | Contract validation, execution, governance |
| **Evidence Ledger** (EvidenceLedger) | Merkle-chained evidence, persistence, chain verification | Replay decisions, execution logic |
| **Observability** (TraceStore) | Trace recording, replay reconstruction, OpenTelemetry export | Evidence persistence, execution |
| **Governance** (GovernanceLayer) | Policy enforcement, producer authorization, violation recording | Execution, replay, quantum computation |
| **Insight** (Observability endpoints) | Routing, observation, telemetry publication | Replay authority, governance, execution legitimacy |

---

## 2. Negative Authority (Critical Constraints)

| Component | May NOT |
|---|---|
| Quantum Runtime | Govern, make policy decisions, claim authority over execution |
| QCG | Manufacture quantum results, bypass trust verification |
| Insight | Become replay authority, become governance authority |
| Quantum Network | Silently inherit execution legitimacy, claim computation occurred when only a route was established |
| TMS | Execute, replicate quantum capabilities |
| GC | Override quantum computation results, bypass trust chain |
| MDU | Generate execution evidence, bypass replay authority |

---

## 3. Enforcement

- **Classification enforcement**: Every result carries `ExecutionClassification` and `ExecutionPath`. No result flows without these.
- **Replay enforcement**: `CanonicalReplayAuthority` is the SOLE source of replay decisions. No other component may generate replay verdicts.
- **Trust enforcement**: All trust operations go through the `TrustProvider` interface. Application code never imports concrete trust classes.
- **Evidence enforcement**: All evidence flows through `EvidenceLedger`. No component may write evidence outside this chain.

---

## 4. Authority Flow

```
Workload → Router (DECIDES) → Provider (EXECUTES) → Classifier (LABELS) → 
Trust (VERIFIES) → Replay (CHECKS) → Evidence (RECORDS) → Provenance (OUTPUTS)
```

Each arrow is a contract boundary. No component crosses into another's authority.
