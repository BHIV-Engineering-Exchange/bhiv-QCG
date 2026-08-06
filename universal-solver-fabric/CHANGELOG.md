# CHANGELOG: Universal Solver Fabric

## [1.0.0] — 2026-08-06 — Constitutional Runtime Integration

### Added
- **RUNTIME_IDENTITY_CARD.md**: Permanent Runtime Identity Card with all 21 mandatory fields
- **constitutional_runtime_contract.py**: Complete Constitutional Runtime Participant Contract
  - Authority Matrix (owns, does not own, delegates)
  - Runtime Contract with lifecycle state machine
  - API Contract with 5 endpoints
  - Event Contract with 8 event types
  - Attachment Contract (LOCAL/REMOTE/HYBRID)
  - Version Negotiation (COMPATIBLE/DEPRECATED/UNSUPPORTED)
  - Consumer/Producer Compatibility validation
  - Failure Behaviour with deterministic failure codes
  - Replay Guarantees
  - Evidence Chain (SHA-256 append-only hash chain)
  - Deterministic Runtime Guarantees
- **fabric_gateway_bridge.py**: Solver Fabric ↔ Communication Gateway integration
  - Trust validation via gateway replay authority
  - Replay continuity across participants
  - Cross-participant evidence correlation
- **fabric_quantum_runtime.py**: Live quantum runtime via Qiskit QuantumProducer
  - QUBO problem translation
  - Classical fallback when quantum unavailable
  - Quantum execution evidence generation
- **fabric_registry_participant.py**: Five-registry participation
  - Capability Registry, Runtime Registry, Replay Registry, Build Registry, Review Registry
  - Deterministic registration with evidence
  - Programmatic retrieval validation
- **fabric_observability.py**: Complete observability layer
  - Execution traces with evidence hashes
  - Runtime metrics (counters, histograms)
  - Consumer invocation logs
  - Failure evidence records
  - Compatibility validation tracking
  - Cross-participant replay chain
  - Full proof export
- **tests/test_constitutional_integration.py**: 68 integration tests covering
  - Authority matrix, version negotiation, runtime contract, API contract
  - Event contract, attachment contract, consumer/producer compatibility
  - Evidence chain, failure behaviour
  - Registry participation (all 5 registries)
  - Runtime lifecycle, replay validation, multi-participant runtime
- **production_readiness_report.py**: Automated production readiness validation

### Updated
- **README.md**: Constitutional runtime participant documentation
- **ARCHITECTURE.md**: Integration diagram and authority boundaries
- **INTEGRATION.md**: Complete upstream/downstream participant mapping
- **REVIEW_INDEX.md**: Constitutional integration review and certification
- **HANDOVER.md**: Complete onboarding package
- **evidence_packet/**: Full evidence structure with registry, replay, observability, deployment proofs

## [0.1.0] — Initial Release

### Added
- Solver Capability Contract (JSON Schema)
- Universal Solver Registry
- Solver Selection Engine
- Execution Adapter with evidence generation
- Solver interfaces (classical, quantum, CP, MIP, evolutionary, metaheuristics, RL)
- Unit test suite (7 tests)
- BCAB/BCAES capability registration documentation
- Platform Service specification
