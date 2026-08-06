# HANDOVER: Universal Solver Fabric

> **Target Audience**: New engineer with zero prior context
> **Last Updated**: 2026-08-06
> **Sprint**: Constitutional Runtime Integration

## What Is This?

The Universal Solver Fabric is BHIV's unified optimization execution layer. It allows any optimization engine (classical, quantum, heuristic, evolutionary) to participate in the BHIV platform through governed capability contracts.

As of this sprint, the Solver Fabric is a **permanent Constitutional Runtime Participant** within the BHIV Living Organism, permanently wired into the platform's registry, replay, evidence, gateway, and observability systems.

## Quick Orientation

| What                         | Where                                          |
|------------------------------|------------------------------------------------|
| Runtime Identity Card        | `RUNTIME_IDENTITY_CARD.md`                     |
| Constitutional Contract      | `constitutional_runtime_contract.py`           |
| Core Solver Registry         | `solver_registry.py`                           |
| Solver Selection Engine      | `solver_selection_engine.py`                   |
| Execution Adapter            | `execution_adapter.py`                         |
| Gateway Bridge               | `fabric_gateway_bridge.py`                     |
| Quantum Runtime              | `fabric_quantum_runtime.py`                    |
| Registry Participant         | `fabric_registry_participant.py`               |
| Observability                | `fabric_observability.py`                      |
| API Specification            | `PLATFORM_SERVICE_SPEC.md`                     |
| Architecture                 | `ARCHITECTURE.md`                              |
| Integration Map              | `INTEGRATION.md`                               |
| Tests                        | `tests/test_constitutional_integration.py` (68 tests) |
| Original Fabric Tests        | `tests/test_fabric.py` (7 tests)               |
| Production Readiness         | `production_readiness_report.py`               |
| Evidence                     | `evidence_packet/`                             |

## How to Run

### Install dependencies
```bash
pip install jsonschema qiskit qiskit-aer numpy python-dotenv cryptography pytest
```

### Run tests
```bash
cd universal-solver-fabric
python -m pytest tests/ -v
```

### Run production readiness report
```bash
cd universal-solver-fabric
set PYTHONIOENCODING=utf-8
python production_readiness_report.py
```

## Key Concepts

1. **Constitutional Position**: The fabric occupies exactly one position in the ecosystem — Platform Service Layer, Agnostic Execution. It is NOT an orchestrator.

2. **Authority Boundaries**: The fabric owns solver registration, selection, execution, and evidence. It does NOT own problem formulation, business logic, orchestration, governance, or replay detection.

3. **Five-Registry Participation**: The fabric registers with Capability, Runtime, Replay, Build, and Review registries programmatically at startup.

4. **Evidence Chain**: Every execution produces a replay-safe evidence package chained via SHA-256 hashes. The chain is append-only and tamper-detectable.

5. **Gateway Bridge**: Solver results flow through the Communication Gateway for trust validation and replay continuity.

6. **Quantum Runtime**: QUBO problems can execute through the live Qiskit QuantumProducer, with automatic classical fallback.

## What To Do Next

1. **Deploy as containerized service**: Use `Dockerfile` and `docker-compose.yml` for deployment.
2. **Enable HTTP registration**: Connect `fabric_registry_participant.py` to live Capability Registry servers.
3. **Add real optimization engines**: Implement `BaseSolverAdapter` for production OR-Tools, Pyomo, or D-Wave backends.
4. **Production monitoring**: Wire `fabric_observability.py` metrics to Prometheus/Grafana.
5. **Expand test coverage**: Add load tests, adversarial tests, and multi-node integration tests.

## Contact

- Team: BHIV Sovereign Optimization
- Domain: Sovereign Optimization
