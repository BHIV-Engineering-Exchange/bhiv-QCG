"""5-Tier Test Suite for BHIV Enterprise Core Logic & Verification.

Standard: SETU OS Architecture v6.0
Tiers:
1. Unit Tests (Contracts & Schema Validation)
2. Integration Tests (State Machine & Pipeline Traversal)
3. Negative & Error Boundary Tests (Zero 500 Exceptions)
4. Determinism Standard (50-Run Bit-Identical SHA-256 State Hash Verification)
5. Regression & Compatibility Tests
"""

import copy
import json
import os
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from contracts.schemas import (
    EvidencePacket,
    IntegrationBlockStatus,
    NiyantranAssignmentPayload,
    ReviewPacketPayload,
    StateTransitionEvent,
    TaskDefinition,
    TaskPriorityEnum,
    TaskStatusEnum,
)
from core.api import router
from core.enterprise_engine import (
    EnterpriseCoreEngine,
    EnterpriseCoreValidationError,
    ImmutabilityViolationError,
    StateTransitionViolationError,
    TaskNotFoundError,
)
from tests.fixtures.sample_payloads import (
    INVALID_TASK_DEFINITION_EXTRA_FIELD,
    INVALID_TASK_DEFINITION_MISSING_OBJECTIVE,
    VALID_EVIDENCE_PACKET,
    VALID_STATE_TRANSITION,
    VALID_TASK_DEFINITION,
)
from web_server import app

client = TestClient(app)


# ============================================================================
# TIER 1: UNIT TESTS (Contracts & Schemas)
# ============================================================================

def test_tier1_valid_task_definition():
    """Verify standard TaskDefinition compiles and validates."""
    task = TaskDefinition(**VALID_TASK_DEFINITION)
    assert task.task_id == "T-OUT-OF-SYLLABUS"
    assert task.priority == TaskPriorityEnum.P0
    assert task.calibrated_duration_minutes == 180
    assert task.integration_block.bhiv_core is True
    assert task.integration_block.niyantran is True


def test_tier1_task_definition_missing_required_field():
    """Verify missing required fields raise Pydantic ValidationError."""
    with pytest.raises(ValidationError):
        TaskDefinition(**INVALID_TASK_DEFINITION_MISSING_OBJECTIVE)


def test_tier1_task_definition_forbids_extra_fields():
    """Verify rogue/extra fields are strictly forbidden."""
    with pytest.raises(ValidationError):
        TaskDefinition(**INVALID_TASK_DEFINITION_EXTRA_FIELD)


def test_tier1_evidence_packet_schema():
    """Verify EvidencePacket schema conforming to v1.0."""
    packet = EvidencePacket(**VALID_EVIDENCE_PACKET)
    assert packet.schema_version == "1.0.0"
    assert packet.source_module_id == "BHIV_ENTERPRISE_CORE"
    assert packet.artifact_type == "GOVERNED_REVIEW_PACKET"


# ============================================================================
# TIER 2: INTEGRATION TESTS (State Machine Traversal & Lifecycle)
# ============================================================================

def test_tier2_full_lifecycle_state_machine():
    """Verify deterministic state traversal from INITIATED through ASSIGNED."""
    engine = EnterpriseCoreEngine(seed="INTEGRATION_TEST_SEED")
    
    # 1. Register task (INITIATED)
    rec = engine.register_task(VALID_TASK_DEFINITION)
    assert rec.status == TaskStatusEnum.INITIATED
    assert len(rec.transitions) == 1
    initial_hash = rec.state_hash
    assert len(initial_hash) == 64

    # 2. VALIDATED
    rec = engine.transition_state(
        task_id=rec.task_id,
        to_status=TaskStatusEnum.VALIDATED,
        trigger="WP1_CONTRACT_INSPECTION_PASSED",
        actor="Kanishk Singh",
        payload={"contract_version": "1.0.0"},
        timestamp_utc="2026-11-17T11:00:00Z",
    )
    assert rec.status == TaskStatusEnum.VALIDATED
    assert rec.state_hash != initial_hash

    # 3. EXECUTED
    rec = engine.transition_state(
        task_id=rec.task_id,
        to_status=TaskStatusEnum.EXECUTED,
        trigger="WP2_CORE_LOGIC_IMPLEMENTED",
        actor="Kanishk Singh",
        payload={"tests_passed": 12},
        timestamp_utc="2026-11-17T12:00:00Z",
    )
    assert rec.status == TaskStatusEnum.EXECUTED

    # 4. EVALUATED
    rec = engine.transition_state(
        task_id=rec.task_id,
        to_status=TaskStatusEnum.EVALUATED,
        trigger="PARIKSHAK_AI_EVALUATION",
        actor="Parikshak",
        payload={"score": 100, "verdict": "PASS"},
        timestamp_utc="2026-11-17T13:00:00Z",
    )
    assert rec.status == TaskStatusEnum.EVALUATED

    # 5. GOVERNED
    rec = engine.transition_state(
        task_id=rec.task_id,
        to_status=TaskStatusEnum.GOVERNED,
        trigger="GC_SHAKTI_GOVERNANCE_SEAL",
        actor="GC Shakti",
        payload={"compliance": "APPROVED"},
        timestamp_utc="2026-11-17T14:00:00Z",
    )
    assert rec.status == TaskStatusEnum.GOVERNED

    # 6. ASSIGNED
    rec = engine.transition_state(
        task_id=rec.task_id,
        to_status=TaskStatusEnum.ASSIGNED,
        trigger="NIYANTRAN_NEXT_TASK_DISPATCH",
        actor="Niyantran",
        payload={"next_task_id": "BHQ-SYSTEMS-002"},
        timestamp_utc="2026-11-17T15:00:00Z",
    )
    assert rec.status == TaskStatusEnum.ASSIGNED
    assert len(rec.transitions) == 6

    # Evidence Packet & Review Packet Generation
    evidence = engine.generate_evidence_packet(rec.task_id)
    assert evidence.artifact_type == "GOVERNED_REVIEW_PACKET"
    assert evidence.payload["governance_status"] == "COMPLIANT"

    review = engine.assemble_review_packet(rec.task_id, score=100, verdict="PASS")
    assert review.score == 100
    assert review.verdict == "PASS"
    assert review.architectural_standard == "SETU OS Architecture v6.0"
    assert review.next_task.next_task_id == "BHQ-SYSTEMS-002"


# ============================================================================
# TIER 3: NEGATIVE & ERROR BOUNDARY TESTS (Zero 500 Exceptions)
# ============================================================================

def test_tier3_forbidden_state_transition_leap():
    """Verify jumping states (e.g. INITIATED directly to ASSIGNED) is strictly prohibited."""
    engine = EnterpriseCoreEngine()
    rec = engine.register_task(VALID_TASK_DEFINITION)
    
    with pytest.raises(StateTransitionViolationError):
        engine.transition_state(
            task_id=rec.task_id,
            to_status=TaskStatusEnum.ASSIGNED,  # Illegal leap
            trigger="UNAUTHORIZED_JUMP",
            actor="adversary",
        )


def test_tier3_duplicate_task_registration_blocked():
    """Verify duplicate registration is rejected to preserve audit immutability."""
    engine = EnterpriseCoreEngine()
    engine.register_task(VALID_TASK_DEFINITION)
    
    with pytest.raises(ImmutabilityViolationError):
        engine.register_task(VALID_TASK_DEFINITION)


def test_tier3_unknown_task_query_raises_not_found():
    """Verify querying an unregistered task raises TaskNotFoundError."""
    engine = EnterpriseCoreEngine()
    with pytest.raises(TaskNotFoundError):
        engine.get_task_record("NON_EXISTENT_TASK")


def test_tier3_api_error_boundary_on_malformed_task_payload():
    """Verify HTTP POST /api/v1/enterprise-core/tasks returns 400 on malformed input (Never 500)."""
    response = client.post("/api/v1/enterprise-core/tasks", json={"invalid_key": "junk"})
    assert response.status_code == 400
    data = response.json()
    assert data["error_code"] == "VALIDATION_ERROR"
    assert "invalid_fields" in data


def test_tier3_api_error_boundary_on_illegal_transition():
    """Verify HTTP POST /transition returns 400/404 on illegal transitions (Never 500)."""
    # Create valid task first
    task_payload = copy.deepcopy(VALID_TASK_DEFINITION)
    task_payload["task_id"] = "T-BOUNDARY-001"
    res1 = client.post("/api/v1/enterprise-core/tasks", json=task_payload)
    assert res1.status_code in (201, 200)

    # Attempt illegal jump directly to ASSIGNED
    res2 = client.post(
        "/api/v1/enterprise-core/tasks/T-BOUNDARY-001/transition",
        json={"to_status": "ASSIGNED", "trigger": "ATTACK", "actor": "rogue"},
    )
    assert res2.status_code == 400
    data = res2.json()
    assert data["error_code"] == "STATE_TRANSITION_VIOLATION"


# ============================================================================
# TIER 4: DETERMINISM STANDARD (50 Consecutive Runs Bit-Identical SHA-256)
# ============================================================================

def test_tier4_50_run_deterministic_state_hash():
    """Assert that 50 consecutive runs of the state machine produce bit-identical SHA-256 hashes."""
    hashes = []
    
    fixed_timestamps = [
        "2026-11-17T10:00:00Z",
        "2026-11-17T11:00:00Z",
        "2026-11-17T12:00:00Z",
        "2026-11-17T13:00:00Z",
        "2026-11-17T14:00:00Z",
        "2026-11-17T15:00:00Z",
    ]

    for run_idx in range(50):
        engine = EnterpriseCoreEngine(seed="CANONICAL_DETERMINISM_SEED_V6")
        
        # INITIATED
        rec = engine.register_task(VALID_TASK_DEFINITION)
        
        # VALIDATED
        rec = engine.transition_state(
            task_id=rec.task_id,
            to_status=TaskStatusEnum.VALIDATED,
            trigger="CONTRACT_INSPECTION",
            actor="Kanishk Singh",
            payload={"check": "passed"},
            timestamp_utc=fixed_timestamps[1],
        )

        # EXECUTED
        rec = engine.transition_state(
            task_id=rec.task_id,
            to_status=TaskStatusEnum.EXECUTED,
            trigger="EXECUTION_RUN",
            actor="Kanishk Singh",
            payload={"result": "success"},
            timestamp_utc=fixed_timestamps[2],
        )

        # EVALUATED
        rec = engine.transition_state(
            task_id=rec.task_id,
            to_status=TaskStatusEnum.EVALUATED,
            trigger="PARIKSHAK_EVAL",
            actor="Parikshak",
            payload={"score": 100},
            timestamp_utc=fixed_timestamps[3],
        )

        # GOVERNED
        rec = engine.transition_state(
            task_id=rec.task_id,
            to_status=TaskStatusEnum.GOVERNED,
            trigger="SHAKTI_RULE",
            actor="GC Shakti",
            payload={"status": "governed"},
            timestamp_utc=fixed_timestamps[4],
        )

        # ASSIGNED
        rec = engine.transition_state(
            task_id=rec.task_id,
            to_status=TaskStatusEnum.ASSIGNED,
            trigger="NIYANTRAN_DISPATCH",
            actor="Niyantran",
            payload={"next": "BHQ-SYSTEMS-002"},
            timestamp_utc=fixed_timestamps[5],
        )

        hashes.append(rec.state_hash)

    # Assert exactly 50 hashes collected
    assert len(hashes) == 50
    # Assert zero drift: exactly 1 distinct hash across all 50 runs!
    unique_hashes = set(hashes)
    assert len(unique_hashes) == 1, f"Determinism failure! Found multiple hashes: {unique_hashes}"
    
    final_deterministic_hash = hashes[0]
    assert len(final_deterministic_hash) == 64

    # Save evidence proof to review_packets/evidence/
    evidence_dir = os.path.join(os.path.dirname(__file__), "..", "review_packets", "evidence")
    os.makedirs(evidence_dir, exist_ok=True)
    evidence_path = os.path.join(evidence_dir, "04_ENTERPRISE_CORE_50_RUN_DETERMINISM_PROOF.json")
    
    proof_record = {
        "standard": "SETU OS Architecture v6.0",
        "task_id": "T-OUT-OF-SYLLABUS",
        "candidate": "Kanishk Singh",
        "total_runs": 50,
        "unique_hash_count": len(unique_hashes),
        "deterministic_sha256_hash": final_deterministic_hash,
        "status": "VERIFIED_BIT_IDENTICAL",
        "sample_run_hashes": hashes[:5],
    }
    with open(evidence_path, "w", encoding="utf-8") as f:
        json.dump(proof_record, f, indent=2)


# ============================================================================
# TIER 5: REGRESSION & COMPATIBILITY TESTS
# ============================================================================

def test_tier5_health_readiness_regression():
    """Verify existing QCG endpoints remain functional."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ("UP", "OK", "READY", "HEALTHY")
