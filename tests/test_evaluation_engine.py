"""5-Tier Test Suite for PARIKSHAK Evaluation Engine (Gov-OS Core Compliance).

Tiers:
1. Unit Tests (Contracts & Schemas)
2. Integration Tests (Full Evaluation & ReportLab PDF Generation)
3. Negative & Security Tests (Forbidden Patterns & Zero 500 Exceptions)
4. Determinism Standard (50-Run Bit-Identical SHA-256 Verdict Hash Verification)
5. Regression & Health Tests
"""

import copy
import json
import os
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from contracts.schemas import (
    EvaluationCriteriaCheck,
    EvaluationRequest,
    EvaluationRuleCategory,
    EvaluationRuleItem,
    EvaluationVerdict,
)
from evaluation_engine.rule_engine import (
    EvaluationRuleEngine,
    EvaluationValidationError,
    ForbiddenPatternViolationError,
)
from main import app
from tests.fixtures.sample_payloads import (
    INVALID_EVALUATION_REQUEST_MALFORMED,
    VALID_EVALUATION_REQUEST,
)

client = TestClient(app)


# ============================================================================
# TIER 1: UNIT TESTS (Contracts & Schemas)
# ============================================================================

def test_tier1_valid_evaluation_request():
    """Verify standard EvaluationRequest compiles and validates."""
    req = EvaluationRequest(**VALID_EVALUATION_REQUEST)
    assert req.task_id == "T-GOV-002"
    assert req.candidate_name == "Kanishk Singh"
    assert req.submission_evidence["schema_compliance"] is True


def test_tier1_evaluation_request_missing_required_field():
    """Verify missing required fields raise Pydantic ValidationError."""
    with pytest.raises(ValidationError):
        EvaluationRequest(**INVALID_EVALUATION_REQUEST_MALFORMED)


def test_tier1_evaluation_request_forbids_extra_fields():
    """Verify extra rogue fields are rejected."""
    bad_payload = copy.deepcopy(VALID_EVALUATION_REQUEST)
    bad_payload["unauthorized_injected_field"] = "exploit"
    with pytest.raises(ValidationError):
        EvaluationRequest(**bad_payload)


# ============================================================================
# TIER 2: INTEGRATION TESTS (Evaluation Run & PDF Generation)
# ============================================================================

def test_tier2_full_evaluation_lifecycle():
    """Verify complete evaluation run yielding 100/100 and PASS verdict."""
    engine = EvaluationRuleEngine(seed="INTEGRATION_TEST_SEED")
    verdict = engine.evaluate_submission(VALID_EVALUATION_REQUEST)

    assert verdict.task_id == "T-GOV-002"
    assert verdict.total_score == 100.0
    assert verdict.verdict == "PASS"
    assert verdict.next_task_recommendation == "T-GOV-003"
    assert len(verdict.criteria_results) == 5
    assert len(verdict.deterministic_verdict_hash) == 64


def test_tier2_reportlab_pdf_generation(tmp_path):
    """Verify ReportLab generates a valid PDF evaluation certificate."""
    engine = EvaluationRuleEngine()
    verdict = engine.evaluate_submission(VALID_EVALUATION_REQUEST)
    
    pdf_out = str(tmp_path / "evaluation_certificate.pdf")
    generated_path = engine.generate_pdf_report(verdict, pdf_out)
    
    assert os.path.exists(generated_path)
    assert os.path.getsize(generated_path) > 1000  # Non-empty PDF


# ============================================================================
# TIER 3: NEGATIVE & SECURITY TESTS (Forbidden Patterns & Zero 500s)
# ============================================================================

def test_tier3_forbidden_pattern_workflow_execution_engine():
    """Verify prohibition of workflow_execution_engine pattern."""
    engine = EvaluationRuleEngine()
    bad_req = copy.deepcopy(VALID_EVALUATION_REQUEST)
    bad_req["submission_evidence"]["attempted_pattern"] = "workflow_execution_engine"
    
    with pytest.raises(ForbiddenPatternViolationError) as exc_info:
        engine.evaluate_submission(bad_req)
    assert "workflow_execution_engine" in str(exc_info.value)


def test_tier3_forbidden_pattern_direct_masterdb_mutation():
    """Verify prohibition of direct_masterdb_schema_mutation pattern."""
    engine = EvaluationRuleEngine()
    bad_req = copy.deepcopy(VALID_EVALUATION_REQUEST)
    bad_req["submission_evidence"]["mutation_action"] = "direct_masterdb_schema_mutation"
    
    with pytest.raises(ForbiddenPatternViolationError) as exc_info:
        engine.evaluate_submission(bad_req)
    assert "direct_masterdb_schema_mutation" in str(exc_info.value)


def test_tier3_api_error_boundary_malformed_input():
    """Verify POST /api/v1/parikshak/evaluate returns 400 on malformed input (Never 500)."""
    response = client.post("/api/v1/parikshak/evaluate", json={"junk": "data"})
    assert response.status_code == 400
    data = response.json()
    assert data["error_code"] == "EVALUATION_VALIDATION_ERROR"
    assert "invalid_fields" in data


def test_tier3_api_error_boundary_forbidden_pattern():
    """Verify POST /api/v1/parikshak/evaluate returns 403 on forbidden patterns (Never 500)."""
    bad_req = copy.deepcopy(VALID_EVALUATION_REQUEST)
    bad_req["submission_evidence"]["illegal"] = "workflow_execution_engine"
    response = client.post("/api/v1/parikshak/evaluate", json=bad_req)
    assert response.status_code == 403
    data = response.json()
    assert data["error_code"] == "FORBIDDEN_PATTERN_VIOLATION"


# ============================================================================
# TIER 4: DETERMINISM STANDARD (50-Run Bit-Identical SHA-256 Verification)
# ============================================================================

def test_tier4_50_run_deterministic_verdict_hash():
    """Assert that 50 consecutive runs of the evaluation engine produce bit-identical SHA-256 hashes."""
    hashes = []
    fixed_timestamp = "2026-11-19T10:00:00Z"

    for run_idx in range(50):
        engine = EvaluationRuleEngine(seed="CANONICAL_GOV_OS_DETERMINISM_SEED")
        verdict = engine.evaluate_submission(
            VALID_EVALUATION_REQUEST,
            fixed_timestamp_utc=fixed_timestamp,
        )
        hashes.append(verdict.deterministic_verdict_hash)

    assert len(hashes) == 50
    unique_hashes = set(hashes)
    assert len(unique_hashes) == 1, f"Determinism failure! Multiple hashes found: {unique_hashes}"

    final_hash = hashes[0]
    assert len(final_hash) == 64

    # Save evidence proof to review_packets/evidence/
    evidence_dir = os.path.join(os.path.dirname(__file__), "..", "review_packets", "evidence")
    os.makedirs(evidence_dir, exist_ok=True)
    evidence_path = os.path.join(evidence_dir, "06_PARIKSHAK_EVALUATION_ENGINE_50_RUN_DETERMINISM.json")

    proof_record = {
        "standard": "Governed Operational System (Gov-OS) Core Compliance",
        "task_id": "T-GOV-002",
        "target_product": "Parikshak Engineering Review Runtime",
        "candidate": "Kanishk Singh",
        "total_runs": 50,
        "unique_hash_count": len(unique_hashes),
        "deterministic_sha256_hash": final_hash,
        "verdict": "PASS",
        "score": 100.0,
        "status": "VERIFIED_BIT_IDENTICAL",
        "sample_run_hashes": hashes[:5],
    }
    with open(evidence_path, "w", encoding="utf-8") as f:
        json.dump(proof_record, f, indent=2)


# ============================================================================
# TIER 5: REGRESSION & HEALTH TESTS
# ============================================================================

def test_tier5_health_check():
    """Verify Parikshak API health endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "UP"
    assert data["service"] == "PARIKSHAK_EVALUATION_RUNTIME"


def test_tier5_list_rules():
    """Verify retrieving canonical Gov-OS evaluation rules."""
    response = client.get("/api/v1/parikshak/rules")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 5
    assert data[0]["rule_id"] == "RULE-GOV-01"
