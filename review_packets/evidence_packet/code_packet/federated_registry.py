"""
federated_registry.py — Multi-Node Federated Registry Protocol

Provides multi-node registry federation with deterministic conflict resolution,
replay-safe event propagation, and federation audit logging.

No duplicate registrations survive federation. Every federation event is
hash-chained and replay-safe.

RESPONSIBILITY BOUNDARY
-----------------------
FederatedRegistryNode OWNS:
    - Peer management and topology
    - Federation event propagation
    - Anti-entropy synchronisation
    - Conflict resolution
    - Federation audit log

FederatedRegistryNode does NOT OWN:
    - Service registration logic       → PlatformServiceRegistry
    - Certificate issuance             → ServiceCertificateAuthority
    - Heartbeat management             → HeartbeatManager
    - Lifecycle transitions            → LifecycleManager
    - Execution / orchestration        → NEVER (architectural boundary)
"""

from __future__ import annotations

import hashlib
import json
import logging
import secrets
import threading
import time
import uuid
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Tuple

from platform_service_registry import (
    PlatformServiceRegistry,
    PlatformServiceRecord,
    CapabilityManifest,
    RegistrationEvidenceRecorder,
)
from service_identity import (
    ServiceCertificateAuthority,
    MutualAuthenticator,
    ServiceCertificate,
    AuthResult,
)
from heartbeat_manager import HeartbeatManager
from node_identity import NodeProof

import config

logger = logging.getLogger("tantra.platform.federation")


# ---------------------------------------------------------------------------
# Federation Event
# ---------------------------------------------------------------------------

@dataclass
class FederationEvent:
    """
    A single replay-safe federation event.

    Every event is hash-chained to its predecessor and carries a nonce
    to prevent replay attacks. The vector_clock enables causal ordering
    across federated peers.
    """
    event_id: str
    event_type: str               # SERVICE_REGISTERED | SERVICE_REMOVED | SERVICE_UPDATED | SYNC_REQUEST | SYNC_RESPONSE
    source_node_id: str
    target_node_id: str           # "" for broadcast
    payload: Dict[str, Any]
    vector_clock: Dict[str, int]  # node_id -> logical timestamp
    timestamp: str                # ISO-8601 UTC
    nonce: str                    # random nonce for replay prevention
    event_hash: str = ""
    previous_event_hash: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


# ---------------------------------------------------------------------------
# Federation Audit Log
# ---------------------------------------------------------------------------

class FederationAuditLog:
    """
    Append-only, hash-chained log of all federation events.

    Provides tamper-evident audit trail for federation operations.
    Thread-safe.
    """

    def __init__(self):
        self._events: List[FederationEvent] = []
        self._lock = threading.Lock()
        self._head_hash = hashlib.sha256(b"FEDERATION_GENESIS").hexdigest()
        self._sequence = 0

    def record(self, event: FederationEvent) -> FederationEvent:
        """
        Record a federation event with hash chaining.

        Mutates event.event_hash and event.previous_event_hash
        then appends to the log.
        """
        with self._lock:
            self._sequence += 1
            event.previous_event_hash = self._head_hash

            # Compute deterministic hash
            hash_seed = json.dumps({
                "event_id": event.event_id,
                "event_type": event.event_type,
                "source_node_id": event.source_node_id,
                "target_node_id": event.target_node_id,
                "payload": event.payload,
                "vector_clock": event.vector_clock,
                "nonce": event.nonce,
                "previous_hash": self._head_hash,
            }, sort_keys=True)
            event.event_hash = hashlib.sha256(hash_seed.encode()).hexdigest()

            self._events.append(event)
            self._head_hash = event.event_hash

            return event

    def verify_chain(self) -> bool:
        """Verify the integrity of the federation audit chain."""
        with self._lock:
            head = hashlib.sha256(b"FEDERATION_GENESIS").hexdigest()
            for event in self._events:
                if event.previous_event_hash != head:
                    return False
                hash_seed = json.dumps({
                    "event_id": event.event_id,
                    "event_type": event.event_type,
                    "source_node_id": event.source_node_id,
                    "target_node_id": event.target_node_id,
                    "payload": event.payload,
                    "vector_clock": event.vector_clock,
                    "nonce": event.nonce,
                    "previous_hash": head,
                }, sort_keys=True)
                expected = hashlib.sha256(hash_seed.encode()).hexdigest()
                if event.event_hash != expected:
                    return False
                head = event.event_hash
            return head == self._head_hash

    def get_events(self, since_sequence: int = 0) -> List[Dict[str, Any]]:
        """Get events starting from a given sequence index."""
        with self._lock:
            return [e.to_dict() for e in self._events[since_sequence:]]

    def get_all_events(self) -> List[Dict[str, Any]]:
        """Return all federation events."""
        with self._lock:
            return [e.to_dict() for e in self._events]

    @property
    def head_hash(self) -> str:
        with self._lock:
            return self._head_hash

    @property
    def sequence(self) -> int:
        with self._lock:
            return self._sequence

    def __len__(self) -> int:
        with self._lock:
            return len(self._events)


# ---------------------------------------------------------------------------
# Conflict Resolver
# ---------------------------------------------------------------------------

class ConflictResolver:
    """
    Deterministic conflict resolution for federated service registrations.

    Resolution order (highest priority first):
    1. Higher version wins (semver comparison)
    2. Earlier registration_timestamp wins (tie-break)
    3. Lower SHA-256(service_id) wins (final deterministic tie-break)

    Given identical inputs, the same record always wins. No randomness.
    """

    @staticmethod
    def _parse_version(v: str) -> Tuple[int, ...]:
        """Parse semver string into comparable tuple."""
        try:
            parts = v.strip().split(".")
            return tuple(int(p) for p in parts)
        except (ValueError, AttributeError):
            return (0, 0, 0)

    @classmethod
    def resolve(
        cls,
        local: PlatformServiceRecord,
        remote: PlatformServiceRecord,
    ) -> PlatformServiceRecord:
        """
        Resolve a conflict between local and remote registration records.

        Returns the winning record. The loser is discarded.
        """
        local_ver = cls._parse_version(local.version)
        remote_ver = cls._parse_version(remote.version)

        # 1. Higher version wins
        if remote_ver > local_ver:
            return remote
        if local_ver > remote_ver:
            return local

        # 2. Earlier registration_timestamp wins
        if remote.registration_timestamp < local.registration_timestamp:
            return remote
        if local.registration_timestamp < remote.registration_timestamp:
            return local

        # 3. Lower hash wins (deterministic tie-break)
        local_hash = hashlib.sha256(local.platform_service_id.encode()).hexdigest()
        remote_hash = hashlib.sha256(remote.platform_service_id.encode()).hexdigest()

        if remote_hash < local_hash:
            return remote
        return local  # default to local if perfectly equal


# ---------------------------------------------------------------------------
# Federated Registry Node
# ---------------------------------------------------------------------------

class FederatedRegistryNode:
    """
    A single node in the federated registry network.

    Wraps a PlatformServiceRegistry with federation capabilities:
    - Peer management (add/remove peers)
    - Authenticated service registration (mTLS pipeline)
    - Event broadcast to all peers
    - Anti-entropy synchronisation with conflict resolution
    - Deduplication: no duplicate service_ids survive sync

    This node is a publication and trust layer only. It never performs
    execution, orchestration, governance, or runtime decision-making.
    """

    def __init__(
        self,
        node_id: str,
        registry: PlatformServiceRegistry = None,
        ca: ServiceCertificateAuthority = None,
        heartbeat: HeartbeatManager = None,
        port: int = 9010,
    ):
        self.node_id = node_id
        self.port = port

        # Core components
        self.registry = registry or PlatformServiceRegistry()
        self.ca = ca or ServiceCertificateAuthority(f"{node_id}-CA")
        self.authenticator = MutualAuthenticator(self.ca)

        # Heartbeat manager with expiry callback
        self._evidence = self.registry.evidence
        self.heartbeat = heartbeat or HeartbeatManager(
            ttl_seconds=config.HEARTBEAT_TTL_SECONDS,
            check_interval=config.HEARTBEAT_CHECK_INTERVAL_SECONDS,
            on_expiry_callback=self._on_lease_expired,
            evidence_recorder=self._evidence,
        )

        # Federation state
        self._peers: Dict[str, FederatedRegistryNode] = {}
        self._vector_clock: Dict[str, int] = {node_id: 0}
        self._seen_nonces: set = set()  # replay prevention
        self._audit_log = FederationAuditLog()
        self._lock = threading.Lock()

        logger.info(f"FederatedRegistryNode '{node_id}' initialised on port {port}")

    # -- Peer management ----------------------------------------------------

    def add_peer(self, peer: FederatedRegistryNode):
        """Register a peer node for federation."""
        with self._lock:
            self._peers[peer.node_id] = peer
            if peer.node_id not in self._vector_clock:
                self._vector_clock[peer.node_id] = 0
        logger.info(f"[{self.node_id}] Added peer: {peer.node_id}")

    def remove_peer(self, peer_id: str):
        """Remove a peer from federation."""
        with self._lock:
            self._peers.pop(peer_id, None)
        logger.info(f"[{self.node_id}] Removed peer: {peer_id}")

    @property
    def peer_ids(self) -> List[str]:
        with self._lock:
            return list(self._peers.keys())

    # -- Authenticated registration -----------------------------------------

    def register_service_authenticated(
        self,
        record: PlatformServiceRecord,
        manifest: CapabilityManifest = None,
        proof: NodeProof = None,
        certificate: ServiceCertificate = None,
    ) -> Dict[str, Any]:
        """
        Register a service with mutual authentication.

        Pipeline:
        1. Authenticate via MutualAuthenticator
        2. Register in local PlatformServiceRegistry
        3. Grant heartbeat lease
        4. Broadcast federation event to all peers
        """
        # If proof and certificate are provided, authenticate
        if proof and certificate:
            auth_result = self.authenticator.authenticate(
                service_id=record.platform_service_id,
                proof=proof,
                certificate=certificate,
                registration_payload=record.to_dict(),
            )
            if not auth_result.authenticated:
                return {
                    "status": "AUTH_FAILED",
                    "service_id": record.platform_service_id,
                    "reason": auth_result.reason,
                }
        else:
            # Internal registration (e.g., from federation sync) — trusted
            auth_result = AuthResult(
                authenticated=True,
                service_id=record.platform_service_id,
                reason="Internal registration (no proof required)",
            )

        # Register in local registry
        result = self.registry.register_service(record, manifest)

        # Grant lease
        if result.get("status") in ("REGISTERED", "ALREADY_REGISTERED"):
            self.heartbeat.grant_lease(record.platform_service_id)

        # Broadcast to peers
        if result.get("status") == "REGISTERED":
            self._broadcast_registration(record, manifest)

        result["authentication"] = auth_result.to_dict()
        return result

    def revoke_service(self, service_id: str, reason: str = "Manual revocation") -> Dict[str, Any]:
        """
        Revoke a service: remove from registry, revoke lease, broadcast removal.
        """
        # Remove from registry
        remove_result = self.registry.remove_service(service_id, reason)

        # Revoke lease
        self.heartbeat.revoke_lease(service_id)

        # Broadcast removal
        self._broadcast_removal(service_id, reason)

        return remove_result

    # -- Federation sync ----------------------------------------------------

    def sync_with_peer(self, peer_node_id: str) -> Dict[str, Any]:
        """
        Pull services from a peer and merge with local registry.

        Uses deterministic conflict resolution for any conflicts.
        No duplicate service_ids survive the merge.
        """
        with self._lock:
            peer = self._peers.get(peer_node_id)
            if not peer:
                return {"status": "PEER_NOT_FOUND", "peer_id": peer_node_id}

        peer_services = peer.registry.list_services()
        merged = 0
        conflicts_resolved = 0
        skipped = 0

        for remote_dict in peer_services:
            sid = remote_dict["platform_service_id"]
            local_dict = self.registry.get_service(sid)

            if local_dict is None:
                # Service not in local registry — adopt it
                remote_record = self._dict_to_record(remote_dict)
                remote_manifest_dict = peer.registry.get_manifest(sid)
                remote_manifest = None
                if remote_manifest_dict:
                    remote_manifest = self._dict_to_manifest(remote_manifest_dict)
                self.registry.merge_remote_service(remote_record, remote_manifest, peer_node_id)
                self.heartbeat.grant_lease(sid)
                merged += 1
            else:
                # Conflict: same service_id exists locally
                local_record = self._dict_to_record(local_dict)
                remote_record = self._dict_to_record(remote_dict)
                winner = ConflictResolver.resolve(local_record, remote_record)

                if winner.registration_timestamp == remote_record.registration_timestamp:
                    # Remote wins — overwrite local
                    remote_manifest_dict = peer.registry.get_manifest(sid)
                    remote_manifest = None
                    if remote_manifest_dict:
                        remote_manifest = self._dict_to_manifest(remote_manifest_dict)
                    self.registry.merge_remote_service(remote_record, remote_manifest, peer_node_id)
                    conflicts_resolved += 1
                else:
                    skipped += 1

        # Record sync event
        self._increment_clock()
        sync_event = self._create_event(
            "SYNC_COMPLETED",
            peer_node_id,
            {
                "merged": merged,
                "conflicts_resolved": conflicts_resolved,
                "skipped": skipped,
                "peer_service_count": len(peer_services),
                "local_service_count": len(self.registry.list_services()),
            },
        )
        self._audit_log.record(sync_event)

        logger.info(
            f"[{self.node_id}] Synced with {peer_node_id}: "
            f"merged={merged}, conflicts={conflicts_resolved}, skipped={skipped}"
        )

        return {
            "status": "SYNC_COMPLETED",
            "peer_id": peer_node_id,
            "merged": merged,
            "conflicts_resolved": conflicts_resolved,
            "skipped": skipped,
        }

    def anti_entropy_sync(self) -> List[Dict[str, Any]]:
        """
        Perform anti-entropy sync with all known peers.

        Returns sync results for each peer.
        """
        results = []
        with self._lock:
            peer_ids = list(self._peers.keys())

        for pid in peer_ids:
            result = self.sync_with_peer(pid)
            results.append(result)

        return results

    # -- Queries ------------------------------------------------------------

    def get_federation_status(self) -> Dict[str, Any]:
        """Return the current federation topology and sync state."""
        with self._lock:
            return {
                "node_id": self.node_id,
                "port": self.port,
                "peers": list(self._peers.keys()),
                "vector_clock": dict(self._vector_clock),
                "service_count": len(self.registry.list_services()),
                "active_leases": len(self.heartbeat.get_active_leases()),
                "audit_log_length": len(self._audit_log),
                "audit_chain_valid": self._audit_log.verify_chain(),
            }

    def get_audit_log(self) -> List[Dict[str, Any]]:
        """Return the federation audit log."""
        return self._audit_log.get_all_events()

    @property
    def audit_log(self) -> FederationAuditLog:
        return self._audit_log

    # -- Internal helpers ---------------------------------------------------

    def _on_lease_expired(self, service_id: str):
        """Callback when a service lease expires."""
        logger.info(f"[{self.node_id}] Lease expired for {service_id}, removing from registry")
        self.registry.remove_service(service_id, "Lease expired")
        self._broadcast_removal(service_id, "Lease expired")

    def _broadcast_registration(self, record: PlatformServiceRecord, manifest: CapabilityManifest = None):
        """Broadcast a new registration to all peers."""
        self._increment_clock()
        event = self._create_event(
            "SERVICE_REGISTERED",
            "",  # broadcast
            {
                "record": record.to_dict(),
                "manifest": manifest.to_dict() if manifest else None,
            },
        )
        self._audit_log.record(event)
        self._propagate_to_peers(event)

    def _broadcast_removal(self, service_id: str, reason: str):
        """Broadcast a service removal to all peers."""
        self._increment_clock()
        event = self._create_event(
            "SERVICE_REMOVED",
            "",
            {"service_id": service_id, "reason": reason},
        )
        self._audit_log.record(event)
        self._propagate_to_peers(event)

    def _propagate_to_peers(self, event: FederationEvent):
        """Push an event to all peers for processing."""
        with self._lock:
            peers = list(self._peers.values())

        for peer in peers:
            try:
                peer.receive_federation_event(event)
            except Exception as e:
                logger.error(f"[{self.node_id}] Failed to propagate to {peer.node_id}: {e}")

    def receive_federation_event(self, event: FederationEvent):
        """
        Process a federation event received from a peer.

        Replay-safe: rejects events with previously seen nonces.
        """
        with self._lock:
            # Replay prevention
            if event.nonce in self._seen_nonces:
                logger.debug(f"[{self.node_id}] Ignoring replayed event: {event.event_id}")
                return
            self._seen_nonces.add(event.nonce)

            # Update vector clock
            for node_id, ts in event.vector_clock.items():
                self._vector_clock[node_id] = max(
                    self._vector_clock.get(node_id, 0), ts
                )

        # Process by type
        if event.event_type == "SERVICE_REGISTERED":
            self._handle_remote_registration(event)
        elif event.event_type == "SERVICE_REMOVED":
            self._handle_remote_removal(event)

        # Record in local audit log
        self._audit_log.record(event)

    def _handle_remote_registration(self, event: FederationEvent):
        """Apply a remote registration event locally."""
        payload = event.payload
        record_dict = payload.get("record", {})
        manifest_dict = payload.get("manifest")

        if not record_dict:
            return

        sid = record_dict.get("platform_service_id")
        local = self.registry.get_service(sid)

        remote_record = self._dict_to_record(record_dict)

        if local is None:
            remote_manifest = None
            if manifest_dict:
                remote_manifest = self._dict_to_manifest(manifest_dict)
            self.registry.merge_remote_service(remote_record, remote_manifest, event.source_node_id)
            self.heartbeat.grant_lease(sid)
        else:
            # Conflict resolution
            local_record = self._dict_to_record(local)
            winner = ConflictResolver.resolve(local_record, remote_record)
            if winner.registration_timestamp == remote_record.registration_timestamp:
                remote_manifest = None
                if manifest_dict:
                    remote_manifest = self._dict_to_manifest(manifest_dict)
                self.registry.merge_remote_service(remote_record, remote_manifest, event.source_node_id)

    def _handle_remote_removal(self, event: FederationEvent):
        """Apply a remote removal event locally."""
        sid = event.payload.get("service_id")
        reason = event.payload.get("reason", "Removed by federated peer")
        if sid:
            self.registry.remove_service(sid, reason)
            self.heartbeat.revoke_lease(sid)

    def _increment_clock(self):
        """Increment this node's logical clock."""
        with self._lock:
            self._vector_clock[self.node_id] = self._vector_clock.get(self.node_id, 0) + 1

    def _create_event(
        self,
        event_type: str,
        target_node_id: str,
        payload: Dict[str, Any],
    ) -> FederationEvent:
        """Create a new federation event with current vector clock."""
        with self._lock:
            clock = dict(self._vector_clock)

        return FederationEvent(
            event_id=str(uuid.uuid4()),
            event_type=event_type,
            source_node_id=self.node_id,
            target_node_id=target_node_id,
            payload=payload,
            vector_clock=clock,
            timestamp=datetime.now(timezone.utc).isoformat(),
            nonce=secrets.token_hex(16),
        )

    @staticmethod
    def _dict_to_record(d: dict) -> PlatformServiceRecord:
        """Convert a dict back to a PlatformServiceRecord."""
        return PlatformServiceRecord(
            platform_service_id=d["platform_service_id"],
            capability_id=d.get("capability_id", ""),
            service_name=d.get("service_name", ""),
            version=d.get("version", "0.0.0"),
            provider=d.get("provider", ""),
            owner=d.get("owner", {}),
            runtime_type=d.get("runtime_type", "PROCESS"),
            service_classification=d.get("service_classification", "PLATFORM_SERVICE"),
            capability_category=d.get("capability_category", "VERIFICATION"),
            status=d.get("status", "ACTIVE"),
            registration_timestamp=d.get("registration_timestamp", ""),
            description=d.get("description", ""),
            tags=d.get("tags", []),
            endpoints=d.get("endpoints", {}),
            dependencies=d.get("dependencies", []),
        )

    @staticmethod
    def _dict_to_manifest(d: dict) -> CapabilityManifest:
        """Convert a dict back to a CapabilityManifest."""
        from platform_service_registry import OperationContract
        ops = []
        for op_dict in d.get("supported_operations", []):
            ops.append(OperationContract(
                operation_name=op_dict["operation_name"],
                description=op_dict.get("description", ""),
                input_contract=op_dict.get("input_contract", {}),
                output_contract=op_dict.get("output_contract", {}),
                execution_modes=op_dict.get("execution_modes", []),
                idempotent=op_dict.get("idempotent", False),
            ))
        return CapabilityManifest(
            manifest_id=d.get("manifest_id", ""),
            service_name=d.get("service_name", ""),
            version=d.get("version", ""),
            supported_operations=ops,
            execution_modes=d.get("execution_modes", []),
            determinism_guarantees=d.get("determinism_guarantees", {}),
            replay_guarantees=d.get("replay_guarantees", {}),
            trust_requirements=d.get("trust_requirements", {}),
            evidence_guarantees=d.get("evidence_guarantees", {}),
            runtime_dependencies=d.get("runtime_dependencies", []),
            version_compatibility=d.get("version_compatibility", {}),
            security_requirements=d.get("security_requirements", {}),
            resource_requirements=d.get("resource_requirements", {}),
        )
