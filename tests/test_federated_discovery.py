"""
test_federated_discovery.py — Unit & Integration Tests for the Secure Federated Capability Fabric

Covers:
- Service identity & certificate authority
- Heartbeat & lease management
- Federation sync & conflict resolution
- Audit chain integrity
- SDK discovery, invocation, evidence
- Quantum trust providers
- Circuit breaker states
"""

import hashlib
import json
import os
import sys
import tempfile
import time
import threading
import unittest
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from service_identity import (
    ServiceCertificateAuthority,
    MutualAuthenticator,
    ServiceCertificate,
    AuthResult,
)
from heartbeat_manager import HeartbeatManager, ServiceLease
from federated_registry import (
    FederatedRegistryNode,
    FederationAuditLog,
    FederationEvent,
    ConflictResolver,
)
from platform_service_registry import (
    PlatformServiceRegistry,
    PlatformServiceRecord,
    CapabilityManifest,
    OperationContract,
    RegistrationEvidenceRecorder,
)
from node_identity import NodeSigner, NodeProof
from quantum_trust_provider import (
    ClassicalTrustProvider,
    PostQuantumTrustProvider,
    HybridTrustProvider,
    SimulatedQRNGProvider,
    QuantumTrustProviderInterface,
    create_trust_provider,
)
from platform_capability_sdk import CircuitBreaker, CircuitState, SDKEvidenceChain
from sdk_models import InvocationEvidence


# ---------------------------------------------------------------------------
# Test Helpers
# ---------------------------------------------------------------------------

def _make_record(sid: str, version: str = "1.0.0", timestamp: str = "") -> PlatformServiceRecord:
    return PlatformServiceRecord(
        platform_service_id=sid,
        capability_id=f"cap-{sid}",
        service_name=f"Service_{sid}",
        version=version,
        provider="TEST",
        owner={"team": "Test", "contact": "test@test.com"},
        runtime_type="PROCESS",
        service_classification="PLATFORM_SERVICE",
        capability_category="VERIFICATION",
        status="ACTIVE",
        registration_timestamp=timestamp or "2026-01-01T00:00:00Z",
    )


# ===========================================================================
# Service Identity Tests
# ===========================================================================

class TestServiceCertificateAuthority(unittest.TestCase):
    def setUp(self):
        self.ca = ServiceCertificateAuthority("TEST-CA")

    def test_issue_certificate(self):
        cert = self.ca.issue_certificate("SVC-001", "deadbeef" * 8)
        self.assertEqual(cert.service_id, "SVC-001")
        self.assertFalse(cert.is_expired())
        self.assertTrue(cert.serial_number.startswith("TANTRA-CERT-"))

    def test_verify_valid_certificate(self):
        signer = NodeSigner("SVC-002", "TEST")
        cert = self.ca.issue_certificate("SVC-002", signer.identity.public_key)
        self.assertTrue(self.ca.verify_certificate(cert))

    def test_revoke_certificate(self):
        cert = self.ca.issue_certificate("SVC-003", "aabbccdd" * 8)
        self.assertTrue(self.ca.revoke_certificate(cert.serial_number))
        self.assertTrue(self.ca.is_revoked(cert.serial_number))
        self.assertFalse(self.ca.verify_certificate(cert))

    def test_expired_certificate(self):
        cert = self.ca.issue_certificate("SVC-004", "11223344" * 8, ttl_seconds=0)
        time.sleep(0.1)
        self.assertTrue(cert.is_expired())
        self.assertFalse(self.ca.verify_certificate(cert))

    def test_list_active_certificates(self):
        self.ca.issue_certificate("SVC-A", "aa" * 32)
        cert_b = self.ca.issue_certificate("SVC-B", "bb" * 32)
        self.ca.revoke_certificate(cert_b.serial_number)
        active = self.ca.list_active_certificates()
        self.assertEqual(len(active), 1)
        self.assertEqual(active[0].service_id, "SVC-A")


class TestMutualAuthentication(unittest.TestCase):
    def setUp(self):
        self.ca = ServiceCertificateAuthority("TEST-CA")
        self.auth = MutualAuthenticator(self.ca)

    def test_successful_authentication(self):
        signer = NodeSigner("SVC-001", "TEST")
        cert = self.ca.issue_certificate("SVC-001", signer.identity.public_key)
        payload = {"action": "register", "service_id": "SVC-001"}
        proof = signer.sign_payload(payload)
        result = self.auth.authenticate("SVC-001", proof, cert, payload)
        self.assertTrue(result.authenticated)

    def test_mismatched_service_id(self):
        signer = NodeSigner("SVC-001", "TEST")
        cert = self.ca.issue_certificate("SVC-002", signer.identity.public_key)
        payload = {"action": "register"}
        proof = signer.sign_payload(payload)
        result = self.auth.authenticate("SVC-001", proof, cert, payload)
        self.assertFalse(result.authenticated)
        self.assertIn("mismatch", result.reason.lower())

    def test_revoked_certificate_auth(self):
        signer = NodeSigner("SVC-001", "TEST")
        cert = self.ca.issue_certificate("SVC-001", signer.identity.public_key)
        self.ca.revoke_certificate(cert.serial_number)
        payload = {"action": "register"}
        proof = signer.sign_payload(payload)
        result = self.auth.authenticate("SVC-001", proof, cert, payload)
        self.assertFalse(result.authenticated)


# ===========================================================================
# Heartbeat Manager Tests
# ===========================================================================

class TestHeartbeatManager(unittest.TestCase):
    def setUp(self):
        self.hb = HeartbeatManager(ttl_seconds=2, check_interval=1)

    def test_grant_lease(self):
        lease = self.hb.grant_lease("SVC-001")
        self.assertEqual(lease.service_id, "SVC-001")
        self.assertEqual(lease.status, "ACTIVE")
        self.assertFalse(lease.is_expired())

    def test_renew_lease(self):
        self.hb.grant_lease("SVC-001")
        lease = self.hb.renew_lease("SVC-001")
        self.assertIsNotNone(lease)
        self.assertEqual(lease.renewal_count, 1)

    def test_heartbeat_received(self):
        self.hb.grant_lease("SVC-001")
        accepted = self.hb.receive_heartbeat("SVC-001")
        self.assertTrue(accepted)

    def test_heartbeat_rejected_no_lease(self):
        accepted = self.hb.receive_heartbeat("SVC-UNKNOWN")
        self.assertFalse(accepted)

    def test_lease_expiry(self):
        self.hb = HeartbeatManager(ttl_seconds=0, check_interval=1)
        self.hb.grant_lease("SVC-001")
        time.sleep(0.1)
        expired = self.hb.check_expired()
        self.assertIn("SVC-001", expired)

    def test_revoke_lease(self):
        self.hb.grant_lease("SVC-001")
        revoked = self.hb.revoke_lease("SVC-001")
        self.assertTrue(revoked)
        lease = self.hb.get_lease("SVC-001")
        self.assertEqual(lease.status, "REVOKED")

    def test_has_active_lease(self):
        self.hb.grant_lease("SVC-001")
        self.assertTrue(self.hb.has_active_lease("SVC-001"))
        self.assertFalse(self.hb.has_active_lease("SVC-UNKNOWN"))


# ===========================================================================
# Federation Tests
# ===========================================================================

class TestConflictResolver(unittest.TestCase):
    def test_higher_version_wins(self):
        local = _make_record("SVC-001", "1.0.0")
        remote = _make_record("SVC-001", "2.0.0")
        winner = ConflictResolver.resolve(local, remote)
        self.assertEqual(winner.version, "2.0.0")

    def test_earlier_timestamp_wins_on_same_version(self):
        local = _make_record("SVC-001", "1.0.0", "2026-01-02T00:00:00Z")
        remote = _make_record("SVC-001", "1.0.0", "2026-01-01T00:00:00Z")
        winner = ConflictResolver.resolve(local, remote)
        self.assertEqual(winner.registration_timestamp, "2026-01-01T00:00:00Z")

    def test_deterministic_resolution(self):
        a = _make_record("SVC-001", "1.0.0", "2026-01-01T00:00:00Z")
        b = _make_record("SVC-001", "1.0.0", "2026-01-01T00:00:00Z")
        winner1 = ConflictResolver.resolve(a, b)
        winner2 = ConflictResolver.resolve(a, b)
        self.assertEqual(winner1.service_name, winner2.service_name)


class TestFederationSync(unittest.TestCase):
    def setUp(self):
        self.node1 = FederatedRegistryNode("NODE-1", port=19010)
        self.node2 = FederatedRegistryNode("NODE-2", port=19011)
        self.node3 = FederatedRegistryNode("NODE-3", port=19012)
        self.node1.add_peer(self.node2)
        self.node1.add_peer(self.node3)
        self.node2.add_peer(self.node1)
        self.node2.add_peer(self.node3)
        self.node3.add_peer(self.node1)
        self.node3.add_peer(self.node2)

    def test_sync_propagates_services(self):
        record = _make_record("SVC-001")
        self.node1.register_service_authenticated(record)
        self.node2.sync_with_peer("NODE-1")
        self.assertIsNotNone(self.node2.registry.get_service("SVC-001"))

    def test_no_duplicates_survive_federation(self):
        record = _make_record("SVC-001")
        self.node1.register_service_authenticated(record)
        self.node2.register_service_authenticated(record)
        self.node1.sync_with_peer("NODE-2")
        self.node2.sync_with_peer("NODE-1")
        # Both should have exactly one copy
        self.assertEqual(len(self.node1.registry.list_services()), 1)
        self.assertEqual(len(self.node2.registry.list_services()), 1)

    def test_anti_entropy_sync_all_peers(self):
        self.node1.register_service_authenticated(_make_record("SVC-A"))
        self.node2.register_service_authenticated(_make_record("SVC-B"))
        self.node3.register_service_authenticated(_make_record("SVC-C"))

        for node in [self.node1, self.node2, self.node3]:
            node.anti_entropy_sync()

        for node in [self.node1, self.node2, self.node3]:
            services = node.registry.list_services()
            sids = {s["platform_service_id"] for s in services}
            self.assertEqual(sids, {"SVC-A", "SVC-B", "SVC-C"})


class TestFederationAuditLog(unittest.TestCase):
    def test_chain_integrity(self):
        log = FederationAuditLog()
        for i in range(5):
            event = FederationEvent(
                event_id=f"evt-{i}",
                event_type="TEST_EVENT",
                source_node_id="NODE-1",
                target_node_id="",
                payload={"index": i},
                vector_clock={"NODE-1": i},
                timestamp="2026-01-01T00:00:00Z",
                nonce=f"nonce-{i}",
            )
            log.record(event)
        self.assertTrue(log.verify_chain())
        self.assertEqual(len(log), 5)

    def test_replay_safe_events(self):
        node = FederatedRegistryNode("NODE-1", port=19010)
        record = _make_record("SVC-001")
        node.register_service_authenticated(record)
        events = node.get_audit_log()
        # Each event has a unique nonce
        nonces = [e["nonce"] for e in events]
        self.assertEqual(len(nonces), len(set(nonces)))


# ===========================================================================
# Quantum Trust Provider Tests
# ===========================================================================

class TestClassicalTrustProvider(unittest.TestCase):
    def setUp(self):
        self.provider = ClassicalTrustProvider()

    def test_sign_verify(self):
        kp = self.provider.generate_key_pair()
        data = b"test-data"
        sig = self.provider.sign(data, kp.private_key_handle)
        self.assertTrue(self.provider.verify(data, sig, kp.public_key))

    def test_verify_tampered_data(self):
        kp = self.provider.generate_key_pair()
        data = b"test-data"
        sig = self.provider.sign(data, kp.private_key_handle)
        self.assertFalse(self.provider.verify(b"tampered", sig, kp.public_key))

    def test_trust_level(self):
        self.assertEqual(self.provider.trust_level(), "CLASSICAL")


class TestPostQuantumTrustProvider(unittest.TestCase):
    def setUp(self):
        self.provider = PostQuantumTrustProvider()

    def test_keygen(self):
        kp = self.provider.generate_key_pair()
        self.assertIsNotNone(kp.public_key)
        self.assertEqual(kp.trust_level, "POST_QUANTUM")

    def test_sign(self):
        kp = self.provider.generate_key_pair()
        data = b"pq-test-data"
        sig = self.provider.sign(data, kp.private_key_handle)
        self.assertIsInstance(sig, bytes)
        self.assertTrue(len(sig) > 0)

    def test_key_exchange(self):
        kp = self.provider.generate_key_pair()
        shared = self.provider.key_exchange(kp.public_key)
        self.assertEqual(len(shared), 32)

    def test_trust_level(self):
        self.assertEqual(self.provider.trust_level(), "POST_QUANTUM")


class TestHybridTrustProvider(unittest.TestCase):
    def setUp(self):
        self.provider = HybridTrustProvider()

    def test_keygen(self):
        kp = self.provider.generate_key_pair()
        self.assertIsNotNone(kp.public_key)
        self.assertEqual(kp.trust_level, "HYBRID")

    def test_sign(self):
        kp = self.provider.generate_key_pair()
        sig = self.provider.sign(b"hybrid-data", kp.private_key_handle)
        self.assertIsInstance(sig, bytes)
        self.assertTrue(len(sig) > 0)

    def test_trust_level(self):
        self.assertEqual(self.provider.trust_level(), "HYBRID")


class TestQRNG(unittest.TestCase):
    def test_simulated_qrng(self):
        qrng = SimulatedQRNGProvider()
        data = qrng.get_random_bytes(32)
        self.assertEqual(len(data), 32)
        # Two calls should produce different output
        data2 = qrng.get_random_bytes(32)
        self.assertNotEqual(data, data2)

    def test_qrng_int(self):
        qrng = SimulatedQRNGProvider()
        val = qrng.get_random_int(1, 100)
        self.assertGreaterEqual(val, 1)
        self.assertLessEqual(val, 100)


class TestQKDInterface(unittest.TestCase):
    def test_bb84(self):
        qkd = QuantumTrustProviderInterface()
        channel = qkd.negotiate_quantum_channel("PEER-1", "BB84")
        key = qkd.distribute_key_bb84(channel)
        self.assertEqual(len(key.key_bytes), 32)
        self.assertEqual(key.protocol, "BB84")

    def test_e91(self):
        qkd = QuantumTrustProviderInterface()
        channel = qkd.negotiate_quantum_channel("PEER-1", "E91")
        key = qkd.distribute_key_e91(channel)
        self.assertEqual(len(key.key_bytes), 32)
        self.assertEqual(key.protocol, "E91")


class TestTrustProviderFactory(unittest.TestCase):
    def test_create_classical(self):
        p = create_trust_provider("CLASSICAL")
        self.assertEqual(p.trust_level(), "CLASSICAL")

    def test_create_post_quantum(self):
        p = create_trust_provider("POST_QUANTUM")
        self.assertEqual(p.trust_level(), "POST_QUANTUM")

    def test_create_hybrid(self):
        p = create_trust_provider("HYBRID")
        self.assertEqual(p.trust_level(), "HYBRID")

    def test_invalid_level(self):
        with self.assertRaises(ValueError):
            create_trust_provider("INVALID")


# ===========================================================================
# Circuit Breaker Tests
# ===========================================================================

class TestCircuitBreaker(unittest.TestCase):
    def test_initial_state_closed(self):
        cb = CircuitBreaker(failure_threshold=3, reset_timeout=1.0)
        self.assertEqual(cb.state, CircuitState.CLOSED)
        self.assertTrue(cb.allow_request())

    def test_opens_after_threshold(self):
        cb = CircuitBreaker(failure_threshold=3, reset_timeout=1.0)
        for _ in range(3):
            cb.record_failure()
        self.assertEqual(cb.state, CircuitState.OPEN)
        self.assertFalse(cb.allow_request())

    def test_half_open_after_timeout(self):
        cb = CircuitBreaker(failure_threshold=2, reset_timeout=0.1)
        cb.record_failure()
        cb.record_failure()
        self.assertEqual(cb.state, CircuitState.OPEN)
        time.sleep(0.15)
        self.assertEqual(cb.state, CircuitState.HALF_OPEN)
        self.assertTrue(cb.allow_request())

    def test_closes_on_success(self):
        cb = CircuitBreaker(failure_threshold=2, reset_timeout=0.1)
        cb.record_failure()
        cb.record_failure()
        time.sleep(0.15)
        cb.record_success()
        self.assertEqual(cb.state, CircuitState.CLOSED)


# ===========================================================================
# SDK Evidence Chain Tests
# ===========================================================================

class TestSDKEvidenceChain(unittest.TestCase):
    def test_chain_integrity(self):
        chain = SDKEvidenceChain()
        for i in range(5):
            ev = InvocationEvidence(
                invocation_id=f"inv-{i}",
                service_id="SVC-001",
                operation="test",
                request_hash=f"req-{i}",
                response_hash=f"resp-{i}",
                trust_method="CLASSICAL",
                duration_ms=i * 10.0,
                status="SUCCESS",
            )
            chain.record(ev)
        self.assertTrue(chain.verify_chain())
        self.assertEqual(len(chain), 5)

    def test_empty_chain_valid(self):
        chain = SDKEvidenceChain()
        self.assertTrue(chain.verify_chain())


# ===========================================================================
# Version Negotiation Tests (via SDK)
# ===========================================================================

class TestVersionNegotiationThroughRegistry(unittest.TestCase):
    def setUp(self):
        self.registry = PlatformServiceRegistry()
        self.registry.negotiator.register_compatibility(
            "SVC-001",
            compatible=["1.0.0", "1.1.0"],
            deprecated=["0.9.0"],
            unsupported=["0.1.0"],
        )

    def test_compatible_version(self):
        result = self.registry.negotiate_version("SVC-001", "1.0.0")
        self.assertEqual(result["status"], "COMPATIBLE")

    def test_deprecated_version(self):
        result = self.registry.negotiate_version("SVC-001", "0.9.0")
        self.assertEqual(result["status"], "DEPRECATED")

    def test_unsupported_version(self):
        result = self.registry.negotiate_version("SVC-001", "0.1.0")
        self.assertEqual(result["status"], "UNSUPPORTED")

    def test_unknown_version(self):
        result = self.registry.negotiate_version("SVC-001", "99.0.0")
        self.assertEqual(result["status"], "UNSUPPORTED")


# ===========================================================================
# Manifest Validation Tests
# ===========================================================================

class TestManifestContractValidation(unittest.TestCase):
    def test_valid_contract(self):
        from platform_capability_sdk import PlatformCapabilitySDK
        sdk = PlatformCapabilitySDK.__new__(PlatformCapabilitySDK)
        manifest = {
            "supported_operations": [
                {
                    "operation_name": "test_op",
                    "input_contract": {"type": "object", "required": ["field_a"]},
                    "output_contract": {"type": "object"},
                }
            ]
        }
        self.assertTrue(sdk.validate_contract("test_op", {"field_a": "value"}, manifest))

    def test_missing_required_field(self):
        from platform_capability_sdk import PlatformCapabilitySDK
        sdk = PlatformCapabilitySDK.__new__(PlatformCapabilitySDK)
        manifest = {
            "supported_operations": [
                {
                    "operation_name": "test_op",
                    "input_contract": {"type": "object", "required": ["field_a"]},
                    "output_contract": {"type": "object"},
                }
            ]
        }
        self.assertFalse(sdk.validate_contract("test_op", {"field_b": "value"}, manifest))


if __name__ == "__main__":
    unittest.main(verbosity=2)
