"""
tests/test_evaluation_engine_unit.py — Unit Tests for Parikshak Evaluation Engine
Task ID: T-GOV-002
Standard: Governed Operational System (Gov-OS) Core Compliance

Validates:
1. Schema instantiation and validation rules
2. Scoring weight normalization and weighted composite calculation
3. State machine deterministic transitions
4. Detection and rejection of forbidden patterns (GC Shakti audit)
5. Verdict generation (PASS / FAIL)
"""

import pytest
from contracts.schemas import (
    ReviewSubmissionPayload,
    CriterionInput,
    CriterionCategory,
    TestSummary,
    VerdictEnum,
    EvaluationState,
)
from evaluation_engine.rule_engine import (
    EvaluationEngine,
    GovOSPolicyViolationException,
    GCShaktiPolicyAuthority,
    NiyantranTaskAssignmentOrchestrator,
)


@pytest.fixture
def valid_submission_payload():
    return ReviewSubmissionPayload(
        task_id="T-GOV-002",
        candidate_id="user-kanishk-singh",
        candidate_name="Kanishk Singh",
        target_product="Parikshak Engineering Review Runtime",
        submission_timestamp="2026-11-21T12:00:00Z",
        review_packet_path="review_packets/REVIEW_PACKET.md",
        criteria=[
            CriterionInput(
                name="Architectural Modularity",
                category=CriterionCategory.ARCHITECTURAL_MODULARITY,
                weight=25.0,
                score=100.0,
                pass_threshold=70.0,
                details="Clean separation between contracts, domain engine, and API layer."
            ),
            CriterionInput(
                name="Gov-OS Core Compliance",
                category=CriterionCategory.GOV_OS_COMPLIANCE,
                weight=25.0,
                score=100.0,
                pass_threshold=80.0,
                details="Zero forbidden patterns, strict error boundaries, immutable state hashing."
            ),
            CriterionInput(
                name="Test & Verification Matrix",
                category=CriterionCategory.TEST_VERIFICATION_MATRIX,
                weight=25.0,
                score=100.0,
                pass_threshold=80.0,
                details="5-Tier automated verification with 100% pass rate."
            ),
            CriterionInput(
                name="Runtime Evidence Grounding",
                category=CriterionCategory.RUNTIME_EVIDENCE_GROUNDING,
                weight=25.0,
                score=100.0,
                pass_threshold=70.0,
                details="50-run identical state hash evidence and immutable audit records."
            ),
        ],
        test_summary=TestSummary(
            total_tests=35,
            passed_tests=35,
            failed_tests=0,
            skipped_tests=0,
            pass_rate=100.0
        ),
        code_packets=[
            {"name": "Rule Engine", "path": "evaluation_engine/rule_engine.py"},
            {"name": "Schemas Contract", "path": "contracts/schemas.py"},
            {"name": "Runtime Server", "path": "main.py"}
        ],
        metadata={"build_env": "production_govos", "tier": "L1_AUDIT"}
    )


class TestEvaluationEngineUnit:

    def test_engine_initialization_state(self):
        engine = EvaluationEngine()
        assert engine.state == EvaluationState.INITIALIZED
        assert len(engine.transition_history) == 0

    def test_successful_evaluation_verdict(self, valid_submission_payload):
        engine = EvaluationEngine()
        verdict = engine.evaluate_submission(valid_submission_payload)

        assert verdict.verdict == VerdictEnum.PASS
        assert verdict.total_score == 100.0
        assert len(verdict.criteria_results) == 4
        assert all(cr.passed for cr in verdict.criteria_results)
        assert len(verdict.deterministic_state_hash) == 64
        assert verdict.governance_compliance["gov_os_core_compliance"] is True

    def test_state_machine_transitions(self, valid_submission_payload):
        engine = EvaluationEngine()
        verdict = engine.evaluate_submission(valid_submission_payload)

        states = [entry["to_state"] for entry in verdict.state_machine_history]
        expected_sequence = [
            EvaluationState.INPUT_VALIDATED.value,
            EvaluationState.GOV_OS_AUDIT.value,
            EvaluationState.RULES_APPLIED.value,
            EvaluationState.HASH_COMPUTED.value,
            EvaluationState.VERIFIED.value,
            EvaluationState.COMPLETED.value,
        ]
        assert states == expected_sequence

    def test_failing_verdict_when_score_below_threshold(self, valid_submission_payload):
        # Alter one score below pass threshold
        valid_submission_payload.criteria[0].score = 45.0
        engine = EvaluationEngine()
        verdict = engine.evaluate_submission(valid_submission_payload)

        assert verdict.verdict == VerdictEnum.FAIL
        assert verdict.criteria_results[0].passed is False

    def test_forbidden_pattern_detection_workflow_execution_engine(self, valid_submission_payload):
        valid_submission_payload.metadata["forbidden_attr"] = "workflow_execution_engine"
        engine = EvaluationEngine()

        with pytest.raises(GovOSPolicyViolationException) as excinfo:
            engine.evaluate_submission(valid_submission_payload)
        assert "FORBIDDEN_PATTERN_DETECTED" in str(excinfo.value)
        assert "workflow_execution_engine" in str(excinfo.value)

    def test_forbidden_pattern_detection_direct_masterdb_mutation(self, valid_submission_payload):
        valid_submission_payload.code_packets.append({"action": "direct_masterdb_schema_mutation"})
        engine = EvaluationEngine()

        with pytest.raises(GovOSPolicyViolationException) as excinfo:
            engine.evaluate_submission(valid_submission_payload)
        assert "FORBIDDEN_PATTERN_DETECTED" in str(excinfo.value)
        assert "direct_masterdb_schema_mutation" in str(excinfo.value)

    def test_gc_shakti_policy_audit(self, valid_submission_payload):
        is_compliant, violations = GCShaktiPolicyAuthority.audit_submission(valid_submission_payload)
        assert is_compliant is True
        assert len(violations) == 0

    def test_niyantran_canonical_next_task_retrieval(self):
        assignment = NiyantranTaskAssignmentOrchestrator.get_canonical_assignment(
            task_id="T-GOV-002",
            candidate_id="user-kanishk-singh",
            candidate_name="Kanishk Singh",
            evaluation_timestamp="2026-11-21T12:00:00Z"
        )
        assert assignment.assigned_task_id == "T-GOV-003"
        assert assignment.target_product == "Parikshak Engineering Review Runtime (PARIKSHAK)"
        assert len(assignment.phase_specifications) == 4
        assert assignment.zero_context_switch_ready is True

    def test_deterministic_hash_calculation(self):
        engine = EvaluationEngine()
        payload = {"b_key": "second", "a_key": "first", "c_num": 42.0}
        hash1 = engine.compute_deterministic_state_hash(payload)
        hash2 = engine.compute_deterministic_state_hash({"c_num": 42.0, "a_key": "first", "b_key": "second"})
        assert hash1 == hash2
        assert len(hash1) == 64
