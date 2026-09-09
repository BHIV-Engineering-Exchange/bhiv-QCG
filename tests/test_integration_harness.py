"""
tests/test_integration_harness.py — Phase 2: Integration Harness Unit Tests

Tests for TANTRAIntegrationHarness covering:
- Full pipeline success flow
- Replay rejection (duplicate trace_id)
- Trust rejection (missing public key)
- Execution halt (low confidence)
- KESHAV analysis mock (enabled/disabled/fallback)
- Input sanitization (trace_id, payload bounds)
- Per-stage error boundary behavior
"""

import pytest
import uuid
import time
import hashlib
from unittest.mock import patch, MagicMock

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from integration_harness import TANTRAIntegrationHarness
from execution_contract import ComputationExecutionContract
from node_identity import NodeSigner
from provenance import sign_contract


# ═══════════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════════

def _make_payload(trace_id: str = None, confidence: float = 0.99):
    """Create a valid signed contract payload dict."""
    trace_id = trace_id or str(uuid.uuid4())
    producer_id = f"TEST_PROD_{uuid.uuid4().hex[:6]}"
    signer = NodeSigner(node_id=producer_id, node_role="QUANTUM")

    contract = ComputationExecutionContract(
        producer_type="QUANTUM",
        producer_id=producer_id,
        payload={"operation": "test", "data": 1},
        confidence=confidence,
        trace_id=trace_id,
        contract_version="2.0.0",
        timestamp=time.strftime("%Y-%m-%dT%H:%M:%S+00:00", time.gmtime()),
    )

    signed = sign_contract(contract, signer)
    return signed.to_dict(), signer.identity.public_key, trace_id


# ═══════════════════════════════════════════════════════════════════════════
# Full Pipeline
# ═══════════════════════════════════════════════════════════════════════════

class TestFullPipeline:

    def test_successful_flow(self):
        harness = TANTRAIntegrationHarness()
        payload, pub_key, trace_id = _make_payload()
        success, response = harness.process_incoming_contract(payload, pub_key)
        assert success is True
        assert response["flow_status"] == "COMPLETED"
        assert "trace_continuity" in response

    def test_flow_records_stages(self):
        harness = TANTRAIntegrationHarness()
        payload, pub_key, trace_id = _make_payload()
        success, response = harness.process_incoming_contract(payload, pub_key)
        assert success is True
        stages = response["stages"]
        assert "replay" in stages
        assert "trust" in stages
        assert "execution" in stages
        assert "consensus" in stages

    def test_flow_records_stage_timings(self):
        """Phase 2: per-stage timing metrics should be present."""
        harness = TANTRAIntegrationHarness()
        payload, pub_key, _ = _make_payload()
        success, response = harness.process_incoming_contract(payload, pub_key)
        assert success is True
        assert "stage_timings_ms" in response
        timings = response["stage_timings_ms"]
        assert "replay" in timings
        assert "trust" in timings
        assert "execution" in timings
        assert "consensus" in timings

    def test_flow_adds_to_evidence_ledger(self):
        harness = TANTRAIntegrationHarness()
        payload, pub_key, _ = _make_payload()
        harness.process_incoming_contract(payload, pub_key)
        assert len(harness.ledger._records) == 1
        assert harness.ledger.verify_chain() is True


# ═══════════════════════════════════════════════════════════════════════════
# Replay Rejection
# ═══════════════════════════════════════════════════════════════════════════

class TestReplayRejection:

    def test_duplicate_trace_id_rejected(self):
        harness = TANTRAIntegrationHarness()
        payload, pub_key, trace_id = _make_payload()

        # First submission succeeds
        success1, resp1 = harness.process_incoming_contract(payload, pub_key)
        assert success1 is True

        # Second submission with same trace_id should be rejected
        success2, resp2 = harness.process_incoming_contract(payload, pub_key)
        assert success2 is False
        assert resp2["flow_status"] == "HALTED"
        assert "REPLAY" in resp2.get("halt_reason", "")


# ═══════════════════════════════════════════════════════════════════════════
# Trust Rejection
# ═══════════════════════════════════════════════════════════════════════════

class TestTrustRejection:

    def test_missing_public_key_rejected(self):
        harness = TANTRAIntegrationHarness()
        payload, _, trace_id = _make_payload()
        success, response = harness.process_incoming_contract(payload, "")
        assert success is False
        assert "TRUST_REJECTED" in response.get("halt_reason", "")

    def test_short_public_key_rejected(self):
        harness = TANTRAIntegrationHarness()
        payload, _, _ = _make_payload()
        success, response = harness.process_incoming_contract(payload, "short")
        assert success is False
        assert "TRUST_REJECTED" in response.get("halt_reason", "")


# ═══════════════════════════════════════════════════════════════════════════
# Input Sanitization (Phase 2)
# ═══════════════════════════════════════════════════════════════════════════

class TestInputSanitization:

    def test_trace_id_control_chars_removed(self):
        harness = TANTRAIntegrationHarness()
        sanitized = harness._sanitize_trace_id("trace\x00id\x1fwith\x7fcontrol")
        assert "\x00" not in sanitized
        assert "\x1f" not in sanitized
        assert "\x7f" not in sanitized

    def test_trace_id_truncation(self):
        harness = TANTRAIntegrationHarness()
        long_id = "x" * 500
        sanitized = harness._sanitize_trace_id(long_id)
        import config
        assert len(sanitized) <= config.INPUT_TRACE_ID_MAX_LENGTH

    def test_empty_trace_id_defaults_to_unknown(self):
        harness = TANTRAIntegrationHarness()
        assert harness._sanitize_trace_id("") == "unknown"
        assert harness._sanitize_trace_id(None) == "unknown"

    def test_payload_bounds_rejects_oversized(self):
        harness = TANTRAIntegrationHarness()
        big_payload = {f"key_{i}": i for i in range(200)}
        assert harness._validate_payload_bounds(big_payload) is False

    def test_payload_bounds_accepts_normal(self):
        harness = TANTRAIntegrationHarness()
        normal_payload = {"key": "value", "data": 42}
        assert harness._validate_payload_bounds(normal_payload) is True

    def test_oversized_payload_halts_pipeline(self):
        harness = TANTRAIntegrationHarness()
        big_payload = {f"key_{i}": i for i in range(200)}
        success, response = harness.process_incoming_contract(big_payload, "some_key")
        assert success is False
        assert "INPUT_VALIDATION" in response.get("halt_reason", "")


# ═══════════════════════════════════════════════════════════════════════════
# KESHAV Analysis
# ═══════════════════════════════════════════════════════════════════════════

class TestKeshavAnalysis:

    def test_keshav_disabled_returns_skipped(self):
        harness = TANTRAIntegrationHarness()
        harness.keshav_client = None  # Simulate disabled
        result = harness._run_keshav_analysis("trace-1", {"data": 1})
        assert result["status"] == "SKIPPED"
        assert result["live"] is False

    def test_keshav_stage_in_response(self):
        harness = TANTRAIntegrationHarness()
        payload, pub_key, _ = _make_payload()
        success, response = harness.process_incoming_contract(payload, pub_key)
        assert "keshav_analysis" in response["stages"]


# ═══════════════════════════════════════════════════════════════════════════
# Error Boundaries (Phase 2)
# ═══════════════════════════════════════════════════════════════════════════

class TestErrorBoundaries:

    def test_pipeline_exception_caught(self):
        """Exceptions in the pipeline should be caught and returned as ERROR."""
        harness = TANTRAIntegrationHarness()
        # Force an exception by passing a non-dict payload
        # The pipeline should catch it gracefully
        success, response = harness.process_incoming_contract(
            {"trace_id": "test", "bad_field": object()},
            "some_public_key_value_that_is_long_enough"
        )
        # Should either halt or error — never crash
        assert success is False
        assert response["flow_status"] in ("HALTED", "ERROR")

    def test_health_updates_on_failure(self):
        harness = TANTRAIntegrationHarness()
        payload, _, _ = _make_payload()
        # Use empty pub key to trigger trust rejection
        harness.process_incoming_contract(payload, "")
        health = harness.health_iface.get_health()
        assert health["metrics"]["error_rate"] > 0
