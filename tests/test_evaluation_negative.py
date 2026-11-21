"""
tests/test_evaluation_negative.py — Negative & Adversarial Tests for Parikshak Runtime
Task ID: T-GOV-002
Standard: Governed Operational System (Gov-OS) Core Compliance

Validates:
1. Rejection of malformed, incomplete, or corrupted inbound payloads
2. Zero unhandled 500 exceptions across adversarial inputs
3. Detection and rejection of forbidden patterns (HTTP 400 ErrorEnvelope)
4. Schema bounds enforcement (extra fields, negative scores, out-of-range weights)
5. Structured ErrorEnvelope response contracts from exception handlers
"""

import pytest
import json
from pydantic import ValidationError
from contracts.schemas import (
    ReviewSubmissionPayload,
    CriterionInput,
    CriterionCategory,
    AutomatedTestSummary,
    ErrorEnvelope,
)
from evaluation_engine.rule_engine import (
    EvaluationEngine,
    GovOSPolicyViolationException,
)
from main import (
    validation_exception_handler,
    govos_violation_handler,
    generic_exception_boundary,
)


class TestEvaluationNegativeSuite:

    def test_missing_mandatory_fields_rejected_by_schema(self):
        """Omitting required fields must raise ValidationError and produce a 422 ErrorEnvelope."""
        incomplete_dict = {
            "task_id": "T-GOV-002",
            # Missing candidate_id, candidate_name, criteria, test_summary
        }
        with pytest.raises(ValidationError) as excinfo:
            ReviewSubmissionPayload.model_validate(incomplete_dict)

        # Pass exception through the FastAPI exception handler
        response = validation_exception_handler(None, excinfo.value)
        assert response.status_code == 422
        body = json.loads(response.body.decode())
        assert body["status"] == "error"
        assert body["error_type"] == "VALIDATION_ERROR"
        assert body["status_code"] == 422
        assert "details" in body

    def test_forbidden_extra_fields_rejected_by_schema(self):
        """Extra undeclared fields must be rejected (ConfigDict extra='forbid')."""
        payload_with_extra = {
            "task_id": "T-GOV-002",
            "candidate_id": "user-kanishk-singh",
            "candidate_name": "Kanishk Singh",
            "submission_timestamp": "2026-11-21T12:00:00Z",
            "criteria": [],
            "test_summary": {
                "total_tests": 10,
                "passed_tests": 10,
                "pass_rate": 100.0
            },
            "unauthorized_backdoor_field": "exploit_attempt"
        }
        with pytest.raises(ValidationError) as excinfo:
            ReviewSubmissionPayload.model_validate(payload_with_extra)

        response = validation_exception_handler(None, excinfo.value)
        assert response.status_code == 422
        body = json.loads(response.body.decode())
        assert body["error_type"] == "VALIDATION_ERROR"

    def test_negative_or_overflow_score_bounds(self):
        """Scores outside [0, 100] must fail validation."""
        bad_score_dict = {
            "name": "Criterion 1",
            "category": "Architectural Modularity",
            "weight": 50.0,
            "score": 150.0,  # Invalid: > 100
            "pass_threshold": 70.0
        }
        with pytest.raises(ValidationError) as excinfo:
            CriterionInput.model_validate(bad_score_dict)

        response = validation_exception_handler(None, excinfo.value)
        assert response.status_code == 422

    def test_forbidden_pattern_workflow_execution_engine_returns_400(self):
        """Inbound payload attempting forbidden pattern must return HTTP 400 ErrorEnvelope."""
        payload = ReviewSubmissionPayload(
            task_id="T-GOV-002",
            candidate_id="user-kanishk-singh",
            candidate_name="Kanishk Singh",
            submission_timestamp="2026-11-21T12:00:00Z",
            criteria=[
                CriterionInput(
                    name="Architectural Modularity",
                    category=CriterionCategory.ARCHITECTURAL_MODULARITY,
                    weight=100.0,
                    score=90.0,
                    pass_threshold=70.0,
                    details="Using workflow_execution_engine inside pipeline."
                )
            ],
            test_summary=AutomatedTestSummary(
                total_tests=10,
                passed_tests=10,
                failed_tests=0,
                skipped_tests=0,
                pass_rate=100.0
            )
        )
        engine = EvaluationEngine()
        with pytest.raises(GovOSPolicyViolationException) as excinfo:
            engine.evaluate_submission(payload)

        # Verify govos_violation_handler produces structured 400
        response = govos_violation_handler(None, excinfo.value)
        assert response.status_code == 400
        body = json.loads(response.body.decode())
        assert body["error_type"] == "GOV_OS_SECURITY_POLICY_VIOLATION"
        assert "workflow_execution_engine" in body["message"]

    def test_forbidden_pattern_direct_masterdb_schema_mutation_returns_400(self):
        """Inbound payload with direct_masterdb_schema_mutation must return HTTP 400."""
        payload = ReviewSubmissionPayload(
            task_id="T-GOV-002",
            candidate_id="user-kanishk-singh",
            candidate_name="Kanishk Singh",
            submission_timestamp="2026-11-21T12:00:00Z",
            criteria=[
                CriterionInput(
                    name="Architectural Modularity",
                    category=CriterionCategory.ARCHITECTURAL_MODULARITY,
                    weight=100.0,
                    score=90.0,
                    pass_threshold=70.0,
                    details="Direct schema change."
                )
            ],
            test_summary=AutomatedTestSummary(
                total_tests=10,
                passed_tests=10,
                failed_tests=0,
                skipped_tests=0,
                pass_rate=100.0
            ),
            code_packets=[{"injection": "direct_masterdb_schema_mutation"}]
        )
        engine = EvaluationEngine()
        with pytest.raises(GovOSPolicyViolationException) as excinfo:
            engine.evaluate_submission(payload)

        response = govos_violation_handler(None, excinfo.value)
        assert response.status_code == 400
        body = json.loads(response.body.decode())
        assert body["error_type"] == "GOV_OS_SECURITY_POLICY_VIOLATION"
        assert "direct_masterdb_schema_mutation" in body["message"]

    def test_generic_exception_boundary_zero_unhandled_500s(self):
        """Any unhandled exception at runtime must be caught by boundary and return structured 400, never 500."""
        unexpected_error = RuntimeError("Unexpected internal state simulation")
        response = generic_exception_boundary(None, unexpected_error)

        assert response.status_code == 400
        body = json.loads(response.body.decode())
        assert body["status"] == "error"
        assert body["error_type"] == "RUNTIME_ERROR_BOUNDARY"
        assert "Unexpected internal state simulation" in body["message"]
        assert body["status_code"] == 400
