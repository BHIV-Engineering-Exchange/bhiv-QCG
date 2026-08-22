# DEP — Next Tasks

## Recommended Next Steps

### Immediate (Next Sprint)
1. **Containerized Deployment**: Deploy the Solver Fabric as a Docker container with the Capability Registry server running separately.
2. **HTTP API Server**: Implement a FastAPI/uvicorn server exposing the Platform Service spec endpoints (`/capabilities`, `/execute`, `/health`).
3. **Live HTTP Registry**: Connect `fabric_registry_participant.py` to the live Capability Registry HTTP server at startup.

### Short-Term
4. **Production Solver Adapters**: Implement `BaseSolverAdapter` for production OR-Tools CP-SAT, Pyomo MILP, and D-Wave Ocean backends.
5. **Prometheus Metrics**: Wire `fabric_observability.py` metrics to Prometheus exporters for Grafana dashboards.
6. **Heartbeat Integration**: Connect to the live `HeartbeatManager` for lease-based liveness monitoring.

### Medium-Term
7. **Multi-Node Federation**: Test solver execution across federated registry nodes.
8. **Load Testing**: Add load tests for concurrent solver selection and execution.
9. **Adversarial Testing**: Add adversarial tests for contract violation scenarios.
10. **D-Wave / IBM Quantum**: Add live cloud quantum backend adapters (D-Wave Leap, IBM Quantum).
