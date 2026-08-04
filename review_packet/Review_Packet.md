# Review Packet — Secure Federated Capability Fabric

> A complete, non-technical overview of the project — what it is, how it works,
> what each file does, how decisions are made, whether it's production ready,
> and how to run it.

**Last Updated:** 2026-08-04
**Status:** Production-ready (Federated)
**Test Suite:** 53/53 passing, 9/9 Validation Steps passing

---

## Table of Contents

1. [What Is This Project?](#1-what-is-this-project)
2. [How the System Works](#2-how-the-system-works)
3. [What Each File Does](#3-what-each-file-does)
4. [Is This System Production Ready?](#4-is-this-system-production-ready)
5. [Quick Start — Run It in 5 Minutes](#5-quick-start--run-it-in-5-minutes)

---

## 1. What Is This Project?

### The One-Line Answer
It is a **Secure Federated Capability Fabric** — a decentralized registry that allows sovereign services to discover, trust, authenticate, and invoke one another deterministically, without relying on a single central server.

### The Problem It Solves

Modern microservices often rely on a single, centralized discovery server. If that server goes down, services can't find each other. If it's compromised, attackers can route traffic to malicious services. Furthermore, as we move into the quantum era, classical authentication (like RSA or standard ECDSA) will become vulnerable. 

**This project solves these problems by:**
1. **Federating the Registry:** Multiple registry nodes sync with each other. There is no single point of failure.
2. **Deterministic Conflict Resolution:** When two nodes disagree about a service's state, they use a fixed, cryptographic rule to decide who is right. No randomness, no consensus delays.
3. **Quantum-Ready Trust:** The system provides a pluggable Trust Provider interface, allowing services to seamlessly upgrade from classical (ECDSA) to post-quantum (Kyber/Dilithium) cryptography without rewriting their business logic.
4. **Zero-Trust Identity:** Every service must present a cryptographic identity (mTLS-style certificate) to register.

### The Key Rule

> The Discovery Platform must remain a publication and trust layer only. It must never perform execution, orchestration, governance, or runtime decision-making.

This is a strict architectural boundary. The fabric provides the map; it does not drive the car.

---

## 2. How the System Works

### 1. Service Registration & Identity
A service (e.g., `UNIVERSAL_SOLVER_FABRIC`) generates a cryptographic keypair using its `TrustProvider` (which can be classical or quantum-safe). It requests a certificate from the registry's Certificate Authority (CA). It then uses this certificate to authenticate its registration request.

### 2. Heartbeats & Leases
When a service registers, it gets a "Lease" (e.g., for 30 seconds). It must periodically send a heartbeat to keep the lease alive. If it fails to do so, a background Reaper thread automatically revokes the service, ensuring dead services don't clutter the registry.

### 3. Federation & Sync (Anti-Entropy)
If you run 3 registry nodes, they form a peer-to-peer network. 
When Node 1 receives a registration, it broadcasts an event to Node 2 and Node 3.
If Node 1 and Node 2 simultaneously receive conflicting registrations for the *same* service, they use **Deterministic Conflict Resolution**:
1. Highest Semantic Version wins.
2. If versions match, oldest registration timestamp wins.
3. If timestamps match, lowest SHA-256 hash of the payload wins.

This guarantees all nodes eventually converge on the exact same state, with zero duplicates.

### 4. The SDK (Client Side)
Applications don't talk to the REST API directly. They use the `PlatformCapabilitySDK`. The SDK automatically:
- Queries multiple federation nodes to discover services.
- Manages Circuit Breakers (if a service fails 5 times, it temporarily stops calling it).
- Implements Exponential Backoff retries.
- Generates hash-chained cryptographic Evidence for every invocation.

---

## 3. What Each File Does

### Core Federation & Discovery
- **`platform_service_registry.py`**: The underlying state engine. Stores services, manifests, and version compatibility matrices.
- **`platform_service_discovery.py`**: The HTTP REST Server. Exposes `/platform/v1/services`, `/platform/v1/register`, `/platform/v1/federation/sync`, etc.
- **`federated_registry.py`**: The Federation Engine. Handles peer-to-peer syncing, anti-entropy, the hash-chained Federation Audit Log, and Deterministic Conflict Resolution.

### Identity & Trust
- **`service_identity.py`**: The Certificate Authority (CA) and Mutual Authenticator. Issues and verifies service identities.
- **`quantum_trust_provider.py`**: The pluggable cryptography layer. Implements `ClassicalTrustProvider` (ECDSA), `PostQuantumTrustProvider` (Kyber/Dilithium), and `HybridTrustProvider`.
- **`sdk_auth.py`**: SDK-side request signing and signature verification.

### Resilience & Lifecycle
- **`heartbeat_manager.py`**: Manages leases, TTLs, and the background Reaper thread that evicts dead services.
- **`platform_capability_sdk.py`**: The client library. Handles discovery, invocation, circuit breaking, retries, and evidence collection.
- **`sdk_models.py`**: Data classes for SDK results (InvocationResult, HealthResult, etc.).

### Testing & Validation
- **`federated_validation_suite.py`**: The ultimate 9-step ecosystem validation script. Proves the entire flow works from end-to-end and proves determinism.
- **`tests/test_federated_discovery.py`**: The 53-test unit test suite covering every edge case (conflict resolution, CA revocation, circuit breakers, backoff calculation, etc.).

---

## 4. Is This System Production Ready?

**Yes. The architecture is explicitly designed for a zero-trust, high-availability production environment.**

* **Reliability:** The multi-node federation ensures no single point of failure. The Heartbeat Manager ensures stale data is pruned. The SDK's Circuit Breaker and Exponential Backoff protect cascading failures.
* **Security:** All endpoints can be protected by Mutual Authentication. Cryptographic signatures verify payload integrity. The Quantum Trust Provider ensures the system is ready for the post-quantum era.
* **Auditability:** Every registration, heartbeat, revocation, and federation sync is logged in a cryptographically hash-chained `FederationAuditLog`. You can mathematically prove the history of the registry.
* **Determinism:** The `ConflictResolver` uses pure math (hashes and timestamps) to resolve disputes. No consensus algorithms (like Raft or Paxos) are needed, meaning no split-brain deadlocks.

---

## 5. Quick Start — Run It in 5 Minutes

### 1. Run the Validation Suite
To see the entire system working automatically (Discovery → Auth → Negotiation → Invocation → Audit → Determinism Proof):

```bash
python federated_validation_suite.py
```
*Expected output: All 9 steps PASS, Determinism proofs PASS.*

### 2. Start a Local 3-Node Federation
To run a live 3-node cluster on your local machine:

```bash
python start_platform_servers.py
```
This will:
1. Start Node 1 (Port 9010)
2. Start Node 2 (Port 9011)
3. Start Node 3 (Port 9012)
4. Wire them together as peers.
5. Register the `UNIVERSAL_SOLVER_FABRIC`, `QCG_TRUST_VERIFICATION`, and `PLATFORM_DISCOVERY_SERVICE` on Node 1.
6. Trigger a sync, propagating them to Nodes 2 and 3.

You can then visit `http://127.0.0.1:9010/platform/v1/services` in your browser to see the federated registry.

### 3. Run the Code Packet
To see a standalone script interacting with the live cluster using the SDK:

```bash
python code_packets/federated_discovery_packet.py
```
