# TANTRA Platform Ecosystem — Final Handover

## Overview

The Platform Runtime Federation & Capability SDK Convergence task is complete. The runtime ecosystem is now a secure, federated, and replay-safe environment serving live BHIV participants.

The system natively supports canonical discovery, capability negotiation, evidence chain generation, and deterministic routing. It guarantees isolated, conflict-free state across a distributed mesh.

## Federation Topology

The TANTRA platform currently operates as a 3-node federated mesh:
- `FEDERATION-NODE-1` (Port 9010)
- `FEDERATION-NODE-2` (Port 9011)
- `FEDERATION-NODE-3` (Port 9012)

All nodes run `FederatedRegistryNode` which enforces anti-entropy synchronisation and deterministic conflict resolution using Lamport clocks/vector clocks. Any capability registered on one node will eventually sync securely to all peers.

## Platform Capability SDK

The `PlatformCapabilitySDK` is the mandatory canonical gateway for all ecosystem participants. 

### Features
1. **Zero-config Discovery**: Auto-connects to discovery endpoints and fetches service metadata.
2. **Version Negotiation**: Asserts compatibility boundaries defined by capabilities (e.g. `COMPATIBLE`, `DEPRECATED`, `UNSUPPORTED`).
3. **Resilience**: Implements transparent retry limits (default: 3) and circuit breaker patterns (threshold: 5 failures, timeout: 60s).
4. **Evidence Generation**: Automatically records cryptographic evidence of execution (hashes of requests/responses) mapped to `invocation_id` and service trust levels (e.g., `CLASSICAL`, `HYBRID`, `POST_QUANTUM`).

### Usage Example
```python
from platform_capability_sdk import PlatformCapabilitySDK

sdk = PlatformCapabilitySDK(
    discovery_urls=["http://127.0.0.1:9010"],
    service_id="MY-CAPABILITY"
)

# 1. Negotiate version
result = sdk.negotiate_version("TANTRA-PSR-USF-001", "1.0.0")

# 2. Invoke operation
response = sdk.invoke_capability(
    service_id="TANTRA-PSR-USF-001",
    operation="discover_solvers",
    payload={"problem_type": "QUBO"}
)
```

## Runtime Contracts

All participants MUST adhere to the canonical schema:

1. **PlatformServiceRecord**: Mandatory metadata required for registration (service_name, provider, capability_category, endpoints, etc).
2. **CapabilityManifest**: Immutable definition of supported operations, determinism/replay/evidence guarantees, and resource/trust requirements.
3. **Evidence Contracts**: All invocations must produce matching execution footprints to satisfy the `ReplayAuthority`.

## Registry Behavior & Known Limitations

- **Heartbeats**: Capabilities are granted a 30s lease by default and MUST emit a heartbeat, or the `HeartbeatManager` will expire them and transition their state to `DRAFT`.
- **Duplicate Protection**: The system guarantees exactly-once execution logic across the federation. Duplicates are deterministically rejected with `sequence_id` preservation.
- **Limitation - Network Timeouts**: The current SDK hard-times-out after 10 seconds. Services requiring massive optimization iterations (e.g. quantum compilation) should negotiate an ASYNCHRONOUS mode.

## Production Certification State

- **Architecture**: Validated (Federation, Evidence, Observability).
- **Execution Paths**: Tested against happy & Byzantine paths.
- **Failures**: Replay safety and isolation completely certified.
- **Status**: PRODUCTION READY.
