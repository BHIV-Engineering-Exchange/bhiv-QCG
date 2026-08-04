# Federation Operations Guide

## Node Setup

Each federation node is a `FederatedRegistryNode` wrapping a `PlatformServiceRegistry`:

```python
from federated_registry import FederatedRegistryNode
from platform_service_registry import PlatformServiceRegistry, RegistrationEvidenceRecorder
from platform_service_discovery import PlatformDiscoveryServer

# Create node
registry = PlatformServiceRegistry(evidence_recorder=RegistrationEvidenceRecorder())
node = FederatedRegistryNode(node_id="NODE-1", registry=registry, port=9010)

# Start HTTP server
server = PlatformDiscoveryServer(
    host="127.0.0.1", port=9010,
    registry=registry, federation_node=node,
)
server.start()
```

## Peer Configuration

Nodes must know about each other to federate:

```python
node1.add_peer(node2)
node1.add_peer(node3)
node2.add_peer(node1)
node2.add_peer(node3)
# ... etc
```

## Conflict Resolution Semantics

When two nodes have different records for the same `platform_service_id`, the `ConflictResolver` applies deterministic rules:

1. **Higher version wins** (semver comparison)
2. **Earlier `registration_timestamp` wins** (tie-break)
3. **Lower SHA-256 hash of `platform_service_id`** (final deterministic tie-break)

Given identical inputs, the same record always wins. No randomness is involved.

## Federation Sync

### Anti-Entropy Sync

Pull-based full-state reconciliation:

```python
results = node.anti_entropy_sync()
# Syncs with all known peers
```

### Event-Driven Propagation

When a service is registered, the node broadcasts a `SERVICE_REGISTERED` event to all peers. Peers apply conflict resolution and adopt or reject the remote record.

### Replay Prevention

Every federation event carries a unique `nonce`. The `_seen_nonces` set ensures no event is processed twice.

## Audit Log Inspection

The federation audit log is an append-only, hash-chained ledger:

```python
events = node.get_audit_log()
is_valid = node.audit_log.verify_chain()
```

### HTTP API

```
GET /platform/v1/federation/status   → node topology + sync state
GET /platform/v1/federation/audit    → hash-chained event log
POST /platform/v1/federation/sync    → trigger anti-entropy sync
```

## No Duplicates Guarantee

The federation protocol ensures that no duplicate `platform_service_id` survives sync. When a remote registration arrives for an existing service, `ConflictResolver.resolve()` picks one winner deterministically. The loser is discarded.
