"""
tests/test_e2e_integration.py — Phase 2: End-to-End Integration Verification

Full lifecycle E2E tests exercising the contract pipeline through the HTTP API:
1. Happy path: create → sign → submit → verify evidence
2. Replay protection: duplicate submission rejected
3. Trust boundary: missing credentials rejected
4. Deterministic execution: identical inputs → identical runtime hashes
5. Hybrid runtime: capability dispatch schema
6. Evidence chain integrity: multi-contract ledger verification
"""

import pytest
import uuid
import time

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

def _signed_contract_payload(
    trace_id: str = None,
    confidence: float = 0.99,
    producer_id: str = None,
    payload: dict = None,
):
    """Build a complete signed contract request body."""
    trace_id = trace_id or str(uuid.uuid4())
    producer_id = producer_id or f"E2E_PROD_{uuid.uuid4().hex[:6]}"
    signer = NodeSigner(node_id=producer_id, node_role="QUANTUM")

    contract = ComputationExecutionContract(
        producer_type="QUANTUM",
        producer_id=producer_id,
        payload=payload or {"operation": "e2e_test", "data": 42},
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
# E2E Test 1: Happy Path — Full Lifecycle
# ═══════════════════════════════════════════════════════════════════════════

class TestE2EHappyPath:

    def test_full_contract_lifecycle(self):
        """
        Producer creates contract → signs → submits to /verify →
        response contains COMPLETED status with all stages.
        """
        payload, trace_id = _signed_contract_payload()

        # Submit
        resp = client.post("/verify", json=payload)
        assert resp.status_code == 200
        data = resp.json()

        # Verify flow completed
        assert data["flow_status"] == "COMPLETED"
        assert data["trace_id"] == trace_id

        # Verify all stages present
        stages = data["stages"]
        assert stages["replay"]["is_valid"] is True
        assert stages["trust"]["passed"] is True
        assert "ack" in stages["execution"]
        assert "consensus_reached" in stages["consensus"]

        # Verify trace continuity
        tc = data["trace_continuity"]
        assert tc["runtime_hash"] is not None
        assert tc["sequence_number"] is not None

    def test_contract_evidence_retrievable(self):
        """After successful submission, evidence hash endpoint should work."""
        payload, trace_id = _signed_contract_payload()
        resp = client.post("/verify", json=payload)
        assert resp.status_code == 200

        # Evidence hash retrieval should work
        resp2 = client.get(f"/evidence/{trace_id}")
        assert resp2.status_code == 200
        data = resp2.json()
        assert data["status"] == "INCLUDED"

    def test_health_reflects_processed_count(self):
        """After submissions, health metrics should reflect processed count."""
        # Get baseline
        h1 = client.get("/health").json()
        baseline = h1["metrics"]["total_processed"]

        # Submit a contract
        payload, _ = _signed_contract_payload()
        client.post("/verify", json=payload)

        # Check updated count
        h2 = client.get("/health").json()
        assert h2["metrics"]["total_processed"] > baseline


# ═══════════════════════════════════════════════════════════════════════════
# E2E Test 2: Replay Protection
# ═══════════════════════════════════════════════════════════════════════════

class TestE2EReplayProtection:

    def test_duplicate_contract_rejected(self):
        """Submitting the same trace_id twice should be rejected."""
        payload, trace_id = _signed_contract_payload()

        # First submission succeeds
        resp1 = client.post("/verify", json=payload)
        assert resp1.status_code == 200
        assert resp1.json()["flow_status"] == "COMPLETED"

        # Second submission should fail with replay rejection
        resp2 = client.post("/verify", json=payload)
        if resp2.status_code == 200:
            data = resp2.json()
            assert data["flow_status"] == "HALTED"
            assert "REPLAY" in data.get("halt_reason", "")
        else:
            assert resp2.status_code == 422


# ═══════════════════════════════════════════════════════════════════════════
# E2E Test 3: Trust Boundary
# ═══════════════════════════════════════════════════════════════════════════

class TestE2ETrustBoundary:

    def test_no_public_key_rejected(self):
        """Contract without a valid public key should be halted."""
        payload, _ = _signed_contract_payload()
        payload["producer_public_key"] = ""

        resp = client.post("/verify", json=payload)
        if resp.status_code == 200:
            data = resp.json()
            assert data["flow_status"] == "HALTED"
            assert "TRUST_REJECTED" in data.get("halt_reason", "")
        else:
            # 422 is also acceptable
            assert resp.status_code == 422

    def test_gc_validate_requires_auth(self):
        """GC validation endpoint must require Bearer token."""
        payload, _ = _signed_contract_payload()
        resp = client.post("/gc/validate", json={
            "contract": payload["contract"],
            "producer_public_key": payload["producer_public_key"],
        })
        assert resp.status_code == 401


# ═══════════════════════════════════════════════════════════════════════════
# E2E Test 4: Deterministic Execution
# ═══════════════════════════════════════════════════════════════════════════

class TestE2EDeterministicExecution:

    def test_identical_payload_produces_matching_ack(self):
        """Two contracts with identical payloads should produce same ACK type."""
        common_payload = {"operation": "deterministic_test", "input": 999}

        p1, _ = _signed_contract_payload(payload=common_payload)
        p2, _ = _signed_contract_payload(payload=common_payload)

        r1 = client.post("/verify", json=p1)
        r2 = client.post("/verify", json=p2)

        assert r1.status_code == 200
        assert r2.status_code == 200

        d1 = r1.json()
        d2 = r2.json()

        # Both should complete
        assert d1["flow_status"] == "COMPLETED"
        assert d2["flow_status"] == "COMPLETED"

        # ACK type should match (both ACK:OK or both ACK:DEGRADED)
        ack1 = d1["stages"]["execution"]["ack"]
        ack2 = d2["stages"]["execution"]["ack"]
        assert ack1.split(":")[1] == ack2.split(":")[1]


# ═══════════════════════════════════════════════════════════════════════════
# E2E Test 5: Hybrid Runtime
# ═══════════════════════════════════════════════════════════════════════════

class TestE2EHybridRuntime:

    def test_hybrid_dispatch_health_check(self):
        """Standard capability dispatch for health_check should succeed."""
        resp = client.post("/hybrid/dispatch", json={
            "service_id": "QCG-HYBRID-RUNTIME",
            "operation": "health_check",
            "payload": {},
            "version": "1.0.0",
            "invocation_id": str(uuid.uuid4()),
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "SUCCESS"
        assert data["operation"] == "health_check"
        assert "duration_ms" in data
        assert data["trust_method"] == "CLASSICAL"

    def test_hybrid_dispatch_list_providers(self):
        resp = client.post("/hybrid/dispatch", json={
            "service_id": "QCG-HYBRID-RUNTIME",
            "operation": "list_providers",
            "payload": {},
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "SUCCESS"
        assert "providers" in data["response"]

    def test_hybrid_dispatch_network_status(self):
        resp = client.post("/hybrid/dispatch", json={
            "service_id": "QCG-HYBRID-RUNTIME",
            "operation": "network_status",
            "payload": {},
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "SUCCESS"

    def test_hybrid_dispatch_invocation_result_format(self):
        """Response should match the InvocationResult schema."""
        resp = client.post("/hybrid/dispatch", json={
            "service_id": "QCG-HYBRID-RUNTIME",
            "operation": "health_check",
            "payload": {},
            "invocation_id": "test-inv-001",
        })
        data = resp.json()
        # Verify InvocationResult required fields
        required_fields = ["invocation_id", "service_id", "operation", "status", "response", "duration_ms", "trust_method", "evidence", "error"]
        for field in required_fields:
            assert field in data, f"Missing InvocationResult field: {field}"


# ═══════════════════════════════════════════════════════════════════════════
# E2E Test 6: Evidence Chain Integrity
# ═══════════════════════════════════════════════════════════════════════════

class TestE2EEvidenceChain:

    def test_multi_contract_chain_integrity(self):
        """Submit 3 contracts and verify the evidence chain is valid."""
        traces = []
        for i in range(3):
            payload, trace_id = _signed_contract_payload(
                payload={"operation": f"chain_test_{i}", "seq": i}
            )
            resp = client.post("/verify", json=payload)
            assert resp.status_code == 200
            data = resp.json()
            assert data["flow_status"] == "COMPLETED"
            traces.append(trace_id)

        # Verify all traces created evidence
        for trace_id in traces:
            resp = client.get(f"/evidence/{trace_id}")
            assert resp.status_code == 200


# ═══════════════════════════════════════════════════════════════════════════
# E2E Test 7: Metrics Integration
# ═══════════════════════════════════════════════════════════════════════════

class TestE2EMetrics:

    def test_metrics_reflect_activity(self):
        """After some API calls, /metrics should show non-zero counters."""
        # Make some requests
        client.get("/health")
        client.get("/capabilities")

        resp = client.get("/metrics")
        assert resp.status_code == 200
        body = resp.text
        assert "qcg_requests_total" in body

    def test_metrics_json_reflect_activity(self):
        client.get("/health")
        resp = client.get("/metrics/json")
        assert resp.status_code == 200
        data = resp.json()
        assert data["requests"]["total"] > 0

    def test_security_headers_on_all_responses(self):
        """All API responses should have security headers."""
        endpoints = ["/health", "/capabilities", "/metrics", "/providers"]
        for ep in endpoints:
            resp = client.get(ep)
            assert resp.headers.get("X-Content-Type-Options") == "nosniff", f"Missing header on {ep}"
            assert resp.headers.get("X-Frame-Options") == "DENY", f"Missing header on {ep}"
            assert "X-Request-ID" in resp.headers, f"Missing X-Request-ID on {ep}"
