# Quantum Runtime Architecture

> Phase 8+: Hybrid Quantum-Classical Runtime — BHIV/QCG Collective Completion

---

## 1. System Topology

The BHIV/QCG Hybrid Runtime bridges probabilistic quantum output to deterministic classical execution contracts. It provides a **unified entry point** for any BHIV workload that may benefit from quantum computation.

### 1.1 Complete Execution Flow

```
[BHIV Workload]
      │
      ▼
[HybridRuntimeOrchestrator]
      │
      ├── 1. Capability Discovery (QuantumProviderRegistry)
      │       └── Lists all available quantum/classical providers
      │
      ├── 2. Suitability Assessment (WorkloadRouter)
      │       └── QUANTUM_PREFERRED | CLASSICAL_PREFERRED | HYBRID_REQUIRED | QUANTUM_REQUIRED
      │
      ├── 3. Routing Decision
      │       └── Best provider selection + fallback chain
      │
      ├── 4. Execution
      │       ├── Quantum Path → Qiskit Aer (LOCAL) / Remote Simulator / Live Hardware
      │       ├── Classical Path → Classical Runtime
      │       └── Fallback Path → Classical when quantum unavailable
      │
      ├── 5. Result Normalization (ClassifiedResult)
      │       └── Every result carries: classification, path, provider_id, hash
      │
      ├── 6. Trust/Replay Boundary (CanonicalReplayAuthority)
      │       └── Replay detection, sequence tracking, persistence
      │
      ├── 7. Evidence Recording (EvidenceLedger + TraceStore)
      │       └── Merkle-chained evidence with file-backed persistence
      │
      ├── 8. Quantum Network Coordination (QuantumNetworkContract)
      │       └── Node declaration, route negotiation, control plane
      │
      └── 9. Provenance Output (BHEX-ready handover)
              └── trace_id, classification, path, hash, merkle_root
```

---

## 2. Execution Classification Taxonomy

Every execution MUST be classified. No result may flow through the system without explicit classification.

| Classification | Description | When Used |
|---|---|---|
| `CLASSICAL` | Pure classical computation | No quantum involvement |
| `QUANTUM_LOCAL` | Local quantum simulator (Qiskit Aer) | Default quantum path |
| `QUANTUM_SIMULATED` | Remote/cloud quantum simulator | Cloud sim providers |
| `QUANTUM_LIVE` | Real quantum hardware | IBM Quantum, IonQ, etc. |
| `HYBRID` | Combined quantum + classical | Mixed workloads |

| Execution Path | Description |
|---|---|
| `LIVE` | Executed on live declared provider |
| `LOCAL` | Executed on local machine |
| `SIMULATED` | Executed on simulator |
| `FALLBACK` | Quantum unavailable; fell back to classical |
| `BLOCKED` | Execution could not proceed |

---

## 3. Component Ownership

| Component | File | Owns | Does NOT Own |
|---|---|---|---|
| Execution Classification | `execution_classification.py` | Classification enums, ClassifiedResult | Routing, execution |
| Provider Registry | `quantum_provider_registry.py` | Provider registration, health, discovery | Workload routing, execution |
| Workload Router | `workload_router.py` | Suitability assessment, routing decisions | Execution, trust |
| Hybrid Orchestrator | `hybrid_runtime_orchestrator.py` | End-to-end orchestration, fallback | Quantum computation, governance |
| Network Contract | `quantum_network_contract.py` | Node declaration, route negotiation | Execution, trust |
| Evidence Ledger | `evidence_ledger.py` | Merkle-chained evidence, persistence | Replay decisions |
| Replay Authority | `canonical_replay_authority.py` | Replay detection, sequence tracking | Execution, governance |
| Trace Store | `observability.py` | Trace recording, replay reconstruction | Evidence persistence |
| Runtime Core | `runtime_core.py` | Blind execution, ACK generation | Producer routing, governance |

---

## 4. Provider Architecture

### 4.1 Provider Types

| Type | Classification | Example |
|---|---|---|
| `LOCAL_SIMULATOR` | `QUANTUM_LOCAL` | Qiskit Aer (auto-registered) |
| `REMOTE_SIMULATOR` | `QUANTUM_SIMULATED` | Cloud-based simulators |
| `LIVE_HARDWARE` | `QUANTUM_LIVE` | IBM Quantum, IonQ, Rigetti |

### 4.2 Provider Health States

| Status | Meaning |
|---|---|
| `AVAILABLE` | Provider accepts workloads |
| `DEGRADED` | Provider operational but with limitations |
| `UNAVAILABLE` | Provider cannot accept workloads |
| `UNKNOWN` | Health not yet checked |

---

## 5. Trust & Provenance Chain

Every execution produces a provenance record containing:

```json
{
  "trace_id": "uuid",
  "classification": "QUANTUM_LOCAL",
  "execution_path": "LOCAL",
  "provider_id": "qiskit-aer-local",
  "result_hash": "sha256...",
  "confidence": 0.95,
  "evidence_chain_head": "sha256...",
  "merkle_root": "sha256...",
  "bhex_ready": true
}
```

**Final rule**: Every claim carries its execution classification and evidence. Replay proves history, not legitimacy. Simulation proves behavior, not deployment. Local verification proves local verification.
