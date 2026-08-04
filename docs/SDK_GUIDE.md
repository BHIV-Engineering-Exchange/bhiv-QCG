# Platform Capability SDK — Developer Guide

## Quick Start

```python
from platform_capability_sdk import PlatformCapabilitySDK
from quantum_trust_provider import create_trust_provider

# Create SDK with classical trust (default)
sdk = PlatformCapabilitySDK(
    discovery_urls=["http://127.0.0.1:9010", "http://127.0.0.1:9011"],
    trust_provider=create_trust_provider("CLASSICAL"),
)

# Discover all services
services = sdk.discover_services()

# Invoke a capability
result = sdk.invoke_capability(
    service_id="TANTRA-PSR-USF-001",
    operation="discover_solvers",
    payload={"problem_type": "LP"},
)
print(result.status, result.duration_ms)
```

## Trust Provider Configuration

The SDK accepts any `TrustProvider` implementation. Three are built in:

| Level | Algorithm | Use Case |
|---|---|---|
| `CLASSICAL` | ECDSA P-256 | Current default, production-ready |
| `POST_QUANTUM` | CRYSTALS-Kyber + Dilithium (simulated) | Quantum-resistant |
| `HYBRID` | ECDSA + Dilithium dual-sign | Defense-in-depth |

### Migrating from Classical to Quantum Trust

Change one line — no application code changes required:

```python
# Before
sdk = PlatformCapabilitySDK(trust_provider=create_trust_provider("CLASSICAL"))

# After — quantum-ready
sdk = PlatformCapabilitySDK(trust_provider=create_trust_provider("POST_QUANTUM"))
```

## Error Handling and Retry Semantics

The SDK includes automatic retries with exponential backoff and jitter:

- **Max retries**: 3 (configurable via `QCG_SDK_MAX_RETRIES`)
- **Base delay**: 0.5s (configurable via `QCG_SDK_RETRY_BASE_DELAY`)
- **Max delay**: 30s (configurable via `QCG_SDK_RETRY_MAX_DELAY`)

### Circuit Breaker

Each service gets its own circuit breaker:

- **CLOSED**: Normal operation, failures are counted
- **OPEN**: After 5 failures, all calls rejected immediately
- **HALF_OPEN**: After 60s timeout, one probe call is allowed

```python
breaker_status = sdk._get_breaker("TANTRA-PSR-USF-001").get_status()
# {'state': 'CLOSED', 'failure_count': 0, ...}
```

## Evidence Collection

Every invocation produces a hash-chained `InvocationEvidence` record:

```python
# After invoking capabilities
all_evidence = sdk.evidence.get_all()
chain_valid = sdk.evidence.verify_chain()
```

## Version Negotiation

```python
result = sdk.negotiate_version("TANTRA-PSR-QCG-001", "1.0.0")
# result.status: COMPATIBLE | DEPRECATED | UNSUPPORTED
```

## Manifest Validation

```python
result = sdk.validate_manifest("TANTRA-PSR-USF-001")
# result.valid: True/False
# result.manifest_hash: SHA-256 of the manifest
```

## Federation Awareness

The SDK queries all discovery URLs and deduplicates by `platform_service_id`:

```python
sdk = PlatformCapabilitySDK(
    discovery_urls=[
        "http://127.0.0.1:9010",
        "http://127.0.0.1:9011",
        "http://127.0.0.1:9012",
    ]
)
# Discovers from all nodes, returns deduplicated list
services = sdk.discover_services()
```
