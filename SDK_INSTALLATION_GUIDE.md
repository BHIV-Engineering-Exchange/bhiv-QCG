# PlatformCapabilitySDK — External Participant Installation Guide

## Current Distribution Status

The SDK is now available as a pip-installable package (`tantra-platform-sdk`) distributed via the GitHub repository. **No PyPI publication yet** — install directly from GitHub.

---

## How to Access the SDK

### Option 1: `pip install` directly from GitHub (Recommended)

```bash
pip install git+https://github.com/PriteshPatra-BHIV/QCG_task1.git#subdirectory=sdk
```

This installs the `tantra-platform-sdk` package (v1.0.0) containing:
- `PlatformCapabilitySDK` (main entry point)
- `InvocationResult`, `NegotiationResult`, `ValidationResult`, `HealthResult`, `InvocationEvidence`
- `SDKAuthenticator`
- `TrustProvider`, `ClassicalTrustProvider`, `KeyPairResult`

### Option 2: Clone and install in editable mode

```bash
git clone https://github.com/PriteshPatra-BHIV/QCG_task1.git
cd QCG_task1/sdk
pip install -e .
```

### Option 3: Copy the minimal SDK files (temporary workaround)

If you cannot wait for the packaging, the SDK is self-contained in these 4 files from the repository root:

| File | Purpose |
|------|---------|
| `platform_capability_sdk.py` | Core SDK class — discovery, invocation, negotiation, evidence |
| `sdk_models.py` | Data models — `InvocationResult`, `NegotiationResult`, `InvocationEvidence`, etc. |
| `sdk_auth.py` | Authentication header construction and response verification |
| `quantum_trust_provider.py` | Trust provider interface (Classical / PostQuantum / Hybrid) |

Copy these 4 files into your project and import normally:

```python
from tantra_platform_sdk import PlatformCapabilitySDK

sdk = PlatformCapabilitySDK(
    discovery_urls=["https://bhiv-qcg.onrender.com"],
    service_id="INSIGHT-STACK-001"
)
```

**Dependencies** (add to your requirements.txt):
```
cryptography>=42.0.0
```

All other SDK dependencies are Python stdlib (`hashlib`, `json`, `urllib`, `uuid`, `threading`, `time`, `dataclasses`).

---

## SDK Usage for External Participants

### 1. Initialize
```python
from tantra_platform_sdk import PlatformCapabilitySDK

sdk = PlatformCapabilitySDK(
    discovery_urls=["https://bhiv-qcg.onrender.com"],
    service_id="YOUR-SERVICE-ID"
)
```

### 2. Discover Services
```python
services = sdk.discover_services()
# Returns list of registered PlatformServiceRecords
```

### 3. Negotiate Version
```python
result = sdk.negotiate_version("TANTRA-PSR-USF-001", "1.0.0")
# result.status: COMPATIBLE | DEPRECATED | UNSUPPORTED
```

### 4. Invoke Capability
```python
result = sdk.invoke_capability(
    service_id="TANTRA-PSR-USF-001",
    operation="discover_solvers",
    payload={"problem_type": "QUBO"}
)
# result.status: SUCCESS | FAILED | TIMEOUT | CIRCUIT_OPEN
# result.evidence: hash-chained invocation proof
```

### 5. Validate Manifest
```python
validation = sdk.validate_manifest("TANTRA-PSR-USF-001")
# validation.valid: True/False
```

---

## Environment Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `QCG_MOCK_SDK` | `0` | Set to `1` for local testing without live endpoints |

---

## Live Endpoint for Integration

The canonical live Platform Runtime is deployed at:

```
https://bhiv-qcg.onrender.com
```

Key endpoints:
| Method | Path | Purpose |
|--------|------|---------|
| GET | `/platform/v1/services` | List all registered services |
| GET | `/platform/v1/services/{id}` | Get service details |
| POST | `/platform/v1/negotiate` | Version negotiation |
| POST | `/platform/v1/register` | Service registration |
| POST | `/platform/v1/heartbeat` | Heartbeat/lease renewal |
| GET | `/platform/v1/health` | Platform health check |
| GET | `/platform/v1/readiness` | Readiness probe |
| POST | `/api/v1/execute` | Canonical capability invocation |

---

## Contact

For SDK issues or integration questions, reach out to **Kanishk** (Platform Runtime / Federation / SDK / Registry owner).
