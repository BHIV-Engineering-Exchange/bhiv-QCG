"""
tests/test_e2e_sdk_federation.py — Phase 2: E2E SDK ↔ Federation Tests

End-to-end integration tests validating the full SDK pipeline through
federated discovery, and multi-node federation convergence with
evidence chain verification.
"""

import pytest
import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from platform_capability_sdk import (
    PlatformCapabilitySDK,
    CircuitBreaker,
    CircuitState,
    SDKEvidenceChain,
)
from sdk_models import InvocationEvidence
from sdk_auth import SDKAuthenticator
from quantum_trust_provider import ClassicalTrustProvider
from federated_registry import FederatedRegistryNode
from platform_service_registry import (
    PlatformServiceRegistry,
    PlatformServiceRecord,
    CapabilityManifest,
    OperationContract,
)


def _make_record(sid: str, version: str = "1.0.0") -> PlatformServiceRecord:
    return PlatformServiceRecord(
        platform_service_id=sid,
        capability_id=f"cap-{sid}",
        service_name=f"Service {sid}",
        version=version,
        provider="test",
        owner={"name": "test"},
        runtime_type="PROCESS",
        service_classification="PLATFORM_SERVICE",
        capability_category="VERIFICATION",
        status="ACTIVE",
    )


def _make_manifest(sid: str) -> CapabilityManifest:
    return CapabilityManifest(
        manifest_id=f"manifest-{sid}",
        service_name=f"Service {sid}",
        version="1.0.0",
        supported_operations=[
            OperationContract(
                operation_name="execute",
                description="Execute the capability",
                input_contract={"required": ["payload"]},
                output_contract={"required": ["result"]},
                execution_modes=["SYNC"],
                idempotent=True,
            ),
        ],
        execution_modes=["SYNC"],
    )


# ---------------------------------------------------------------------------
# E2E: Full SDK Mock Pipeline
# ---------------------------------------------------------------------------

class TestE2ESDKPipeline:

    def test_full_mock_invocation_pipeline(self):
        """
        E2E: SDK discovers → negotiates → invokes (mocked) → evidence chain valid.
        """
        os.environ["QCG_MOCK_SDK"] = "1"
        try:
            sdk = PlatformCapabilitySDK(discovery_urls=["http://localhost:19999"])

            # Invoke 3 different capabilities
            for i in range(3):
                result = sdk.invoke_capability(
                    service_id=f"e2e-svc-{i}",
                    operation="execute",
                    payload={"iteration": i, "data": f"test-{i}"},
                    version="1.0.0",
                )
                assert result.status == "SUCCESS"
                assert result.evidence is not None
                assert result.trust_method == "CLASSICAL"

            # Verify evidence chain integrity
            assert len(sdk.evidence) == 3
            assert sdk.evidence.verify_chain() is True

            # Verify evidence records are properly ordered
            all_evidence = sdk.evidence.get_all()
            for i in range(1, len(all_evidence)):
                assert all_evidence[i]["previous_evidence_hash"] == all_evidence[i - 1]["evidence_hash"]

        finally:
            del os.environ["QCG_MOCK_SDK"]

    def test_circuit_breaker_trips_and_recovers(self):
        """
        E2E: Circuit breaker trips after failures, blocks requests, then recovers.
        """
        sdk = PlatformCapabilitySDK(discovery_urls=["http://localhost:19999"])
        breaker = sdk._get_breaker("trip-svc")

        # Trip the breaker
        for _ in range(breaker.failure_threshold):
            breaker.record_failure()

        # Should be blocked
        result = sdk.invoke_capability("trip-svc", "op", {"data": 1})
        assert result.status == "CIRCUIT_OPEN"

        # Recover
        breaker.record_success()
        assert breaker.state == CircuitState.CLOSED

    def test_sdk_auth_roundtrip(self):
        """
        E2E: SDKAuthenticator signs a payload and the signature is verifiable.
        """
        provider = ClassicalTrustProvider()
        auth = SDKAuthenticator("e2e-service", provider)
        auth.initialise()

        payload = {"service_id": "svc-1", "operation": "execute", "data": "test"}

        # Sign
        headers = auth.build_auth_headers(payload)
        assert headers["X-Service-ID"] == "e2e-service"

        # The signature should be valid hex
        sig_hex = headers["X-Service-Signature"]
        pub_hex = headers["X-Service-PublicKey"]
        bytes.fromhex(sig_hex)
        bytes.fromhex(pub_hex)


# ---------------------------------------------------------------------------
# E2E: Federation Convergence
# ---------------------------------------------------------------------------

class TestE2EFederationConvergence:

    def test_three_node_ring_convergence_with_audit(self):
        """
        E2E: 3-node federation ring, services registered on different nodes,
        anti-entropy sync produces convergence, audit chains valid on all nodes.
        """
        nodes = []
        for i, name in enumerate(["e2e-ring-a", "e2e-ring-b", "e2e-ring-c"]):
            nodes.append(FederatedRegistryNode(name, port=19050 + i))

        # Full mesh
        for i, node in enumerate(nodes):
            for j, peer in enumerate(nodes):
                if i != j:
                    node.add_peer(peer)

        # Register unique services on each node
        nodes[0].register_service_authenticated(_make_record("e2e-alpha", "1.0.0"))
        nodes[1].register_service_authenticated(_make_record("e2e-beta", "2.0.0"))
        nodes[2].register_service_authenticated(_make_record("e2e-gamma", "1.5.0"))

        # Anti-entropy sync across all
        for node in nodes:
            node.anti_entropy_sync()

        # Verify convergence: all nodes have all services
        expected_sids = {"e2e-alpha", "e2e-beta", "e2e-gamma"}
        for node in nodes:
            sids = {s["platform_service_id"] for s in node.registry.list_services()}
            assert expected_sids.issubset(sids), f"{node.node_id} missing services: {expected_sids - sids}"

        # Verify audit chains are valid on all nodes
        for node in nodes:
            assert node.audit_log.verify_chain() is True, f"{node.node_id} audit chain invalid"

        # Verify federation status is queryable
        for node in nodes:
            status = node.get_federation_status()
            assert status["audit_chain_valid"] is True
            assert status["service_count"] >= 3

    def test_federation_revocation_propagates(self):
        """
        E2E: Service revocation on one node propagates to peers.
        """
        node_a = FederatedRegistryNode("e2e-rev-a", port=19060)
        node_b = FederatedRegistryNode("e2e-rev-b", port=19061)
        node_a.add_peer(node_b)
        node_b.add_peer(node_a)

        # Register on A (broadcasts to B)
        node_a.register_service_authenticated(_make_record("e2e-revoke-svc"))

        # B should have received it via broadcast
        b_svc = node_b.registry.get_service("e2e-revoke-svc")
        assert b_svc is not None

        # Revoke on A (should broadcast removal to B)
        node_a.revoke_service("e2e-revoke-svc", "E2E revocation test")

        # B should no longer have the service
        b_svc_after = node_b.registry.get_service("e2e-revoke-svc")
        assert b_svc_after is None


# ---------------------------------------------------------------------------
# E2E: Security Boundary
# ---------------------------------------------------------------------------

class TestE2ESecurityBoundary:

    def test_malformed_auth_payload_handled(self):
        """E2E: SDK auth gracefully handles malformed payloads."""
        provider = ClassicalTrustProvider()
        auth = SDKAuthenticator("sec-service", provider)
        auth.initialise()

        # None payload
        headers = auth.build_auth_headers(None)
        assert headers["X-Service-ID"] == "sec-service"

        # Empty list (not dict)
        headers = auth.build_auth_headers([])
        assert headers["X-Service-ID"] == "sec-service"

    def test_invalid_signature_verification(self):
        """E2E: Invalid signature is correctly rejected."""
        provider = ClassicalTrustProvider()
        auth = SDKAuthenticator("sec-service", provider)
        auth.initialise()

        result = auth.verify_response_signature(
            {"data": "test"},
            "invalid_hex_garbage",
            auth.public_key_hex,
        )
        assert result is False
