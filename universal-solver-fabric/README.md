# Universal Solver Fabric

The Universal Solver Fabric is the foundational optimization infrastructure of the BHIV Sovereign Optimization Capability, deployed as a **Constitutional Runtime Participant** (`Optimization.SolverFabric.v1`) within the TANTRA canonical ecosystem.

## Constitutional Position

| Field                | Value                                          |
|----------------------|------------------------------------------------|
| Runtime ID           | `TANTRA-PSR-USF-001`                           |
| Capability ID        | `bhiv.capabilities.solver_fabric`              |
| Permanent Identity   | `Optimization.SolverFabric.v1`                 |
| Constitutional Layer | Platform Service Layer / Agnostic Execution    |
| Version              | 1.0.0                                          |

## Components

### Core Solver Fabric
1. **Solver Capability Contract** (`solver_contract.schema.json`): JSON Schema enforcing solver capability declarations.
2. **Universal Solver Registry** (`solver_registry.py`): Validates, tracks, and discovers registered solvers.
3. **Solver Selection Engine** (`solver_selection_engine.py`): Deterministic solver ranking and selection.
4. **Execution Adapter** (`execution_adapter.py`): Replay-safe execution with evidence generation.
5. **Solver Interfaces** (`solver_interfaces/`): Attachment points for classical, quantum, CP, MIP, evolutionary, and other engines.

### Constitutional Integration
6. **Constitutional Runtime Contract** (`constitutional_runtime_contract.py`): Authority matrix, runtime/API/event/attachment contracts, version negotiation, replay/evidence guarantees.
7. **Gateway Bridge** (`fabric_gateway_bridge.py`): Integration with the Quantum Communication Gateway for trust validation and replay continuity.
8. **Quantum Runtime** (`fabric_quantum_runtime.py`): Live quantum execution via Qiskit QuantumProducer with classical fallback.
9. **Registry Participant** (`fabric_registry_participant.py`): Five-registry participation (Capability, Runtime, Replay, Build, Review).
10. **Observability** (`fabric_observability.py`): Trace collection, metrics, consumer logs, failure evidence, cross-participant replay chains.

## Getting Started

### Prerequisites
```bash
pip install jsonschema
pip install qiskit qiskit-aer  # For quantum runtime
```

### Quick Start — Registration & Selection
```python
from solver_registry import SolverRegistry
from solver_selection_engine import SolverSelectionEngine

registry = SolverRegistry("solver_contract.schema.json")
# Register solvers...
engine = SolverSelectionEngine(registry)
recommendations = engine.select_solvers({"problem_type": "MILP", "required_constraints": ["LINEAR"]})
```

### Quick Start — Constitutional Integration
```python
from constitutional_runtime_contract import ConstitutionalRuntimeContract
from fabric_registry_participant import SolverFabricRegistryParticipant
from fabric_observability import SolverFabricObservability

# Initialize contract
contract = ConstitutionalRuntimeContract()

# Register with all five registries
participant = SolverFabricRegistryParticipant(contract=contract)
result = participant.register_all()

# Record execution observability
obs = SolverFabricObservability(contract=contract)
trace = obs.record_execution(trace_id="...", replay_id="...", ...)
```

## Testing
```bash
# Constitutional integration tests (68 tests)
python -m pytest tests/test_constitutional_integration.py -v

# Original fabric tests (7 tests)
python -m pytest tests/test_fabric.py -v

# Production readiness report
python production_readiness_report.py
```

## Architecture & Integration
- `RUNTIME_IDENTITY_CARD.md` — Permanent constitutional identity (21 fields)
- `ARCHITECTURE.md` — Architectural boundaries and component breakdown
- `INTEGRATION.md` — Ecosystem integration mapping
- `PLATFORM_SERVICE_SPEC.md` — Platform Service API specification
- `runtime_flow.md` — Runtime execution sequence diagram
