# Integration Guide

> End-to-end integration surface for the BHIV/QCG Hybrid Quantum-Classical Runtime.

---

## 1. API Endpoints

### 1.1 Hybrid Runtime Endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| `POST` | `/hybrid/submit` | Submit a workload to the hybrid runtime |
| `GET` | `/providers` | List quantum providers and their status |
| `GET` | `/network/status` | Quantum network coordination status |
| `GET` | `/hybrid/health` | Aggregate health of the hybrid runtime |

### 1.2 Existing Endpoints (unchanged)

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/health`, `/health/live`, `/health/ready` | Health and readiness |
| `GET` | `/capabilities` | Capability manifest |
| `POST` | `/verify` | Contract verification pipeline |
| `GET` | `/evidence/certificate/{id}` | Execution certificate |
| `GET` | `/evidence/trace/{trace_id}` | Trace history |
| `GET` | `/replay/lineage/{trace_id}` | Replay lineage |

---

## 2. Workload Submission

### 2.1 Request

```json
POST /hybrid/submit
{
  "workload": {
    "workload_id": "my-workload-001",
    "message": "QUANTUM_TEST",
    "noise": 0.05,
    "shots": 1024,
    "seed": 42,
    "workload_type": "SIMULATION",
    "problem_size": 5
  },
  "workload_type": "SIMULATION",
  "problem_size": 5,
  "is_qubo_compatible": true,
  "classical_fallback_acceptable": true
}
```

### 2.2 Response

The response contains the complete execution result with classification, evidence, and provenance:

```json
{
  "workload_id": "my-workload-001",
  "trace_id": "uuid",
  "status": "COMPLETED",
  "classified_result": {
    "classification": "QUANTUM_LOCAL",
    "execution_path": "LOCAL",
    "provider_id": "qiskit-aer-local",
    "confidence": 0.95,
    "result_hash": "sha256..."
  },
  "routing_decision": {
    "suitability": "QUANTUM_PREFERRED",
    "recommended_provider_id": "qiskit-aer-local"
  },
  "provenance": {
    "trace_id": "uuid",
    "merkle_root": "sha256...",
    "bhex_ready": true
  }
}
```

---

## 3. Python SDK Integration

```python
from hybrid_runtime_orchestrator import HybridRuntimeOrchestrator
from workload_router import WorkloadMetadata

orchestrator = HybridRuntimeOrchestrator()

result = orchestrator.submit_workload(
    workload={"message": "QUANTUM_TEST", "noise": 0.05},
    metadata=WorkloadMetadata(
        workload_id="sdk-001",
        workload_type="SIMULATION",
        problem_size=5,
        is_qubo_compatible=True,
    ),
)

print(result.classified_result)
print(result.provenance)
```

---

## 4. Health Monitoring

```json
GET /hybrid/health
{
  "orchestrator": "HEALTHY",
  "providers": {
    "total_providers": 1,
    "available": 1,
    "quantum_execution_possible": true,
    "live_quantum_possible": false
  },
  "network": {
    "status": "ACTIVE",
    "total_nodes": 1,
    "active_nodes": 1
  },
  "evidence_ledger": {
    "chain_length": 5,
    "chain_valid": true,
    "merkle_root": "sha256..."
  }
}
```

---

## 5. Integration with Other BHIV Components

| Component | Integration Point | Protocol |
|---|---|---|
| NICAI | `POST /hybrid/submit` | HTTP REST |
| InsightFlow | `GET /hybrid/health` | HTTP REST |
| Pravah | Response provenance | Stream ingestion |
| KESHAV | Trust verification layer | ECDSA verification |
| MDU | Evidence ledger + Merkle proofs | REST |
| GC | Authority boundary enforcement | Governance API |
