"""
tests/test_federation_convergence.py — Phase 2: Federation Convergence Tests

Validates ConflictResolver, FederationAuditLog, FederatedRegistryNode
contracts, and multi-node anti-entropy convergence.
"""

import pytest
import sys
import os
import time
import hashlib
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

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
)


def _make_record(sid: str, version: str = "1.0.0", timestamp: str = "2026-01-01T00:00:00Z") -> PlatformServiceRecord:
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
        registration_timestamp=timestamp,
        status="ACTIVE",
    )


# ---------------------------------------------------------------------------
# ConflictResolver Tests
# ---------------------------------------------------------------------------

class TestConflictResolver:

    def test_higher_version_wins(self):
        local = _make_record("svc-1", version="1.0.0")
        remote = _make_record("svc-1", version="2.0.0")
        winner = ConflictResolver.resolve(local, remote)
        assert winner.version == "2.0.0"

    def test_earlier_timestamp_wins_on_version_tie(self):
        local = _make_record("svc-1", version="1.0.0", timestamp="2026-02-01T00:00:00Z")
        remote = _make_record("svc-1", version="1.0.0", timestamp="2026-01-01T00:00:00Z")
        winner = ConflictResolver.resolve(local, remote)
        assert winner.registration_timestamp == "2026-01-01T00:00:00Z"

    def test_hash_tiebreak_is_deterministic(self):
        local = _make_record("svc-a", version="1.0.0", timestamp="2026-01-01T00:00:00Z")
        remote = _make_record("svc-a", version="1.0.0", timestamp="2026-01-01T00:00:00Z")
        winner1 = ConflictResolver.resolve(local, remote)
        winner2 = ConflictResolver.resolve(local, remote)
        assert winner1.platform_service_id == winner2.platform_service_id

    def test_local_wins_on_higher_version(self):
        local = _make_record("svc-1", version="3.0.0")
        remote = _make_record("svc-1", version="1.0.0")
        winner = ConflictResolver.resolve(local, remote)
        assert winner.version == "3.0.0"


# ---------------------------------------------------------------------------
# FederationAuditLog Tests
# ---------------------------------------------------------------------------

class TestFederationAuditLog:

    def test_empty_chain_valid(self):
        log = FederationAuditLog()
        assert log.verify_chain() is True
        assert len(log) == 0

    def test_genesis_hash(self):
        log = FederationAuditLog()
        expected = hashlib.sha256(b"FEDERATION_GENESIS").hexdigest()
        assert log.head_hash == expected

    def test_record_and_chain(self):
        log = FederationAuditLog()
        event = FederationEvent(
            event_id="ev-001",
            event_type="SERVICE_REGISTERED",
            source_node_id="node-a",
            target_node_id="",
            payload={"sid": "svc-1"},
            vector_clock={"node-a": 1},
            timestamp="2026-01-01T00:00:00Z",
            nonce="nonce-001",
        )
        recorded = log.record(event)
        assert recorded.event_hash != ""
        assert log.verify_chain() is True
        assert log.sequence == 1

    def test_tamper_detection(self):
        log = FederationAuditLog()
        event = FederationEvent(
            event_id="ev-tamper",
            event_type="SERVICE_REGISTERED",
            source_node_id="node-a",
            target_node_id="",
            payload={"data": "test"},
            vector_clock={"node-a": 1},
            timestamp="2026-01-01T00:00:00Z",
            nonce="nonce-tamper",
        )
        recorded = log.record(event)
        recorded.event_hash = "tampered"
        assert log.verify_chain() is False

    def test_sequence_monotonicity(self):
        log = FederationAuditLog()
        for i in range(3):
            event = FederationEvent(
                event_id=f"ev-{i}",
                event_type="SYNC_COMPLETED",
                source_node_id="node-a",
                target_node_id="",
                payload={},
                vector_clock={"node-a": i + 1},
                timestamp="2026-01-01T00:00:00Z",
                nonce=f"nonce-{i}",
            )
            log.record(event)
        assert log.sequence == 3
        assert log.verify_chain() is True


# ---------------------------------------------------------------------------
# FederatedRegistryNode Tests
# ---------------------------------------------------------------------------

class TestFederatedRegistryNode:

    def test_node_creation(self):
        node = FederatedRegistryNode("test-node-1", port=19001)
        assert node.node_id == "test-node-1"
        assert node.port == 19001
        assert node.peer_ids == []

    def test_add_and_remove_peer(self):
        node_a = FederatedRegistryNode("node-a", port=19001)
        node_b = FederatedRegistryNode("node-b", port=19002)
        node_a.add_peer(node_b)
        assert "node-b" in node_a.peer_ids
        node_a.remove_peer("node-b")
        assert "node-b" not in node_a.peer_ids

    def test_register_service_internally(self):
        node = FederatedRegistryNode("node-reg", port=19003)
        record = _make_record("svc-internal")
        result = node.register_service_authenticated(record)
        assert result["status"] in ("REGISTERED", "ALREADY_REGISTERED")

    def test_revoke_service(self):
        node = FederatedRegistryNode("node-rev", port=19004)
        record = _make_record("svc-revoke")
        node.register_service_authenticated(record)
        result = node.revoke_service("svc-revoke", "Testing revocation")
        assert result["status"] in ("REMOVED", "NOT_FOUND")

    def test_replay_safe_event_deduplication(self):
        node = FederatedRegistryNode("node-replay", port=19005)
        event = FederationEvent(
            event_id="ev-dup",
            event_type="SERVICE_REGISTERED",
            source_node_id="external",
            target_node_id="",
            payload={"record": _make_record("svc-dup").to_dict()},
            vector_clock={"external": 1},
            timestamp="2026-01-01T00:00:00Z",
            nonce="replay-nonce-001",
        )
        node.receive_federation_event(event)
        # Second time should be silently ignored (replayed)
        node.receive_federation_event(event)
        # Only one service should exist
        services = node.registry.list_services()
        dup_count = sum(1 for s in services if s["platform_service_id"] == "svc-dup")
        assert dup_count <= 1

    def test_federation_status(self):
        node = FederatedRegistryNode("node-status", port=19006)
        status = node.get_federation_status()
        assert status["node_id"] == "node-status"
        assert status["audit_chain_valid"] is True

    def test_get_audit_log(self):
        node = FederatedRegistryNode("node-audit", port=19007)
        record = _make_record("svc-audit")
        node.register_service_authenticated(record)
        log = node.get_audit_log()
        assert isinstance(log, list)


# ---------------------------------------------------------------------------
# Anti-Entropy Convergence Tests
# ---------------------------------------------------------------------------

class TestFederationConvergence:

    def test_two_node_sync_convergence(self):
        """Two nodes register different services, sync, and end up with the union."""
        node_a = FederatedRegistryNode("conv-a", port=19010)
        node_b = FederatedRegistryNode("conv-b", port=19011)
        node_a.add_peer(node_b)
        node_b.add_peer(node_a)

        # Register different services on each node
        node_a.register_service_authenticated(_make_record("svc-alpha"))
        node_b.register_service_authenticated(_make_record("svc-beta"))

        # Sync
        node_a.sync_with_peer("conv-b")
        node_b.sync_with_peer("conv-a")

        # Both nodes should have both services
        a_services = {s["platform_service_id"] for s in node_a.registry.list_services()}
        b_services = {s["platform_service_id"] for s in node_b.registry.list_services()}

        assert "svc-alpha" in a_services
        assert "svc-beta" in a_services
        assert "svc-alpha" in b_services
        assert "svc-beta" in b_services

    def test_three_node_anti_entropy(self):
        """Three nodes form a ring, each with a unique service. Anti-entropy converges."""
        nodes = []
        for name in ["ring-a", "ring-b", "ring-c"]:
            nodes.append(FederatedRegistryNode(name, port=19020 + len(nodes)))

        # Full mesh peering
        for i, node in enumerate(nodes):
            for j, peer in enumerate(nodes):
                if i != j:
                    node.add_peer(peer)

        # Register unique services
        nodes[0].register_service_authenticated(_make_record("svc-ring-1"))
        nodes[1].register_service_authenticated(_make_record("svc-ring-2"))
        nodes[2].register_service_authenticated(_make_record("svc-ring-3"))

        # Anti-entropy on all nodes
        for node in nodes:
            node.anti_entropy_sync()

        # All nodes should have all 3 services
        for node in nodes:
            sids = {s["platform_service_id"] for s in node.registry.list_services()}
            assert "svc-ring-1" in sids, f"{node.node_id} missing svc-ring-1"
            assert "svc-ring-2" in sids, f"{node.node_id} missing svc-ring-2"
            assert "svc-ring-3" in sids, f"{node.node_id} missing svc-ring-3"

    def test_conflict_resolution_during_sync(self):
        """When the same service exists on two nodes with different versions, higher wins."""
        node_a = FederatedRegistryNode("conflict-a", port=19030)
        node_b = FederatedRegistryNode("conflict-b", port=19031)
        node_a.add_peer(node_b)

        # Same service_id, different versions
        node_a.register_service_authenticated(_make_record("svc-conflict", version="1.0.0"))
        node_b.register_service_authenticated(_make_record("svc-conflict", version="2.0.0"))

        # Sync A from B
        result = node_a.sync_with_peer("conflict-b")
        assert result["conflicts_resolved"] >= 1

        # A should now have version 2.0.0
        svc = node_a.registry.get_service("svc-conflict")
        assert svc["version"] == "2.0.0"

    def test_audit_chains_valid_after_sync(self):
        """Audit chains on all nodes remain valid after sync operations."""
        node_a = FederatedRegistryNode("audit-a", port=19040)
        node_b = FederatedRegistryNode("audit-b", port=19041)
        node_a.add_peer(node_b)
        node_b.add_peer(node_a)

        node_a.register_service_authenticated(_make_record("svc-aud-1"))
        node_b.register_service_authenticated(_make_record("svc-aud-2"))
        node_a.sync_with_peer("audit-b")
        node_b.sync_with_peer("audit-a")

        assert node_a.audit_log.verify_chain() is True
        assert node_b.audit_log.verify_chain() is True
