"""
test_platform_live_integration.py — Live Integration Failure Path Tests

Validates 10 failure-path scenarios across the federated discovery fabric:
1. Federation node failure/recovery
2. Incompatible version rejection
3. Unavailable node graceful handling
4. Duplicate registration rejection
5. Capability failure / circuit breaker
6. Replay attack prevention
7. Deterministic routing / conflict resolution
8. Lease expiry cleanup
9. Certificate revocation
10. Evidence chain integrity
"""

import os
import sys
import time
import uuid
import unittest
from datetime import datetime, timezone
import tempfile
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from platform_service_registry import (
    PlatformServiceRegistry,
    PlatformServiceRecord,
    RegistrationEvidenceRecorder,
)
from federated_registry import FederatedRegistryNode, ConflictResolver, FederationEvent
from heartbeat_manager import HeartbeatManager
from service_identity import ServiceCertificateAuthority
from platform_capability_sdk import CircuitBreaker, CircuitState, SDKEvidenceChain, InvocationEvidence
from canonical_replay_authority import CanonicalReplayAuthority
from replay_registry import ReplayRegistry
import tempfile
from pathlib import Path


def _make_record(sid: str, version: str = "1.0.0", timestamp: str = "") -> PlatformServiceRecord:
    return PlatformServiceRecord(
        platform_service_id=sid,
        capability_id=f"cap-{sid}",
        service_name=f"Service_{sid}",
        version=version,
        provider="TEST",
        owner={"team": "Test"},
        runtime_type="PROCESS",
        service_classification="PLATFORM_SERVICE",
        capability_category="EXECUTION",
        status="ACTIVE",
        registration_timestamp=timestamp or datetime.now(timezone.utc).isoformat(),
    )


class TestPlatformLiveIntegrationFailurePaths(unittest.TestCase):

    def setUp(self):
        self.node1 = FederatedRegistryNode(
            node_id="NODE-1",
            registry=PlatformServiceRegistry(evidence_recorder=RegistrationEvidenceRecorder()),
            port=9210
        )
        self.node2 = FederatedRegistryNode(
            node_id="NODE-2",
            registry=PlatformServiceRegistry(evidence_recorder=RegistrationEvidenceRecorder()),
            port=9211
        )
        self.node1.add_peer(self.node2)
        self.node2.add_peer(self.node1)

    def test_federation_node_failure_recovery(self):
        self.node1.register_service_authenticated(_make_record("test-svc-1"))
        self.node1.anti_entropy_sync()
        self.assertIn("test-svc-1", [s["platform_service_id"] for s in self.node2.registry.list_services()])

        self.node1._peers = {}
        self.node1.register_service_authenticated(_make_record("test-svc-2"))
        self.node1.anti_entropy_sync()
        
        self.assertNotIn("test-svc-2", [s["platform_service_id"] for s in self.node2.registry.list_services()])

        # Recover by re-adding peer
        self.node1.add_peer(self.node2)
        self.node2.add_peer(self.node1)
        self.node1.anti_entropy_sync()
        self.node2.anti_entropy_sync()
        self.assertIn("test-svc-2", [s["platform_service_id"] for s in self.node2.registry.list_services()])

    def test_incompatible_version_rejection(self):
        self.node1.registry.negotiator.register_compatibility(
            service_id="ver-test-svc",
            compatible=["2.0.0"],
            deprecated=["1.0.0"],
            unsupported=["0.5.0"]
        )
        res = self.node1.registry.negotiate_version("ver-test-svc", "2.0.0")
        self.assertEqual(res["status"], "COMPATIBLE")
        
        res = self.node1.registry.negotiate_version("ver-test-svc", "1.0.0")
        self.assertEqual(res["status"], "DEPRECATED")

        res = self.node1.registry.negotiate_version("ver-test-svc", "0.5.0")
        self.assertEqual(res["status"], "UNSUPPORTED")

    def test_unavailable_node_graceful_handling(self):
        from platform_capability_sdk import PlatformCapabilitySDK
        from quantum_trust_provider import ClassicalTrustProvider
        sdk = PlatformCapabilitySDK(
            discovery_urls=["http://127.0.0.1:9999"],
            trust_provider=ClassicalTrustProvider(),
            service_id="TEST-CLIENT"
        )
        services = sdk.discover_services()
        self.assertEqual(len(services), 0)

    def test_duplicate_registration_rejection(self):
        rec = _make_record("dup-test-svc")
        res1 = self.node1.register_service_authenticated(rec)
        self.assertEqual(res1["status"], "REGISTERED")

        res2 = self.node1.register_service_authenticated(rec)
        self.assertEqual(res2["status"], "ALREADY_REGISTERED")

    def test_capability_failure_circuit_breaker(self):
        cb = CircuitBreaker(failure_threshold=3, reset_timeout=0.2)
        self.assertEqual(cb.state, CircuitState.CLOSED)
        self.assertTrue(cb.allow_request())

        for _ in range(3):
            cb.record_failure()
        
        self.assertEqual(cb.state, CircuitState.OPEN)
        self.assertFalse(cb.allow_request())

        time.sleep(0.25)
        self.assertEqual(cb.state, CircuitState.HALF_OPEN)
        self.assertTrue(cb.allow_request())

        cb.record_success()
        self.assertEqual(cb.state, CircuitState.CLOSED)

    def test_replay_attack_prevention(self):
        event = FederationEvent(
            event_id="evt-1",
            event_type="SERVICE_REGISTERED",
            source_node_id="NODE-2",
            target_node_id="",
            payload={"test": True},
            vector_clock={"NODE-2": 1},
            timestamp=datetime.now(timezone.utc).isoformat(),
            nonce="test-nonce-123"
        )
        self.node1.receive_federation_event(event)
        count_before = len(self.node1.audit_log)
        
        self.node1.receive_federation_event(event)
        self.assertEqual(len(self.node1.audit_log), count_before)

        reg = ReplayRegistry(path=Path(tempfile.mktemp()))
        auth = CanonicalReplayAuthority(reg)
        trace_id = "trace-123"
        t = time.time()
        
        res1 = auth.submit(trace_id, t)
        self.assertEqual(res1.status, "VALID")
        
        res2 = auth.submit(trace_id, t)
        self.assertEqual(res2.status, "DUPLICATE")

    def test_deterministic_routing(self):
        rec_a = _make_record("conflict-svc", version="1.0.0", timestamp="2026-01-01T00:00:00Z")
        rec_b = _make_record("conflict-svc", version="2.0.0", timestamp="2026-01-02T00:00:00Z")

        winner1 = ConflictResolver.resolve(rec_a, rec_b)
        self.assertEqual(winner1.version, "2.0.0")

        rec_c = _make_record("conflict-svc", version="1.0.0", timestamp="2026-01-03T00:00:00Z")
        winner2 = ConflictResolver.resolve(rec_a, rec_c)
        self.assertEqual(winner2.registration_timestamp, "2026-01-01T00:00:00Z")

    def test_lease_expiry_cleanup(self):
        hb = HeartbeatManager(ttl_seconds=1, check_interval=1)
        hb.grant_lease("test-lease-svc", ttl_seconds=1)
        
        self.assertTrue(hb.has_active_lease("test-lease-svc"))
        time.sleep(1.2)
        expired = hb.check_expired()
        
        self.assertIn("test-lease-svc", expired)
        self.assertFalse(hb.has_active_lease("test-lease-svc"))

    def test_certificate_revocation(self):
        ca = self.node1.ca
        cert = ca.issue_certificate("test-cert-svc", "aabbcc")
        
        self.assertTrue(ca.verify_certificate(cert))
        
        ca.revoke_certificate(cert.serial_number)
        
        self.assertFalse(ca.verify_certificate(cert))

    def test_evidence_chain_integrity(self):
        chain = SDKEvidenceChain()
        e1 = InvocationEvidence(
            invocation_id="inv-1", service_id="svc", operation="op",
            request_hash="req1", response_hash="res1", trust_method="CLASSICAL",
            duration_ms=10.0, status="SUCCESS"
        )
        e2 = InvocationEvidence(
            invocation_id="inv-2", service_id="svc", operation="op",
            request_hash="req2", response_hash="res2", trust_method="CLASSICAL",
            duration_ms=12.0, status="SUCCESS"
        )
        
        chain.record(e1)
        chain.record(e2)
        
        self.assertTrue(chain.verify_chain())
        
        # Tamper
        chain._evidence[0].response_hash = "TAMPERED"
        self.assertFalse(chain.verify_chain())


if __name__ == "__main__":
    unittest.main()
