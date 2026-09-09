"""
tests/test_platform_discovery_fastapi.py — Phase 2: Platform Discovery Tests

Tests the FastAPI discovery server endpoints, security middleware, 
payload sanitization, and the new `/v1/metrics` endpoint.
"""

import pytest
import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from platform_discovery_fastapi import app, registry
import config


client = TestClient(app)

# ═══════════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════════

@pytest.fixture(autouse=True)
def clear_registry():
    """Ensure a clean registry before each test."""
    registry._services.clear()
    yield
    registry._services.clear()


def _make_valid_service_record(service_id="test-service-1"):
    return {
        "service_id": service_id,
        "record": {
            "platform_service_id": service_id,
            "capability_id": "test-cap-1",
            "service_name": "Test Service",
            "version": "1.0.0",
            "status": "ACTIVE"
        }
    }


# ═══════════════════════════════════════════════════════════════════════════
# Health & Middleware Endpoints
# ═══════════════════════════════════════════════════════════════════════════

class TestHealthAndMiddleware:

    def test_health_returns_200(self):
        resp = client.get("/v1/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "UP"
        assert "uptime_seconds" in data
        assert "total_requests" in data

    def test_health_live_returns_200(self):
        resp = client.get("/v1/health/live")
        assert resp.status_code == 200
        assert resp.json()["ready"] is True

    def test_security_headers_present(self):
        resp = client.get("/v1/health")
        assert resp.headers.get("X-Content-Type-Options") == "nosniff"
        assert resp.headers.get("X-Frame-Options") == "DENY"
        assert "X-Request-ID" in resp.headers

    def test_correlation_id_echoed(self):
        resp = client.get("/v1/health", headers={"X-Request-ID": "custom-id-123"})
        assert resp.headers.get("X-Request-ID") == "custom-id-123"

    def test_metrics_prometheus_export(self):
        # Register a service to bump the gauge
        client.post("/v1/register", json=_make_valid_service_record())
        
        resp = client.get("/v1/metrics")
        assert resp.status_code == 200
        body = resp.text
        # Check standard metrics from MetricsCollector
        assert "qcg_uptime_seconds" in body
        assert "qcg_requests_total" in body
        # Check specific platform metrics
        assert "tantra_platform_services_registered 1" in body


# ═══════════════════════════════════════════════════════════════════════════
# Registration & Validation
# ═══════════════════════════════════════════════════════════════════════════

class TestRegistrationEndpoints:

    def test_register_valid_service(self):
        payload = _make_valid_service_record("svc-1")
        resp = client.post("/v1/register", json=payload)
        assert resp.status_code == 200
        assert resp.json()["status"] == "REGISTERED"

    def test_register_duplicate_returns_already_registered(self):
        payload = _make_valid_service_record("svc-1")
        client.post("/v1/register", json=payload)
        resp2 = client.post("/v1/register", json=payload)
        assert resp2.status_code == 200
        assert resp2.json()["status"] == "ALREADY_REGISTERED"

    def test_register_missing_service_id(self):
        payload = {"record": {"capability_id": "cap-1"}}
        resp = client.post("/v1/register", json=payload)
        assert resp.status_code == 400

    def test_list_services_after_registration(self):
        client.post("/v1/register", json=_make_valid_service_record("svc-1"))
        client.post("/v1/register", json=_make_valid_service_record("svc-2"))
        resp = client.get("/v1/services")
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] == 2


# ═══════════════════════════════════════════════════════════════════════════
# Input Sanitization & Boundaries
# ═══════════════════════════════════════════════════════════════════════════

class TestInputSanitization:

    def test_payload_keys_limit_exceeded(self):
        payload = _make_valid_service_record("svc-1")
        # Add too many keys to root
        for i in range(config.INPUT_PAYLOAD_MAX_KEYS + 5):
            payload[f"extra_key_{i}"] = i
            
        resp = client.post("/v1/register", json=payload)
        assert resp.status_code == 413
        assert "Payload exceeds maximum keys limit" in resp.json()["detail"]

    def test_payload_size_limit_exceeded(self):
        # The test client doesn't automatically set Content-Length for large dicts in a way 
        # that Starlette Request.headers.get("content-length") catches during the 
        # synchronous pre-check, so we mock the header explicitly.
        payload = _make_valid_service_record("svc-1")
        headers = {"content-length": str(config.MAX_REQUEST_BODY_SIZE + 10)}
        resp = client.post("/v1/register", json=payload, headers=headers)
        assert resp.status_code == 413
        assert "Request body too large" in resp.json()["detail"]

    def test_service_id_control_chars_sanitized(self):
        # Include a null byte and a newline in the requested service_id
        dirty_id = "test\x00-service\n-1"
        clean_id = "test-service-1"
        payload = _make_valid_service_record(dirty_id)
        
        resp = client.post("/v1/register", json=payload)
        assert resp.status_code == 200
        
        # Check the registry if the sanitized ID was used
        resp = client.get(f"/v1/services/{clean_id}")
        assert resp.status_code == 200

    def test_invalid_json_returns_400(self):
        resp = client.post("/v1/register", content="NOT JSON", headers={"Content-Type": "application/json"})
        assert resp.status_code == 400


# ═══════════════════════════════════════════════════════════════════════════
# Service Lifecycle (Heartbeat, Negotiate, Revoke)
# ═══════════════════════════════════════════════════════════════════════════

class TestServiceLifecycle:

    def test_heartbeat_updates_service(self):
        client.post("/v1/register", json=_make_valid_service_record("svc-1"))
        
        resp = client.post("/v1/heartbeat", json={"service_id": "svc-1", "status": "DEPRECATED"})
        assert resp.status_code == 200
        
        svc_resp = client.get("/v1/services/svc-1")
        assert svc_resp.json()["status"] == "DEPRECATED"

    def test_negotiate_version_success(self):
        client.post("/v1/register", json=_make_valid_service_record("svc-1"))
        
        resp = client.post("/v1/negotiate", json={"service_id": "svc-1", "version": "1.0.0"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "COMPATIBLE"
        assert data["negotiated_version"] == "1.0.0"

    def test_negotiate_version_not_found(self):
        resp = client.post("/v1/negotiate", json={"service_id": "nonexistent", "version": "1.0.0"})
        assert resp.status_code == 200
        assert resp.json()["status"] == "UNKNOWN_SERVICE"

    def test_revoke_service(self):
        client.post("/v1/register", json=_make_valid_service_record("svc-1"))
        
        resp = client.post("/v1/revoke", json={"service_id": "svc-1", "reason": "testing"})
        assert resp.status_code == 200
        
        svc_resp = client.get("/v1/services/svc-1")
        assert svc_resp.status_code == 404
