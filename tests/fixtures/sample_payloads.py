"""Sample payload fixtures for WP1 validation tests."""

VALID_TASK_DEFINITION = {
    "task_id": "T-OUT-OF-SYLLABUS",
    "target_product": "BHIV Enterprise Operating System Common Core",
    "assigned_candidate": "Kanishk Singh",
    "calibrated_duration_minutes": 180,
    "difficulty_level": "BEGINNER",
    "priority": "P0",
    "objective": "Implement and verify focused Enterprise Core capability under SETU OS Architecture v6.0.",
    "integration_block": {
        "bhiv_core": True,
        "gc_shakti": True,
        "niyantran": True,
        "bucket": True,
        "gov_os": True,
        "saarthi": True,
    },
    "metadata": {
        "version": "1.0.0",
        "environment": "production-hardened",
    },
}

INVALID_TASK_DEFINITION_MISSING_OBJECTIVE = {
    "task_id": "T-OUT-OF-SYLLABUS",
    "target_product": "BHIV Enterprise Operating System Common Core",
    "assigned_candidate": "Kanishk Singh",
    "calibrated_duration_minutes": 180,
    # missing objective
}

INVALID_TASK_DEFINITION_EXTRA_FIELD = {
    "task_id": "T-OUT-OF-SYLLABUS",
    "target_product": "BHIV Enterprise Operating System Common Core",
    "assigned_candidate": "Kanishk Singh",
    "calibrated_duration_minutes": 180,
    "objective": "Implement and verify focused Enterprise Core capability under SETU OS Architecture v6.0.",
    "unauthorized_rogue_field": "exploit_attempt",
}

VALID_STATE_TRANSITION = {
    "transition_id": "trans-56142b347d12",
    "task_id": "T-OUT-OF-SYLLABUS",
    "from_status": "INITIATED",
    "to_status": "VALIDATED",
    "trigger": "SCHEMA_VALIDATION_PASSED",
    "actor": "Kanishk Singh",
    "timestamp_utc": "2026-11-17T10:00:00Z",
    "payload": {"checks_passed": ["contract_inspection", "interface_alignment"]},
}

VALID_EVIDENCE_PACKET = {
    "artifact_id": "art-93655843-67f7",
    "trace_id": "trace-56142b347d12",
    "timestamp_utc": "2026-11-17T10:00:00Z",
    "schema_version": "1.0.0",
    "source_module_id": "BHIV_ENTERPRISE_CORE",
    "artifact_type": "GOVERNED_REVIEW_PACKET",
    "parent_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    "payload": {
        "score": 100,
        "verdict": "PASS",
        "status": "VERIFIED",
    },
    "signature": "ecdsa_secp256k1_signature_hash_proof",
}
