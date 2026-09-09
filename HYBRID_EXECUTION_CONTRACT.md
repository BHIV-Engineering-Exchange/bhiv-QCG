# Hybrid Execution Contract

> Workload Routing, Classification Taxonomy, and Result Normalization

---

## 1. Contract Structure

Every execution in the hybrid runtime produces a `ClassifiedResult`:

```json
{
  "trace_id": "uuid",
  "classification": "QUANTUM_LOCAL | QUANTUM_SIMULATED | QUANTUM_LIVE | CLASSICAL | HYBRID",
  "execution_path": "LIVE | LOCAL | SIMULATED | FALLBACK | BLOCKED",
  "provider_id": "qiskit-aer-local",
  "result_payload": { ... },
  "confidence": 0.95,
  "result_hash": "sha256...",
  "fallback_reason": "",
  "blocked_reason": "",
  "original_classification": "",
  "timestamp": "ISO-8601"
}
```

---

## 2. Workload Routing

### 2.1 Suitability Assessment

| Suitability | Trigger | Provider Selection |
|---|---|---|
| `QUANTUM_PREFERRED` | QUBO-compatible, 3-100 variables | Best available quantum |
| `CLASSICAL_PREFERRED` | Small problems (<3 vars), general computation | Classical runtime |
| `HYBRID_REQUIRED` | QUBO >100 variables (NISQ limits) | Hybrid approach |
| `QUANTUM_REQUIRED` | Requires entanglement or live hardware | Quantum or BLOCKED |

### 2.2 Routing Decision

The `WorkloadRouter` produces a `RoutingDecision` containing:
- `suitability`: assessment result
- `recommended_provider_id`: which provider to use
- `recommended_classification`: expected classification
- `recommended_path`: expected execution path
- `fallback_available`: whether classical fallback exists
- `reason`: human-readable explanation

### 2.3 Fallback Chain

```
Quantum Live → Quantum Simulated → Quantum Local → Classical Fallback → BLOCKED
```

Every fallback is **visibly classified**. A fallback result carries:
- `execution_path = "FALLBACK"`
- `original_classification`: what was intended
- `fallback_reason`: why fallback occurred

---

## 3. Provider Selection Priority

When `prefer_live = True`:
1. `LIVE_HARDWARE` (AVAILABLE)
2. `REMOTE_SIMULATOR` (AVAILABLE)
3. `LOCAL_SIMULATOR` (AVAILABLE)
4. Any DEGRADED provider
5. Classical fallback (if acceptable)
6. BLOCKED (if no fallback)

---

## 4. Result Normalization

All execution results — quantum, classical, hybrid, fallback, blocked — are wrapped in `ClassifiedResult`. This guarantees:

1. **Uniform interface**: consumers never need to know execution type
2. **Explicit classification**: no ambiguity about what executed
3. **Provenance**: result_hash binds the result to its execution context
4. **Fallback visibility**: fallback results are never disguised as quantum

---

## 5. Execution Contract Fields

The `ComputationExecutionContract` now includes:

| Field | Type | Description |
|---|---|---|
| `execution_classification` | string | CLASSICAL / QUANTUM_LOCAL / QUANTUM_SIMULATED / QUANTUM_LIVE / HYBRID |
| `execution_path` | string | LIVE / LOCAL / SIMULATED / FALLBACK / BLOCKED |

These fields are added alongside existing `producer_type` (CLASSICAL / QUANTUM / HYBRID) for backward compatibility.
