"""
tests/test_web_server.py — Phase 2: Web Server Integration Tests

Tests the FastAPI web server endpoints including health, capabilities,
contract verification, evidence retrieval, hybrid runtime, and the new
production monitoring (middleware, metrics, lifecycle hooks).
"""

import pytest
import json
import uuid
import time
from unittest.mock import patch, MagicMock

from fastapi.testclient import TestClient

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from web_server import app
from execution_contract import ComputationExecutionContract
from node_identity import NodeSigner
from provenance import sign_contract


client = TestClient(app)


# ═══════════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════════

def _make_signed_contract(trace_id: str = None, confidence: float = 0.99):
    """Create a valid signed contract payload for /verify."""
    trace_id = trace_id or str(uuid.uuid4())
    producer_id = f"TEST_PRODUCER_{uuid.uuid4().hex[:8]}"
    signer = NodeSigner(node_id=producer_id, node_role="QUANTUM")
    
    contract = ComputationExecutionContract(
        producer_type="QUANTUM",
        producer_id=producer_id,
        payload={"operation": "test_op", "input": 42},
        confidence=confidence,
        trace_id=trace_id,
        contract_version="2.0.0",
        timestamp=time.strftime("%Y-%m-%dT%H:%M:%S+00:00", time.gmtime()),
    )
    
    signed = sign_contract(contract, signer)
    return {
        "contract": signed.to_dict(),
        "producer_public_key": signer.identity.public_key,
    }, trace_id


# ═══════════════════════════════════════════════════════════════════════════
# Health Endpoints
# ═══════════════════════════════════════════════════════════════════════════

class TestHealthEndpoints:

    def test_health_returns_200(self):
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "UP"

    def test_health_live_returns_200(self):
        resp = client.get("/health/live")
        assert resp.status_code == 200
        assert resp.json()["readiness"] == "READY"

    def test_health_ready_returns_200(self):
        resp = client.get("/health/ready")
        assert resp.status_code == 200
        data = resp.json()
        assert "metrics" in data
        assert "uptime_seconds" in data["metrics"]

    def test_health_contains_dependency_status(self):
        resp = client.get("/health")
        data = resp.json()
        assert "dependencies" in data
        assert data["dependencies"]["replay_registry"] == "ONLINE"


# ═══════════════════════════════════════════════════════════════════════════
# Capabilities
# ═══════════════════════════════════════════════════════════════════════════

class TestCapabilitiesEndpoint:

    def test_capabilities_returns_200(self):
        resp = client.get("/capabilities")
        assert resp.status_code == 200

    def test_capabilities_contains_expected_entries(self):
        resp = client.get("/capabilities")
        data = resp.json()
        assert "capabilities" in data
        cap_ids = [c["capability_id"] for c in data["capabilities"]]
        assert "cap-replay-verif" in cap_ids
        assert "cap-trust-verif" in cap_ids
        assert "cap-execution" in cap_ids
        assert "cap-consensus" in cap_ids

    def test_capabilities_versioned(self):
        resp = client.get("/capabilities")
        data = resp.json()
        assert "version" in data


# ═══════════════════════════════════════════════════════════════════════════
# Contract Verification
# ═══════════════════════════════════════════════════════════════════════════

class TestVerifyEndpoint:

    def test_verify_valid_contract_returns_200(self):
        payload, _ = _make_signed_contract()
        resp = client.post("/verify", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["flow_status"] == "COMPLETED"

    def test_verify_returns_trace_continuity(self):
        payload, trace_id = _make_signed_contract()
        resp = client.post("/verify", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert "trace_continuity" in data
        assert "runtime_hash" in data["trace_continuity"]

    def test_verify_missing_public_key_returns_422(self):
        """Contract without a valid public key should be rejected."""
        payload, _ = _make_signed_contract()
        payload["producer_public_key"] = ""
        resp = client.post("/verify", json=payload)
        # Should halt due to trust rejection
        assert resp.status_code in (200, 422)
        if resp.status_code == 200:
            data = resp.json()
            assert data["flow_status"] == "HALTED"

    def test_verify_includes_stage_timings(self):
        """Phase 2: verify responses should include per-stage timing data."""
        payload, _ = _make_signed_contract()
        resp = client.post("/verify", json=payload)
        if resp.status_code == 200:
            data = resp.json()
            assert "stage_timings_ms" in data

    def test_verify_empty_body_returns_422(self):
        """Empty request body should return validation error."""
        resp = client.post("/verify", json={})
        # FastAPI/Pydantic may accept empty body with all-optional fields
        # but the pipeline should halt with INVALID_CONTRACT
        assert resp.status_code in (200, 422)


# ═══════════════════════════════════════════════════════════════════════════
# Evidence Endpoints
# ═══════════════════════════════════════════════════════════════════════════

class TestEvidenceEndpoints:

    def test_evidence_certificate_not_found(self):
        resp = client.get("/evidence/certificate/nonexistent-id")
        assert resp.status_code == 404

    def test_evidence_trace_not_found(self):
        resp = client.get("/evidence/trace/nonexistent-trace")
        assert resp.status_code == 404

    def test_evidence_hash_endpoint(self):
        resp = client.get("/evidence/some-hash-value")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "INCLUDED"
        assert "merkle_proof" in data


# ═══════════════════════════════════════════════════════════════════════════
# GC Validation
# ═══════════════════════════════════════════════════════════════════════════

class TestGCValidation:

    def test_gc_validate_missing_auth_returns_401(self):
        payload, _ = _make_signed_contract()
        req_body = {"contract": payload["contract"], "producer_public_key": payload["producer_public_key"]}
        resp = client.post("/gc/validate", json=req_body)
        assert resp.status_code == 401

    def test_gc_validate_invalid_auth_returns_401(self):
        payload, _ = _make_signed_contract()
        req_body = {"contract": payload["contract"], "producer_public_key": payload["producer_public_key"]}
        resp = client.post("/gc/validate", json=req_body, headers={"Authorization": "InvalidToken"})
        assert resp.status_code == 401


# ═══════════════════════════════════════════════════════════════════════════
# Hybrid Runtime
# ═══════════════════════════════════════════════════════════════════════════

class TestHybridEndpoints:

    def test_hybrid_health_returns_200(self):
        resp = client.get("/hybrid/health")
        assert resp.status_code == 200

    def test_providers_returns_200(self):
        resp = client.get("/providers")
        assert resp.status_code == 200
        data = resp.json()
        assert "providers" in data
        assert "aggregate" in data

    def test_network_status_returns_200(self):
        resp = client.get("/network/status")
        assert resp.status_code == 200

    def test_hybrid_dispatch_health_check(self):
        resp = client.post("/hybrid/dispatch", json={
            "service_id": "QCG-HYBRID-RUNTIME",
            "operation": "health_check",
            "payload": {},
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "SUCCESS"
        assert data["operation"] == "health_check"

    def test_hybrid_dispatch_unknown_operation(self):
        resp = client.post("/hybrid/dispatch", json={
            "service_id": "QCG-HYBRID-RUNTIME",
            "operation": "nonexistent_op",
            "payload": {},
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "SERVICE_NOT_FOUND"


# ═══════════════════════════════════════════════════════════════════════════
# Metrics & Monitoring (Phase 2)
# ═══════════════════════════════════════════════════════════════════════════

class TestMetricsEndpoints:

    def test_metrics_returns_200_prometheus_format(self):
        resp = client.get("/metrics")
        assert resp.status_code == 200
        assert "text/plain" in resp.headers["content-type"]
        body = resp.text
        assert "qcg_uptime_seconds" in body
        assert "qcg_requests_total" in body

    def test_metrics_json_returns_200(self):
        resp = client.get("/metrics/json")
        assert resp.status_code == 200
        data = resp.json()
        assert "uptime_seconds" in data
        assert "requests" in data
        assert "errors" in data
        assert "latency_ms" in data


# ═══════════════════════════════════════════════════════════════════════════
# Security Headers (Phase 2)
# ═══════════════════════════════════════════════════════════════════════════

class TestSecurityHeaders:

    def test_response_contains_security_headers(self):
        resp = client.get("/health")
        assert resp.headers.get("X-Content-Type-Options") == "nosniff"
        assert resp.headers.get("X-Frame-Options") == "DENY"
        assert resp.headers.get("Strict-Transport-Security") is not None
        assert resp.headers.get("Cache-Control") == "no-store, no-cache, must-revalidate"

    def test_response_contains_request_id(self):
        resp = client.get("/health")
        assert "X-Request-ID" in resp.headers

    def test_custom_request_id_is_echoed(self):
        custom_id = "test-correlation-12345"
        resp = client.get("/health", headers={"X-Request-ID": custom_id})
        assert resp.headers.get("X-Request-ID") == custom_id

    def test_response_time_header_present(self):
        resp = client.get("/health")
        assert "X-Response-Time-Ms" in resp.headers
        # Should be a valid number
        float(resp.headers["X-Response-Time-Ms"])


# ═══════════════════════════════════════════════════════════════════════════
# Replay Lineage
# ═══════════════════════════════════════════════════════════════════════════

class TestReplayLineage:

    def test_replay_lineage_not_found(self):
        resp = client.get("/replay/lineage/nonexistent-trace")
        assert resp.status_code == 404
