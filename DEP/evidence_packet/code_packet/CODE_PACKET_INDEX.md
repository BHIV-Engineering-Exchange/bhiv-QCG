# Code Packet Index

> Files included in the evidence code packet for review.

---

## New Files (Kanishk's Integration Layer)

| File | Purpose | Why It Changed |
|---|---|---|
| `execution_classification.py` | **Foundation**: Defines the execution classification taxonomy (CLASSICAL, QUANTUM_LOCAL, QUANTUM_SIMULATED, QUANTUM_LIVE, HYBRID) and execution paths (LIVE, LOCAL, SIMULATED, FALLBACK, BLOCKED). Every result in the hybrid runtime is wrapped in `ClassifiedResult`. | New — required by task to ensure every execution carries its classification |
| `quantum_provider_registry.py` | **Discovery**: Registry of quantum providers with health monitoring and best-provider selection. Auto-registers the local Qiskit Aer simulator. Provides the capability discovery surface. | New — required for quantum capability attachment through canonical discovery |
| `workload_router.py` | **Routing**: Assesses workload suitability (QUANTUM_PREFERRED, CLASSICAL_PREFERRED, etc.) and produces explicit routing decisions with fallback chains. Never executes — only decides. | New — required for suitability decision and quantum/classical routing |
| `quantum_network_contract.py` | **Networking**: Coordination contract for quantum network operations. Node declaration, route negotiation, classical control plane. Protocol-ready surface, not simulated physics. | New — required for quantum-network coordination contract |
| `hybrid_runtime_orchestrator.py` | **Orchestration**: Central convergence engine implementing the complete target runtime path from capability discovery through provenance output. Ties all components together. | New — required for collective runtime convergence |
| `test_hybrid_runtime.py` | **Verification**: All 12 mandatory tests from the task spec, plus 4 classification utility tests. Every test states its expected execution path. | New — required by Phase 4 |

## Modified Files

| File | What Changed | Why |
|---|---|---|
| `evidence_ledger.py` | Added file-backed persistence (`save_to_disk`, `load_from_disk`, auto-save on append). Constructor now accepts `persistence_path`. | Evidence/replay must survive restart — was in-memory only |
| `config.py` | Added 5 new config keys for hybrid runtime: `EVIDENCE_LEDGER_PATH`, `QUANTUM_NETWORK_ENABLED`, `DEFAULT_EXECUTION_CLASSIFICATION`, `QUANTUM_PROVIDER_PREFER_LIVE`, `CLASSICAL_FALLBACK_ENABLED`. | New components need configuration |
| `execution_contract.py` | Added `execution_classification` and `execution_path` fields to `ComputationExecutionContract`. | Every contract must carry its execution classification |
| `observability.py` | Added `record_quantum_execution_trace()` to `TraceStore` for quantum-classified traces. | Observability must capture classification metadata |
| `web_server.py` | Fixed git merge conflict (L143-151). Added 4 new endpoints: `POST /hybrid/submit`, `GET /providers`, `GET /network/status`, `GET /hybrid/health`. | Merge conflict was blocking. New endpoints expose hybrid runtime API |
| `integration_harness.py` | **Removed pseudo-token bypass** (`Bearer VALID_GC_TOKEN`). Producer registration now requires valid ECDSA public key (min 16 chars). Producers without valid keys are HALTED. | Deliverable 5: remove pseudo trust from production flow |

## Why Each File Is Here

Every file in this packet either:
1. **Implements a new capability** required by the collective task (classification, routing, orchestration, networking), or
2. **Modifies an existing component** to integrate with the new hybrid runtime (persistence, config, observability, trust boundary), or
3. **Proves the system works** (test suite with all 12 mandatory scenarios)

No file is included that doesn't directly relate to the collective completion deliverables.
