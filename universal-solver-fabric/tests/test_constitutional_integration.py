"""
test_constitutional_integration.py — Comprehensive Integration Test Suite

Tests the Universal Solver Fabric's constitutional integration across:
    - Unit Tests (contract validation, authority, version negotiation)
    - Integration Tests (gateway bridge, registry, SDK)
    - Runtime Tests (full lifecycle)
    - Replay Validation (cross-participant)
    - Registry Validation (all five registries)
    - Version Negotiation Tests
    - Failure Recovery Tests
    - Multi-Participant Runtime Tests
"""

import json
import os
import sys
import time
import uuid

import pytest

# Add paths for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from constitutional_runtime_contract import (
    ConstitutionalRuntimeContract,
    AuthorityMatrix,
    RuntimeContract,
    APIContract,
    EventContract,
    AttachmentContract,
    ConsumerCompatibility,
    ProducerCompatibility,
    FailureBehaviour,
    ReplayGuarantee,
    EvidenceChain,
    DeterministicGuarantees,
    VersionCompatibility,
    FailureCode,
    LifecycleState,
    EventType,
    AttachmentMode,
    negotiate_version,
    parse_semver,
    RUNTIME_ID,
    CAPABILITY_ID,
    PERMANENT_IDENTITY,
    FABRIC_VERSION,
)
from fabric_registry_participant import (
    SolverFabricRegistryParticipant,
    build_capability_registry_payload,
    build_platform_service_payload,
    build_build_registry_payload,
    build_review_registry_payload,
)
from fabric_observability import (
    SolverFabricObservability,
    FabricMetrics,
)


# ===========================================================================
# UNIT TESTS — Constitutional Contract
# ===========================================================================

class TestAuthorityMatrix:
    def test_owns_solver_selection(self):
        matrix = AuthorityMatrix()
        assert matrix.validate_authority("Deterministic Solver Selection")

    def test_owns_evidence_generation(self):
        matrix = AuthorityMatrix()
        assert matrix.validate_authority("Evidence package generation")

    def test_does_not_own_problem_formulation(self):
        matrix = AuthorityMatrix()
        assert matrix.is_explicitly_forbidden("Problem formulation")

    def test_does_not_own_business_logic(self):
        matrix = AuthorityMatrix()
        assert matrix.is_explicitly_forbidden("Business logic")

    def test_does_not_own_orchestration(self):
        matrix = AuthorityMatrix()
        assert matrix.is_explicitly_forbidden("Orchestration of external workflows")

    def test_delegates_to_replay_authority(self):
        matrix = AuthorityMatrix()
        assert "CanonicalReplayAuthority" in matrix.delegates_to


class TestVersionNegotiation:
    def test_exact_version_match(self):
        status, version = negotiate_version("1.0.0", ["1.0.0"])
        assert status == VersionCompatibility.COMPATIBLE
        assert version == "1.0.0"

    def test_compatible_minor_upgrade(self):
        status, version = negotiate_version("1.0.0", ["1.1.0"])
        assert status == VersionCompatibility.COMPATIBLE

    def test_deprecated_minor_downgrade(self):
        status, version = negotiate_version("1.2.0", ["1.0.0"])
        assert status == VersionCompatibility.DEPRECATED

    def test_unsupported_major_mismatch(self):
        status, version = negotiate_version("2.0.0", ["1.0.0"])
        assert status == VersionCompatibility.UNSUPPORTED

    def test_invalid_version_string(self):
        status, version = negotiate_version("invalid", ["1.0.0"])
        assert status == VersionCompatibility.UNSUPPORTED

    def test_parse_semver_valid(self):
        assert parse_semver("1.2.3") == (1, 2, 3)

    def test_parse_semver_invalid(self):
        with pytest.raises(ValueError):
            parse_semver("not.a.version")


class TestRuntimeContract:
    def test_valid_transition_registered_to_discovered(self):
        contract = RuntimeContract()
        assert contract.validate_transition("REGISTERED", "DISCOVERED")

    def test_valid_transition_executing_to_completed(self):
        contract = RuntimeContract()
        assert contract.validate_transition("EXECUTING", "COMPLETED")

    def test_valid_transition_executing_to_failed(self):
        contract = RuntimeContract()
        assert contract.validate_transition("EXECUTING", "FAILED")

    def test_invalid_transition_completed_to_executing(self):
        contract = RuntimeContract()
        assert not contract.validate_transition("COMPLETED", "EXECUTING")

    def test_deregistered_is_terminal(self):
        contract = RuntimeContract()
        assert not contract.validate_transition("DEREGISTERED", "REGISTERED")

    def test_identity_fields(self):
        contract = RuntimeContract()
        assert contract.runtime_id == RUNTIME_ID
        assert contract.capability_id == CAPABILITY_ID
        assert contract.permanent_identity == PERMANENT_IDENTITY


class TestAPIContract:
    def test_has_capabilities_endpoint(self):
        api = APIContract()
        ep = api.get_endpoint("/capabilities")
        assert ep is not None
        assert ep.method == "GET"

    def test_has_execute_endpoint(self):
        api = APIContract()
        ep = api.get_endpoint("/execute")
        assert ep is not None
        assert ep.method == "POST"

    def test_has_health_endpoint(self):
        api = APIContract()
        ep = api.get_endpoint("/health")
        assert ep is not None

    def test_to_dict_complete(self):
        api = APIContract()
        d = api.to_dict()
        assert "base_url" in d
        assert "endpoints" in d
        assert len(d["endpoints"]) >= 3


class TestEventContract:
    def test_emit_valid_event(self):
        ec = EventContract()
        event = ec.emit(EventType.EXECUTION_STARTED.value, "trace-123", {"key": "val"})
        assert event.event_type == EventType.EXECUTION_STARTED.value
        assert event.trace_id == "trace-123"

    def test_emit_invalid_event_raises(self):
        ec = EventContract()
        with pytest.raises(ValueError):
            ec.emit("invalid.event.type", "trace-123")

    def test_event_query_by_type(self):
        ec = EventContract()
        ec.emit(EventType.EXECUTION_STARTED.value, "trace-1")
        ec.emit(EventType.EXECUTION_COMPLETED.value, "trace-1")
        ec.emit(EventType.EXECUTION_STARTED.value, "trace-2")
        started = ec.get_events(event_type=EventType.EXECUTION_STARTED.value)
        assert len(started) == 2

    def test_event_query_by_trace(self):
        ec = EventContract()
        ec.emit(EventType.EXECUTION_STARTED.value, "trace-A")
        ec.emit(EventType.EXECUTION_COMPLETED.value, "trace-A")
        ec.emit(EventType.EXECUTION_STARTED.value, "trace-B")
        trace_a = ec.get_events(trace_id="trace-A")
        assert len(trace_a) == 2

    def test_listener_called(self):
        ec = EventContract()
        received = []
        ec.register_listener(lambda e: received.append(e))
        ec.emit(EventType.HEALTH_CHECK.value, "t1")
        assert len(received) == 1


class TestAttachmentContract:
    def test_valid_modes(self):
        ac = AttachmentContract()
        assert ac.validate_mode("LOCAL")
        assert ac.validate_mode("REMOTE")
        assert ac.validate_mode("HYBRID")

    def test_invalid_mode(self):
        ac = AttachmentContract()
        assert not ac.validate_mode("UNKNOWN")

    def test_negotiate_valid(self):
        ac = AttachmentContract()
        assert ac.negotiate("REMOTE") == "REMOTE"

    def test_negotiate_fallback(self):
        ac = AttachmentContract()
        assert ac.negotiate("INVALID") == "LOCAL"


class TestConsumerCompatibility:
    def test_valid_request(self):
        cc = ConsumerCompatibility()
        valid, errors = cc.validate({"problem_type": "MILP"})
        assert valid
        assert len(errors) == 0

    def test_missing_required_field(self):
        cc = ConsumerCompatibility()
        valid, errors = cc.validate({"some_other_field": "value"})
        assert not valid
        assert len(errors) > 0


class TestProducerCompatibility:
    def test_valid_output(self):
        pc = ProducerCompatibility()
        output = {
            "trace_id": "t1",
            "replay_id": "r1",
            "status": "COMPLETED",
            "provenance": {},
            "result": {},
        }
        valid, errors = pc.validate(output)
        assert valid

    def test_missing_trace_id(self):
        pc = ProducerCompatibility()
        output = {"replay_id": "r1", "status": "OK", "provenance": {}, "result": {}}
        valid, errors = pc.validate(output)
        assert not valid


class TestEvidenceChain:
    def test_append_and_verify(self):
        chain = EvidenceChain()
        chain.append({"trace_id": "t1", "replay_id": "r1", "status": "OK"})
        chain.append({"trace_id": "t2", "replay_id": "r2", "status": "OK"})
        assert chain.chain_length == 2
        assert chain.verify()

    def test_tamper_detection(self):
        chain = EvidenceChain()
        chain.append({"trace_id": "t1", "replay_id": "r1", "status": "OK"})
        chain.append({"trace_id": "t2", "replay_id": "r2", "status": "OK"})

        # Tamper with the chain
        chain._chain[0]["status"] = "TAMPERED"
        assert not chain.verify()

    def test_empty_chain_valid(self):
        chain = EvidenceChain()
        assert chain.verify()
        assert chain.chain_length == 0

    def test_hash_continuity(self):
        chain = EvidenceChain()
        e1 = chain.append({"trace_id": "t1", "replay_id": "r1", "status": "OK"})
        e2 = chain.append({"trace_id": "t2", "replay_id": "r2", "status": "OK"})
        assert e2["previous_evidence_hash"] == e1["evidence_hash"]


class TestFailureBehaviour:
    def test_create_failure_evidence(self):
        fb = FailureBehaviour()
        evidence = fb.create_failure_evidence(
            FailureCode.CAPABILITY_MISMATCH,
            "trace-123",
            "No solver for NLP",
        )
        assert evidence["status"] == "FAILED"
        assert evidence["failure_code"] == "HALT:CAPABILITY_MISMATCH"
        assert evidence["trace_id"] == "trace-123"
        assert "provenance" in evidence


# ===========================================================================
# INTEGRATION TESTS — Registry Participation
# ===========================================================================

class TestRegistryParticipation:
    def test_register_all_five_registries(self):
        participant = SolverFabricRegistryParticipant()
        result = participant.register_all()

        assert result["total_registrations"] == 5
        assert result["evidence_chain_valid"]

        for key in ["capability_registry", "runtime_registry", "replay_registry",
                     "build_registry", "review_registry"]:
            assert result["registrations"][key]["status"] == "REGISTERED"

    def test_deterministic_registration(self):
        """Two registrations produce the same IDs."""
        p1 = SolverFabricRegistryParticipant()
        p2 = SolverFabricRegistryParticipant()

        r1 = p1.register_all()
        r2 = p2.register_all()

        assert r1["registrations"]["capability_registry"]["id"] == r2["registrations"]["capability_registry"]["id"]
        assert r1["registrations"]["runtime_registry"]["id"] == r2["registrations"]["runtime_registry"]["id"]

    def test_retrieval_after_registration(self):
        participant = SolverFabricRegistryParticipant()
        participant.register_all()

        assert participant.retrieve_capability() is not None
        assert participant.retrieve_runtime() is not None
        assert participant.retrieve_replay() is not None
        assert participant.retrieve_build() is not None
        assert participant.retrieve_review() is not None

    def test_capability_payload_structure(self):
        payload = build_capability_registry_payload()
        required_keys = [
            "capability_id", "capability_name", "owner", "version",
            "status", "scope", "dependencies", "attachment_rules",
            "authority_limits", "inputs", "outputs", "consumers",
            "documentation_reference",
        ]
        for key in required_keys:
            assert key in payload, f"Missing key: {key}"

    def test_platform_service_payload_structure(self):
        payload = build_platform_service_payload()
        assert payload["platform_service_id"] == RUNTIME_ID
        assert "manifest" in payload
        assert "version_matrix" in payload
        assert "constitutional_identity" in payload

    def test_registration_evidence_generated(self):
        participant = SolverFabricRegistryParticipant()
        participant.register_all()
        evidence = participant.get_registration_evidence()
        assert len(evidence) == 5
        for e in evidence:
            assert e["status"] == "REGISTERED"
            assert e["evidence_hash"] != ""


# ===========================================================================
# RUNTIME TESTS — Full Lifecycle
# ===========================================================================

class TestRuntimeLifecycle:
    def test_full_lifecycle_register_discover_execute_evidence(self):
        """Full lifecycle: register → discover → negotiate → invoke → execute → evidence → replay."""
        contract = ConstitutionalRuntimeContract()

        # 1. Register
        participant = SolverFabricRegistryParticipant(contract=contract)
        reg_result = participant.register_all()
        assert reg_result["total_registrations"] == 5

        # 2. Discover (retrieve registration)
        cap = participant.retrieve_capability()
        assert cap is not None
        assert cap["capability_id"] == CAPABILITY_ID

        # 3. Negotiate version
        status, version = contract.negotiate_version("1.0.0")
        assert status == VersionCompatibility.COMPATIBLE

        # 4. Validate consumer request
        request = {"problem_type": "MILP", "required_constraints": ["LINEAR"]}
        valid, errors = contract.validate_consumer_request(request)
        assert valid

        # 5. Negotiate attachment
        mode = contract.negotiate_attachment("LOCAL")
        assert mode == "LOCAL"

        # 6. Simulate execution evidence
        evidence = {
            "trace_id": str(uuid.uuid4()),
            "replay_id": str(uuid.uuid4()),
            "status": "COMPLETED",
            "provenance": {
                "fabric_version": FABRIC_VERSION,
                "solver_id": "TEST_SOLVER",
                "solver_version": "1.0.0",
            },
            "deterministic_inputs": {"problem_type": "MILP"},
            "result": {"objective_value": 42.0},
        }

        # 7. Record in evidence chain
        chained = contract.record_evidence(evidence)
        assert "evidence_hash" in chained

        # 8. Validate output
        valid, errors = contract.validate_execution_output(evidence)
        assert valid

        # 9. Verify chain
        assert contract.verify_evidence_chain()

        # 10. Emit events
        contract.emit_event(EventType.EXECUTION_COMPLETED.value, evidence["trace_id"])

    def test_observability_during_lifecycle(self):
        contract = ConstitutionalRuntimeContract()
        obs = SolverFabricObservability(contract=contract)

        # Execute and record
        trace = obs.record_execution(
            trace_id=str(uuid.uuid4()),
            replay_id=str(uuid.uuid4()),
            solver_id="TEST_SOLVER_01",
            problem_type="MILP",
            status="COMPLETED",
            execution_duration_ms=150.0,
            solver_version="1.0.0",
        )

        assert trace.sequence == 1
        assert obs.trace_count == 1
        assert obs.get_health()["status"] in ("HEALTHY", "UNHEALTHY")

        # Log consumer invocation
        inv = obs.log_consumer_invocation(
            consumer_id="test-consumer",
            operation="execute_optimization",
            request_payload={"problem_type": "MILP"},
            response_status="COMPLETED",
            duration_ms=150.0,
            trace_id=trace.trace_id,
        )
        assert obs.consumer_count == 1


# ===========================================================================
# REPLAY VALIDATION
# ===========================================================================

class TestReplayValidation:
    def test_replay_chain_across_executions(self):
        contract = ConstitutionalRuntimeContract()
        obs = SolverFabricObservability(contract=contract)

        # Multiple executions
        for i in range(5):
            obs.record_execution(
                trace_id=str(uuid.uuid4()),
                replay_id=str(uuid.uuid4()),
                solver_id=f"SOLVER_{i}",
                problem_type="MILP",
                status="COMPLETED",
                execution_duration_ms=100.0 + i * 10,
            )

        chain = obs.export_replay_chain()
        assert len(chain) == 5
        # Verify sequence ordering
        for i, entry in enumerate(chain):
            assert entry["sequence"] == i + 1

    def test_evidence_chain_integrity(self):
        contract = ConstitutionalRuntimeContract()

        for i in range(10):
            contract.record_evidence({
                "trace_id": str(uuid.uuid4()),
                "replay_id": str(uuid.uuid4()),
                "status": "COMPLETED",
            })

        assert contract.verify_evidence_chain()
        assert contract.evidence_chain.chain_length == 10

    def test_replay_guarantee_validation(self):
        from constitutional_runtime_contract import REPLAY_GUARANTEE

        valid_evidence = {
            "trace_id": "t1",
            "replay_id": "r1",
            "deterministic_inputs": {"type": "MILP"},
            "provenance": {
                "fabric_version": "1.0.0",
                "solver_id": "S1",
                "solver_version": "1.0.0",
            },
        }
        valid, errors = REPLAY_GUARANTEE.validate_evidence(valid_evidence)
        assert valid

        invalid_evidence = {"trace_id": "t1"}
        valid, errors = REPLAY_GUARANTEE.validate_evidence(invalid_evidence)
        assert not valid
        assert len(errors) > 0


# ===========================================================================
# VERSION NEGOTIATION TESTS
# ===========================================================================

class TestVersionNegotiationIntegration:
    def test_compatible_path(self):
        contract = ConstitutionalRuntimeContract()
        status, ver = contract.negotiate_version("1.0.0")
        assert status == VersionCompatibility.COMPATIBLE

    def test_deprecated_path(self):
        status, ver = negotiate_version("1.5.0", ["1.0.0"])
        assert status == VersionCompatibility.DEPRECATED

    def test_unsupported_path(self):
        status, ver = negotiate_version("3.0.0", ["1.0.0", "2.0.0"])
        assert status == VersionCompatibility.UNSUPPORTED

    def test_multiple_supported_versions(self):
        status, ver = negotiate_version("1.0.0", ["1.0.0", "1.1.0", "1.2.0"])
        assert status == VersionCompatibility.COMPATIBLE


# ===========================================================================
# FAILURE RECOVERY TESTS
# ===========================================================================

class TestFailureRecovery:
    def test_graceful_failure_evidence(self):
        contract = ConstitutionalRuntimeContract()
        failure = contract.create_failure(
            FailureCode.CAPABILITY_MISMATCH,
            "trace-fail-1",
            "No solver supports NLP",
        )
        assert failure["status"] == "FAILED"
        assert failure["failure_code"] == "HALT:CAPABILITY_MISMATCH"
        assert "provenance" in failure

    def test_failure_recorded_in_observability(self):
        obs = SolverFabricObservability()
        failure = obs.record_failure(
            trace_id="trace-fail-2",
            failure_code="HALT:ENGINE_CRASH",
            failure_detail="Solver segfault",
            solver_id="BROKEN_SOLVER",
            problem_type="MILP",
        )
        assert obs.failure_count == 1
        assert failure.failure_code == "HALT:ENGINE_CRASH"

    def test_failure_execution_recorded(self):
        obs = SolverFabricObservability()
        obs.record_execution(
            trace_id=str(uuid.uuid4()),
            replay_id=str(uuid.uuid4()),
            solver_id="FAILING_SOLVER",
            problem_type="MILP",
            status="FAILED",
            execution_duration_ms=50.0,
            failure_code="HALT:TIMEOUT",
            failure_detail="Exceeded 60s limit",
        )
        metrics = obs.get_metrics()
        assert metrics["executions_failed"] == 1
        assert metrics["failure_rate"] == 1.0

    def test_circuit_breaker_concept(self):
        """Verify failure rate triggers DEGRADED health."""
        obs = SolverFabricObservability()
        obs.update_solver_count(1)

        # 6 failures, 4 successes = 60% failure rate → DEGRADED
        for i in range(10):
            obs.record_execution(
                trace_id=str(uuid.uuid4()),
                replay_id=str(uuid.uuid4()),
                solver_id="FLAKY_SOLVER",
                problem_type="MILP",
                status="FAILED" if i < 6 else "COMPLETED",
                execution_duration_ms=100.0,
            )

        health = obs.get_health()
        assert health["status"] == "DEGRADED"


# ===========================================================================
# MULTI-PARTICIPANT RUNTIME TESTS
# ===========================================================================

class TestMultiParticipantRuntime:
    def test_solver_to_gateway_bridge(self):
        """Test Solver Fabric → Gateway communication (requires gateway.py imports)."""
        try:
            from fabric_gateway_bridge import SolverFabricGatewayBridge

            bridge = SolverFabricGatewayBridge()

            solver_evidence = {
                "trace_id": str(uuid.uuid4()),
                "replay_id": str(uuid.uuid4()),
                "status": "COMPLETED",
                "provenance": {
                    "fabric_version": FABRIC_VERSION,
                    "solver_id": "TEST_SOLVER",
                    "solver_version": "1.0.0",
                    "attachment_mode": "LOCAL",
                },
                "result": {"objective_value": 42.0, "decision_variables": {"x": 1}},
            }

            result = bridge.route_solver_result(solver_evidence)

            assert "bridge_evidence" in result
            assert "gateway_response" in result
            assert result["bridge_evidence"]["solver_trace_id"] == solver_evidence["trace_id"]
            assert result["gateway_response"]["source_type"] == "CLASSICAL"

        except ImportError:
            pytest.skip("Gateway dependencies not available")

    def test_trust_validation_via_gateway(self):
        """Test trust validation through gateway replay authority."""
        try:
            from fabric_gateway_bridge import SolverFabricGatewayBridge

            bridge = SolverFabricGatewayBridge()

            evidence = {
                "trace_id": str(uuid.uuid4()),
                "replay_id": str(uuid.uuid4()),
                "status": "COMPLETED",
                "result": {"value": 1},
            }

            trust_result = bridge.validate_trust(evidence)
            assert "trust_validated" in trust_result
            assert "transport_status" in trust_result

        except ImportError:
            pytest.skip("Gateway dependencies not available")

    def test_replay_continuity_across_participants(self):
        """Test replay continuity across solver + gateway."""
        try:
            from fabric_gateway_bridge import SolverFabricGatewayBridge

            bridge = SolverFabricGatewayBridge()

            evidence_list = [
                {
                    "trace_id": str(uuid.uuid4()),
                    "replay_id": str(uuid.uuid4()),
                    "status": "COMPLETED",
                    "result": {"value": i},
                }
                for i in range(3)
            ]

            result = bridge.validate_replay_continuity(evidence_list)
            assert result["executions_processed"] == 3
            assert result["evidence_chain_valid"]

        except ImportError:
            pytest.skip("Gateway dependencies not available")

    def test_quantum_runtime_integration(self):
        """Test quantum solver adapter."""
        try:
            from fabric_quantum_runtime import LiveQuantumSolverAdapter

            adapter = LiveQuantumSolverAdapter(seed=42)
            adapter.bind_problem({"problem_type": "QUBO", "max_variables": 5})
            result = adapter.execute()

            assert "status" in result
            assert "solution" in result
            assert "replay_metadata" in result
            assert "execution_metadata" in result

        except ImportError:
            pytest.skip("Quantum runtime dependencies not available")

    def test_full_three_participant_flow(self):
        """
        Full 3-participant flow:
        Solver Registry → Solver Execution → Gateway Bridge → Evidence
        """
        contract = ConstitutionalRuntimeContract()
        obs = SolverFabricObservability(contract=contract)

        # 1. Registry participation
        participant = SolverFabricRegistryParticipant(contract=contract)
        reg_result = participant.register_all()
        assert reg_result["total_registrations"] == 5

        # 2. Simulate solver execution
        trace_id = str(uuid.uuid4())
        replay_id = str(uuid.uuid4())

        execution_evidence = {
            "trace_id": trace_id,
            "replay_id": replay_id,
            "status": "COMPLETED",
            "provenance": {
                "fabric_version": FABRIC_VERSION,
                "solver_id": "ORTOOLS_CP_SAT_01",
                "solver_version": "1.0.0",
                "attachment_mode": "LOCAL",
            },
            "deterministic_inputs": {
                "problem_type": "MILP",
                "constraints_applied": ["LINEAR"],
            },
            "result": {
                "objective_value": 42.0,
                "decision_variables": {"x1": 1, "x2": 0},
            },
        }

        # 3. Record in observability
        obs.update_solver_count(1)
        trace = obs.record_execution(
            trace_id=trace_id,
            replay_id=replay_id,
            solver_id="ORTOOLS_CP_SAT_01",
            problem_type="MILP",
            status="COMPLETED",
            execution_duration_ms=150.0,
            solver_version="1.0.0",
        )
        assert trace.sequence == 1

        # 4. Try gateway bridge
        try:
            from fabric_gateway_bridge import SolverFabricGatewayBridge
            bridge = SolverFabricGatewayBridge(contract=contract)
            bridge_result = bridge.route_solver_result(execution_evidence)
            assert bridge_result["bridge_evidence"]["status"] in ("COMPLETED", "DEGRADED")
        except ImportError:
            pass  # Gateway not available

        # 5. Verify evidence chain integrity
        assert contract.verify_evidence_chain()

        # 6. Export full proof
        proof = obs.export_full_proof()
        assert proof["metrics"]["executions_total"] == 1
        assert proof["evidence_chain"]["valid"]


# ===========================================================================
# COMPOSITE CONTRACT TESTS
# ===========================================================================

class TestConstitutionalRuntimeContract:
    def test_identity(self):
        contract = ConstitutionalRuntimeContract()
        identity = contract.get_identity()
        assert identity["runtime_id"] == RUNTIME_ID
        assert identity["capability_id"] == CAPABILITY_ID
        assert identity["permanent_identity"] == PERMANENT_IDENTITY

    def test_manifest_export(self):
        contract = ConstitutionalRuntimeContract()
        manifest = contract.to_manifest()
        assert "identity" in manifest
        assert "authority_matrix" in manifest
        assert "runtime_contract" in manifest
        assert "api_contract" in manifest
        assert "event_contract" in manifest
        assert "replay_guarantees" in manifest
        assert "deterministic_guarantees" in manifest

    def test_full_workflow(self):
        contract = ConstitutionalRuntimeContract()

        # Validate request
        valid, errors = contract.validate_consumer_request({"problem_type": "CP"})
        assert valid

        # Negotiate version
        status, ver = contract.negotiate_version("1.0.0")
        assert status == VersionCompatibility.COMPATIBLE

        # Negotiate attachment
        mode = contract.negotiate_attachment("REMOTE")
        assert mode == "REMOTE"

        # Record evidence
        ev = contract.record_evidence({
            "trace_id": "t1", "replay_id": "r1", "status": "COMPLETED"
        })
        assert "evidence_hash" in ev

        # Emit event
        event = contract.emit_event(
            EventType.EXECUTION_COMPLETED.value, "t1", {"solver": "test"}
        )
        assert event.event_type == EventType.EXECUTION_COMPLETED.value

        # Verify chain
        assert contract.verify_evidence_chain()
