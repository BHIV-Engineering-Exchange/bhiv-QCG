"""
tests/test_evaluation_engine_integration.py — Integration Tests for Parikshak Runtime Endpoints
Task ID: T-GOV-002
Standard: Governed Operational System (Gov-OS) Core Compliance

Validates:
1. End-to-end API route execution (/health, /status, /evaluate, /verify, /assign-task, /audit)
2. Inbound/Outbound v1.0 payload handling and serialization
3. Verification endpoint cryptographic parity
4. Zero-context-switch Niyantran task assignment route
"""

import pytest
from contracts.schemas import (
    ReviewSubmissionPayload,
    CriterionInput,
    CriterionCategory,
    AutomatedTestSummary,
    VerificationRequest,
    VerdictEnum,
)
from main import (
    health_check,
    runtime_status,
    evaluate_submission,
    verify_verdict,
    assign_canonical_next_task,
    get_audit_trail,
)


@pytest.fixture
def sample_submission_payload():
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
                details="Modularity verified."
            ),
            CriterionInput(
                name="Gov-OS Core Compliance",
                category=CriterionCategory.GOV_OS_COMPLIANCE,
                weight=25.0,
                score=100.0,
                pass_threshold=80.0,
                details="Gov-OS compliance verified."
            ),
            CriterionInput(
                name="Test & Verification Matrix",
                category=CriterionCategory.TEST_VERIFICATION_MATRIX,
                weight=25.0,
                score=100.0,
                pass_threshold=80.0,
                details="All test tiers passed."
            ),
            CriterionInput(
                name="Runtime Evidence Grounding",
                category=CriterionCategory.RUNTIME_EVIDENCE_GROUNDING,
                weight=25.0,
                score=100.0,
                pass_threshold=70.0,
                details="Evidence verified."
            )
        ],
        test_summary=AutomatedTestSummary(
            total_tests=40,
            passed_tests=40,
            failed_tests=0,
            skipped_tests=0,
            pass_rate=100.0
        ),
        code_packets=[
            {"module": "evaluation_engine", "version": "1.0.0"}
        ],
        metadata={"environment": "production_govos"}
    )


class TestEvaluationIntegrationSuite:

    def test_health_endpoints(self):
        data = health_check()
        assert data["status"] == "UP"
        assert data["task_id"] == "T-GOV-002"
        assert data["service"] == "Parikshak Engineering Review Runtime"
        assert data["standard"] == "Governed Operational System (Gov-OS) core compliance"

    def test_status_endpoint(self):
        data = runtime_status()
        assert data["runtime_status"] == "OPERATIONAL"
        assert "GC_Shakti" in data["ecosystem_connectivity"]
        assert "Niyantran" in data["ecosystem_connectivity"]
        assert "Gov_OS" in data["ecosystem_connectivity"]
        assert "Saarthi" in data["ecosystem_connectivity"]
        assert data["engine_invariants"]["v1_schema_enforced"] is True

    def test_evaluate_endpoint_success(self, sample_submission_payload):
        verdict = evaluate_submission(sample_submission_payload)
        assert verdict.schema_version == "1.0"
        assert verdict.verdict == VerdictEnum.PASS
        assert verdict.total_score == 100.0
        assert len(verdict.deterministic_state_hash) == 64
        assert verdict.candidate_name == "Kanishk Singh"
        assert verdict.governance_compliance["gov_os_core_compliance"] is True

    def test_verify_endpoint_valid_hash(self, sample_submission_payload):
        verdict = evaluate_submission(sample_submission_payload)
        req = VerificationRequest(
            verdict_payload=verdict,
            expected_state_hash=verdict.deterministic_state_hash
        )
        vdata = verify_verdict(req)
        assert vdata.verified is True
        assert vdata.deterministic_match is True
        assert vdata.gov_os_compliant is True

    def test_assign_canonical_next_task_endpoint(self):
        payload = {
            "task_id": "T-GOV-002",
            "candidate_id": "user-kanishk-singh",
            "candidate_name": "Kanishk Singh"
        }
        data = assign_canonical_next_task(payload)
        assert data.assigned_task_id == "T-GOV-003"
        assert data.candidate_name == "Kanishk Singh"
        assert data.zero_context_switch_ready is True
        assert len(data.phase_specifications) == 4
        assert data.phase_specifications[0]["checkpoint_minute"] == 60

    def test_audit_trail_endpoint(self, sample_submission_payload):
        evaluate_submission(sample_submission_payload)
        audit = get_audit_trail()
        assert audit["total_records"] >= 1
        assert "audit_records" in audit
