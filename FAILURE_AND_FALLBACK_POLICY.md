# Failure and Fallback Policy

> How the hybrid runtime handles failures, degradation, and unavailability.

---

## 1. Failure Modes

| Failure | Detection | Response | Classification |
|---|---|---|---|
| Quantum provider unavailable | Health check returns UNAVAILABLE | Classical fallback (if acceptable) | FALLBACK |
| Quantum execution error | Exception during invocation | Classical fallback (if acceptable) | FALLBACK |
| Provider not registered | Registry lookup returns None | BLOCKED | BLOCKED |
| Invalid workload input | Validation exception | BLOCKED with error | BLOCKED |
| Trust verification failure | Signature check fails | BLOCKED | BLOCKED |
| Replay detected | Duplicate trace_id | BLOCKED (replay halt) | BLOCKED |
| Contract version below minimum | Semver check fails | BLOCKED (validation error) | BLOCKED |
| Network route unavailable | Node offline / protocol mismatch | BLOCKED | BLOCKED |
| Provider degraded | Health returns DEGRADED | Proceed with caution | SIMULATED/LOCAL |
| Evidence persistence failure | Disk write error | Log warning, continue | (unchanged) |

---

## 2. Fallback Chain

```
Quantum LIVE → Quantum SIMULATED → Quantum LOCAL → Classical FALLBACK → BLOCKED
```

### 2.1 Fallback Rules

1. **Fallback is explicit**: Every fallback result carries `execution_path = "FALLBACK"`, `fallback_reason`, and `original_classification`.
2. **Fallback confidence penalty**: Fallback results have reduced confidence (0.8 vs 1.0 for true classical).
3. **Fallback is opt-in**: Workloads can set `classical_fallback_acceptable = False` to require quantum or BLOCKED.
4. **Fallback never masquerades**: A classical fallback is NEVER presented as quantum execution.

### 2.2 BLOCKED Rules

1. **BLOCKED is terminal**: No execution occurs, no result payload.
2. **BLOCKED carries reason**: The `blocked_reason` field explains why.
3. **BLOCKED has zero confidence**: `confidence = 0.0`.
4. **BLOCKED is honest**: It means "we could not do what you asked."

---

## 3. Visibility Requirements

Every result flowing through the hybrid runtime MUST satisfy:

| Requirement | Enforced By |
|---|---|
| Classification is explicit | `ClassifiedResult.classification` |
| Path is explicit | `ClassifiedResult.execution_path` |
| Provider is identified | `ClassifiedResult.provider_id` |
| Fallback reason is stated | `ClassifiedResult.fallback_reason` |
| Block reason is stated | `ClassifiedResult.blocked_reason` |
| Original intent is preserved | `ClassifiedResult.original_classification` |
| Result is hash-bound | `ClassifiedResult.result_hash` |

---

## 4. Recovery

| Scenario | Recovery Action |
|---|---|
| Provider comes back online | Re-register, update status to AVAILABLE |
| Evidence ledger corruption | Re-initialize from disk persistence |
| Network route drops | Re-negotiate via `request_route()` |
| Service restart | Evidence ledger auto-restores from `persistence_path` |
