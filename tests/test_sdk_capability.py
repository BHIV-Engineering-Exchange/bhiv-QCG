"""
tests/test_sdk_capability.py — Phase 2: Platform Capability SDK Tests

Validates CircuitBreaker, SDKEvidenceChain, SDKAuthenticator, and
PlatformCapabilitySDK contracts.
"""

import pytest
import sys
import os
import time
import hashlib
import json
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from platform_capability_sdk import (
    CircuitBreaker,
    CircuitState,
    SDKEvidenceChain,
    PlatformCapabilitySDK,
)
from sdk_models import InvocationEvidence
from sdk_auth import SDKAuthenticator
from quantum_trust_provider import ClassicalTrustProvider


# ---------------------------------------------------------------------------
# CircuitBreaker Tests
# ---------------------------------------------------------------------------

class TestCircuitBreaker:

    def test_initial_state_is_closed(self):
        cb = CircuitBreaker(failure_threshold=3, reset_timeout=1.0)
        assert cb.state == CircuitState.CLOSED
        assert cb.allow_request() is True

    def test_transitions_to_open_on_threshold(self):
        cb = CircuitBreaker(failure_threshold=3, reset_timeout=10.0)
        cb.record_failure()
        cb.record_failure()
        assert cb.state == CircuitState.CLOSED
        cb.record_failure()
        assert cb.state == CircuitState.OPEN
        assert cb.allow_request() is False

    def test_transitions_to_half_open_on_timeout(self):
        cb = CircuitBreaker(failure_threshold=2, reset_timeout=0.1)
        cb.record_failure()
        cb.record_failure()
        assert cb.state == CircuitState.OPEN
        time.sleep(0.15)
        assert cb.state == CircuitState.HALF_OPEN
        assert cb.allow_request() is True

    def test_transitions_closed_on_success_from_half_open(self):
        cb = CircuitBreaker(failure_threshold=2, reset_timeout=0.1)
        cb.record_failure()
        cb.record_failure()
        time.sleep(0.15)
        assert cb.state == CircuitState.HALF_OPEN
        cb.record_success()
        assert cb.state == CircuitState.CLOSED

    def test_get_status_returns_dict(self):
        cb = CircuitBreaker(failure_threshold=5, reset_timeout=60.0)
        status = cb.get_status()
        assert status["state"] == "CLOSED"
        assert status["failure_count"] == 0
        assert status["failure_threshold"] == 5

    def test_success_resets_failure_count(self):
        cb = CircuitBreaker(failure_threshold=5, reset_timeout=60.0)
        cb.record_failure()
        cb.record_failure()
        cb.record_success()
        assert cb.get_status()["failure_count"] == 0


# ---------------------------------------------------------------------------
# SDKEvidenceChain Tests
# ---------------------------------------------------------------------------

class TestSDKEvidenceChain:

    def test_empty_chain_is_valid(self):
        chain = SDKEvidenceChain()
        assert chain.verify_chain() is True
        assert len(chain) == 0

    def test_genesis_hash_is_deterministic(self):
        chain = SDKEvidenceChain()
        expected = hashlib.sha256(b"SDK_EVIDENCE_GENESIS").hexdigest()
        assert chain.head_hash == expected

    def test_record_appends_and_chains(self):
        chain = SDKEvidenceChain()
        genesis = chain.head_hash

        ev = InvocationEvidence(
            invocation_id="inv-001",
            service_id="svc-001",
            operation="execute",
            request_hash="req-hash-1",
            response_hash="resp-hash-1",
            trust_method="CLASSICAL",
            duration_ms=42.0,
            status="SUCCESS",
        )
        recorded = chain.record(ev)

        assert len(chain) == 1
        assert recorded.previous_evidence_hash == genesis
        assert recorded.evidence_hash != ""
        assert chain.head_hash == recorded.evidence_hash
        assert chain.verify_chain() is True

    def test_chain_integrity_after_multiple_records(self):
        chain = SDKEvidenceChain()
        for i in range(5):
            ev = InvocationEvidence(
                invocation_id=f"inv-{i}",
                service_id="svc-001",
                operation="op",
                request_hash=f"rq-{i}",
                response_hash=f"rs-{i}",
                trust_method="CLASSICAL",
                duration_ms=float(i),
                status="SUCCESS",
            )
            chain.record(ev)
        assert len(chain) == 5
        assert chain.verify_chain() is True

    def test_tamper_detection(self):
        chain = SDKEvidenceChain()
        ev = InvocationEvidence(
            invocation_id="inv-tamper",
            service_id="svc-001",
            operation="op",
            request_hash="rq",
            response_hash="rs",
            trust_method="CLASSICAL",
            duration_ms=1.0,
            status="SUCCESS",
        )
        recorded = chain.record(ev)
        # Tamper with the evidence hash
        recorded.evidence_hash = "tampered_hash"
        assert chain.verify_chain() is False

    def test_get_all_returns_dicts(self):
        chain = SDKEvidenceChain()
        ev = InvocationEvidence(
            invocation_id="inv-dict",
            service_id="svc-001",
            operation="op",
            request_hash="rq",
            response_hash="rs",
            trust_method="CLASSICAL",
            duration_ms=1.0,
            status="SUCCESS",
        )
        chain.record(ev)
        all_ev = chain.get_all()
        assert len(all_ev) == 1
        assert isinstance(all_ev[0], dict)
        assert all_ev[0]["invocation_id"] == "inv-dict"


# ---------------------------------------------------------------------------
# SDKAuthenticator Tests
# ---------------------------------------------------------------------------

class TestSDKAuthenticator:

    def test_auth_header_generation(self):
        provider = ClassicalTrustProvider()
        auth = SDKAuthenticator("test-service", provider)
        auth.initialise()

        headers = auth.build_auth_headers({"key": "value"})
        assert "X-Service-ID" in headers
        assert headers["X-Service-ID"] == "test-service"
        assert "X-Service-Signature" in headers
        assert "X-Service-PublicKey" in headers
        assert "X-Trust-Level" in headers

    def test_sign_payload_returns_hex(self):
        provider = ClassicalTrustProvider()
        auth = SDKAuthenticator("test-service", provider)
        auth.initialise()

        sig = auth.sign_payload({"data": "test"})
        assert isinstance(sig, str)
        # Should be valid hex
        bytes.fromhex(sig)

    def test_empty_payload_handled_gracefully(self):
        provider = ClassicalTrustProvider()
        auth = SDKAuthenticator("test-service", provider)
        auth.initialise()

        # Should not raise, should log a warning and use empty dict
        headers = auth.build_auth_headers(None)
        assert "X-Service-ID" in headers

    def test_verify_response_empty_signature_returns_false(self):
        provider = ClassicalTrustProvider()
        auth = SDKAuthenticator("test-service", provider)
        auth.initialise()

        assert auth.verify_response_signature({"data": "test"}, "", "abcdef") is False

    def test_verify_response_empty_pubkey_returns_false(self):
        provider = ClassicalTrustProvider()
        auth = SDKAuthenticator("test-service", provider)
        auth.initialise()

        assert auth.verify_response_signature({"data": "test"}, "abcdef", "") is False

    def test_public_key_hex(self):
        provider = ClassicalTrustProvider()
        auth = SDKAuthenticator("test-service", provider)
        auth.initialise()

        pk_hex = auth.public_key_hex
        assert isinstance(pk_hex, str)
        assert len(pk_hex) > 0
        # Should be valid hex
        bytes.fromhex(pk_hex)


# ---------------------------------------------------------------------------
# PlatformCapabilitySDK Tests (mocked HTTP)
# ---------------------------------------------------------------------------

class TestPlatformCapabilitySDK:

    def test_invoke_circuit_open_path(self):
        """When circuit breaker is open, invoke should return CIRCUIT_OPEN."""
        sdk = PlatformCapabilitySDK(discovery_urls=["http://localhost:19999"])
        # Trip the breaker
        breaker = sdk._get_breaker("test-svc")
        for _ in range(breaker.failure_threshold):
            breaker.record_failure()
        assert breaker.state == CircuitState.OPEN

        result = sdk.invoke_capability("test-svc", "op", {"data": 1})
        assert result.status == "CIRCUIT_OPEN"
        assert "OPEN" in result.error

    def test_invoke_service_not_found_path(self):
        """When service is not found, invoke should return SERVICE_NOT_FOUND."""
        sdk = PlatformCapabilitySDK(
            discovery_urls=["http://localhost:19999"],
            max_retries=0,
        )
        # Mock negotiate to succeed but get_service to return None
        with patch.object(sdk, 'negotiate_version') as mock_neg:
            mock_neg.return_value = MagicMock(
                status="COMPATIBLE",
                negotiated_version="1.0.0",
                to_dict=lambda: {},
            )
            with patch.object(sdk, 'get_service', return_value=None):
                result = sdk.invoke_capability("missing-svc", "op", {"data": 1})
        assert result.status == "SERVICE_NOT_FOUND"

    def test_invoke_success_with_mock(self):
        """Mock a successful invocation and verify evidence is collected."""
        os.environ["QCG_MOCK_SDK"] = "1"
        try:
            sdk = PlatformCapabilitySDK(discovery_urls=["http://localhost:19999"])
            result = sdk.invoke_capability("mock-svc", "op", {"data": 1})
            assert result.status == "SUCCESS"
            assert result.evidence is not None
            assert len(sdk.evidence) == 1
            assert sdk.evidence.verify_chain() is True
        finally:
            del os.environ["QCG_MOCK_SDK"]

    def test_evidence_chain_integrity_across_invocations(self):
        """Multiple mock invocations produce a valid evidence chain."""
        os.environ["QCG_MOCK_SDK"] = "1"
        try:
            sdk = PlatformCapabilitySDK(discovery_urls=["http://localhost:19999"])
            for i in range(5):
                result = sdk.invoke_capability(f"svc-{i}", "op", {"i": i})
                assert result.status == "SUCCESS"
            assert len(sdk.evidence) == 5
            assert sdk.evidence.verify_chain() is True
        finally:
            del os.environ["QCG_MOCK_SDK"]
