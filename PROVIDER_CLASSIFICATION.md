# Provider Classification

> Quantum Provider Types, Status States, and Classification Rules

---

## 1. Provider Types

| Type | Classification | Description | Current Status |
|---|---|---|---|
| `LOCAL_SIMULATOR` | `QUANTUM_LOCAL` | Qiskit Aer on the local machine | **Available** (auto-registered) |
| `REMOTE_SIMULATOR` | `QUANTUM_SIMULATED` | Cloud-hosted quantum simulators | Not configured |
| `LIVE_HARDWARE` | `QUANTUM_LIVE` | Real quantum processors | Not configured |

---

## 2. Provider Status States

| Status | Meaning | Accepts Workloads |
|---|---|---|
| `AVAILABLE` | Provider healthy, fully operational | Yes |
| `DEGRADED` | Provider operational with limitations | Yes (with caveats) |
| `UNAVAILABLE` | Provider cannot accept workloads | No |
| `UNKNOWN` | Health not yet determined | No |

---

## 3. Classification Rules

### 3.1 From Provider State

| Provider Status | Is Live HW | Is Remote Sim | Is Local Sim | → Classification | → Path |
|---|---|---|---|---|---|
| AVAILABLE | Yes | - | - | QUANTUM_LIVE | LIVE |
| AVAILABLE | - | Yes | - | QUANTUM_SIMULATED | SIMULATED |
| AVAILABLE | - | - | Yes | QUANTUM_LOCAL | LOCAL |
| UNAVAILABLE | Any | Any | Any | CLASSICAL | BLOCKED |
| (+ classical component) | - | - | Yes | HYBRID | LOCAL |

### 3.2 Fallback Classification

When quantum is unavailable and classical fallback is acceptable:
- Classification → `CLASSICAL`
- Path → `FALLBACK`
- `fallback_reason` → explains why fallback occurred
- `original_classification` → what was originally intended

### 3.3 Block Classification

When execution cannot proceed:
- Classification → `CLASSICAL`
- Path → `BLOCKED`
- `blocked_reason` → explains why blocked
- Confidence → `0.0`

---

## 4. Currently Registered Providers

The system auto-registers one default provider on startup:

```
Provider ID:   qiskit-aer-local
Provider Name: Qiskit Aer Local Simulator
Provider Type: LOCAL_SIMULATOR
Status:        AVAILABLE
Max Qubits:    30
Noise Model:   configurable
Backend:       aer_simulator
```

---

## 5. Adding New Providers

Register a new provider via `QuantumProviderRegistry.register_provider()`:

```python
from quantum_provider_registry import QuantumProviderRegistry, QuantumProviderRecord

registry = QuantumProviderRegistry()
registry.register_provider(QuantumProviderRecord(
    provider_id="ibm-quantum-brisbane",
    provider_name="IBM Quantum Brisbane",
    provider_type="LIVE_HARDWARE",
    status="AVAILABLE",
    health_endpoint="https://quantum-computing.ibm.com/api/health",
    max_qubits=127,
    supported_gates=["h", "x", "cx", "rz", "sx"],
))
```

**Important**: No provider is presented as available unless it genuinely is. The system will not masquerade a local simulator as live quantum hardware.
