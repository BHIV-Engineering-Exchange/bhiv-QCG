# Insight Stack Live Runtime - Team Endpoint Reference

**Project:** Insight Stack Live Runtime Convergence  
**Owner:** Insight Stack  
**Status:** Live / Verified  
**Last Verified:** 2026-08-10  
**Scope:** InsightFlow, InsightBridge, InsightCore

---

## 1. Purpose

This is a standalone team-sharing reference for the current live Insight Stack runtime endpoints.

**Insight Runtime:**  
`https://insight-constitutional-runtime.onrender.com`

**BHIV Platform / TANTRA Registry:**  
`https://bhiv-qcg.onrender.com`

Insight owns the Insight-side runtime participation. The BHIV Platform owns platform registration, discovery, capability registry, and related platform services.

---

# 2. Live Service Identities

## InsightFlow

| Field | Value |
|---|---|
| Service ID | `insightflow.runtime.intelligence.v1` |
| Version | `1.0.2` |
| Status | `ACTIVE` |
| Classification | `DOMAIN_SERVICE` |
| Category | `INTELLIGENCE` |
| Runtime Type | `Constitutional Runtime Participant` |

**Execution**

`POST https://insight-constitutional-runtime.onrender.com/api/v1/execute`

**Health**

`GET https://insight-constitutional-runtime.onrender.com/api/v1/health/insightflow.runtime.intelligence.v1`

---

## InsightBridge

| Field | Value |
|---|---|
| Service ID | `insightbridge.runtime.intelligence.v1` |
| Version | `1.0.2` |
| Status | `ACTIVE` |
| Classification | `DOMAIN_SERVICE` |
| Category | `INTELLIGENCE` |
| Runtime Type | `Constitutional Runtime Participant` |

**Execution**

`POST https://insight-constitutional-runtime.onrender.com/api/v1/execute`

**Health**

`GET https://insight-constitutional-runtime.onrender.com/api/v1/health/insightbridge.runtime.intelligence.v1`

---

## InsightCore

| Field | Value |
|---|---|
| Service ID | `insightcore.runtime.intelligence.v1` |
| Version | `1.0.2` |
| Status | `ACTIVE` |
| Classification | `DOMAIN_SERVICE` |
| Category | `INTELLIGENCE` |
| Runtime Type | `Constitutional Runtime Participant` |

**Execution**

`POST https://insight-constitutional-runtime.onrender.com/api/v1/execute`

**Health**

`GET https://insight-constitutional-runtime.onrender.com/api/v1/health/insightcore.runtime.intelligence.v1`

---

# 3. Canonical Execution Endpoint

All three Insight participants use the same deployed execution endpoint:

```text
POST https://insight-constitutional-runtime.onrender.com/api/v1/execute
```

The participant is selected through `service_id`.

### InsightFlow request

```json
{
  "service_id": "insightflow.runtime.intelligence.v1",
  "operation": "execute",
  "version": "1.0.2",
  "invocation_id": "UUID",
  "payload": {
    "source": "team-integration-check"
  }
}
```

Replace `service_id` with:

```text
insightbridge.runtime.intelligence.v1
```

or:

```text
insightcore.runtime.intelligence.v1
```

for the other participants.

### Verified successful response fields

```text
invocation_id
service_id
operation
status
response
duration_ms
trust_method
evidence
error
retry_count
timestamp
```

Expected successful state:

```text
status = SUCCESS
error  = null
version = 1.0.2
```

The evidence object contains the invocation ID, service ID, request hash, response hash, trust method, status, duration and timestamp.

---

# 4. Participant Health Endpoints

### InsightFlow

```text
GET https://insight-constitutional-runtime.onrender.com/api/v1/health/insightflow.runtime.intelligence.v1
```

### InsightBridge

```text
GET https://insight-constitutional-runtime.onrender.com/api/v1/health/insightbridge.runtime.intelligence.v1
```

### InsightCore

```text
GET https://insight-constitutional-runtime.onrender.com/api/v1/health/insightcore.runtime.intelligence.v1
```

Verified response pattern:

```json
{
  "service_id": "insightflow.runtime.intelligence.v1",
  "status": "UP",
  "version": "1.0.2",
  "state": "ACTIVE",
  "timestamp": "..."
}
```

---

# 5. BHIV Platform Registry Endpoints

These endpoints belong to the BHIV Platform side.

## Platform Service Registration

```text
POST https://bhiv-qcg.onrender.com/registry/platform/v1/register
```

Current registered Insight services:

```text
insightflow.runtime.intelligence.v1
insightbridge.runtime.intelligence.v1
insightcore.runtime.intelligence.v1
```

Verified behavior:

```text
HTTP 200
```

If the same service/version is already present, the platform can return:

```text
ALREADY_REGISTERED
```

with registration evidence.

---

# 6. Capability Registry

## Capability Registration

```text
POST https://bhiv-qcg.onrender.com/registry/capabilities/register
```

Current capabilities:

```text
insightflow.runtime.intelligence.v1
insightbridge.runtime.intelligence.v1
insightcore.runtime.intelligence.v1
```

Verified response pattern:

```json
{
  "status": "REGISTERED",
  "capability_id": "insightflow.runtime.intelligence.v1"
}
```

---

# 7. Individual Registry Lookup

## InsightFlow

```text
GET https://bhiv-qcg.onrender.com/registry/platform/v1/services/insightflow.runtime.intelligence.v1
```

## InsightBridge

```text
GET https://bhiv-qcg.onrender.com/registry/platform/v1/services/insightbridge.runtime.intelligence.v1
```

## InsightCore

```text
GET https://bhiv-qcg.onrender.com/registry/platform/v1/services/insightcore.runtime.intelligence.v1
```

The verified InsightFlow lookup returned the service identity, version, status and the execution/health endpoints.

---

# 8. Discovery

Discovery is performed through the canonical BHIV Platform Discovery / Platform Capability SDK path.

The verified SDK discovery result contained:

```text
InsightFlow     1.0.2    ACTIVE
InsightBridge   1.0.2    ACTIVE
InsightCore     1.0.2    ACTIVE
```

**Important:** Insight does not maintain a parallel registry or custom discovery system.

The exact direct REST discovery route should be taken from the current BHIV Platform API/OpenAPI contract supplied by the Platform Runtime owner. This reference intentionally does not invent an unverified discovery URL.

---

# 9. Version Negotiation

Current Insight participant version:

```text
1.0.2
```

Version negotiation is performed through the canonical Platform SDK/integration.

Verified result:

```text
status = COMPATIBLE
requested_version = 1.0.2
negotiated_version = 1.0.2
```

This was verified for:

```text
InsightFlow
InsightBridge
InsightCore
```

Teams should use the canonical Platform SDK negotiation mechanism rather than creating separate compatibility logic.

---

# 10. Verified Integration Flow

```text
Registration
     |
     v
Platform Registry
     |
     v
Discovery
     |
     v
Version Negotiation
     |
     v
Capability Invocation
     |
     v
Execution Evidence
     |
     v
Replay Validation
     |
     v
Health / Telemetry
```

The live proof currently covers:

1. Registration
2. Discovery
3. Version negotiation
4. Invocation
5. Execution evidence
6. Replay validation
7. Health visibility
8. Telemetry visibility
9. Failure-path behavior
10. End-to-end integration summary

---

# 11. Participant Dependencies

## InsightFlow

```text
PlatformCapabilitySDK
PlatformDiscovery
PlatformRegistry
RuntimeCore
```

## InsightBridge

```text
PlatformCapabilitySDK
PlatformDiscovery
RuntimeCore
QuantumCommunicationGateway
```

## InsightCore

```text
PlatformCapabilitySDK
PlatformDiscovery
RuntimeCore
ReplayRegistry
```

These are integration dependencies, not ownership claims.

---

# 12. Authority Boundaries

### Insight Stack owns

```text
Insight participant execution
Insight runtime identity
Insight-side evidence generation
Insight integration adapters
Insight health/telemetry participation
Replay participation
```

### Insight Stack does not own

```text
BHIV Platform governance
Platform Registry implementation
Platform Discovery implementation
Platform Capability SDK implementation
Quantum execution
Core governance
```

---

# 13. Quick Health Commands

### InsightFlow

```powershell
Invoke-RestMethod `
  -Uri "https://insight-constitutional-runtime.onrender.com/api/v1/health/insightflow.runtime.intelligence.v1" `
  -Method Get
```

### InsightBridge

```powershell
Invoke-RestMethod `
  -Uri "https://insight-constitutional-runtime.onrender.com/api/v1/health/insightbridge.runtime.intelligence.v1" `
  -Method Get
```

### InsightCore

```powershell
Invoke-RestMethod `
  -Uri "https://insight-constitutional-runtime.onrender.com/api/v1/health/insightcore.runtime.intelligence.v1" `
  -Method Get
```

Expected:

```text
status  = UP
state   = ACTIVE
version = 1.0.2
```

---

# 14. Quick Execution Check

Example InsightFlow invocation:

```powershell
$body = @{
    service_id = "insightflow.runtime.intelligence.v1"
    operation = "execute"
    version = "1.0.2"
    invocation_id = [guid]::NewGuid().ToString()
    payload = @{
        source = "team-integration-check"
    }
} | ConvertTo-Json -Depth 10

Invoke-RestMethod `
  -Uri "https://insight-constitutional-runtime.onrender.com/api/v1/execute" `
  -Method Post `
  -ContentType "application/json" `
  -Body $body
```

Expected:

```text
status     = SUCCESS
service_id = insightflow.runtime.intelligence.v1
version    = 1.0.2
error      = null
```

---

# 15. Team-Specific Notes

## Kanishk - Platform Runtime

Use the canonical:

```text
Platform Registry
Platform Discovery
Platform Capability SDK
```

Do not create another Insight-specific registry or discovery mechanism.

## Pritesh - Quantum Platform Services

InsightBridge declares:

```text
QuantumCommunicationGateway
```

as an integration dependency.

Quantum execution remains outside Insight ownership.

## Dhiraj - Quantum Runtime

Insight does not replace or redesign the Quantum Runtime.

Where Quantum Runtime interaction is required, use the agreed platform contract and runtime boundary.

## Vinayak - Testing / Certification

Current live evidence covers:

```text
Registration
Discovery
Invocation
Evidence
Replay
Health
Telemetry
Version Compatibility
Failure Paths
End-to-End Summary
```

---

# 16. Current Live Status

| Area | Status |
|---|---|
| InsightFlow registration | VERIFIED |
| InsightBridge registration | VERIFIED |
| InsightCore registration | VERIFIED |
| Discovery | VERIFIED |
| Version negotiation | VERIFIED |
| Runtime invocation | VERIFIED |
| Execution evidence | VERIFIED |
| Replay validation | VERIFIED |
| Health visibility | VERIFIED |
| Telemetry visibility | VERIFIED |
| Failure-path evidence | VERIFIED |
| Live end-to-end convergence | VERIFIED |

Current deployed version:

```text
1.0.2
```

---

# 17. Endpoint Summary

| Purpose | Method | Endpoint |
|---|---|---|
| InsightFlow health | GET | `https://insight-constitutional-runtime.onrender.com/api/v1/health/insightflow.runtime.intelligence.v1` |
| InsightBridge health | GET | `https://insight-constitutional-runtime.onrender.com/api/v1/health/insightbridge.runtime.intelligence.v1` |
| InsightCore health | GET | `https://insight-constitutional-runtime.onrender.com/api/v1/health/insightcore.runtime.intelligence.v1` |
| Insight execution | POST | `https://insight-constitutional-runtime.onrender.com/api/v1/execute` |
| Platform service registration | POST | `https://bhiv-qcg.onrender.com/registry/platform/v1/register` |
| Capability registration | POST | `https://bhiv-qcg.onrender.com/registry/capabilities/register` |
| InsightFlow registry lookup | GET | `https://bhiv-qcg.onrender.com/registry/platform/v1/services/insightflow.runtime.intelligence.v1` |
| InsightBridge registry lookup | GET | `https://bhiv-qcg.onrender.com/registry/platform/v1/services/insightbridge.runtime.intelligence.v1` |
| InsightCore registry lookup | GET | `https://bhiv-qcg.onrender.com/registry/platform/v1/services/insightcore.runtime.intelligence.v1` |

---

# 18. Integration Rule

Use the canonical platform path:

```text
Fresh BHIV Capability
        |
        v
Canonical Platform Discovery
        |
        v
Insight Capability
        |
        v
Canonical Insight Runtime Execution
```

Do not:

- create a second registry;
- create a second runtime;
- bypass the canonical Platform Runtime;
- hard-code platform internals into Insight;
- replace Platform SDK discovery with a custom discovery layer;
- use localhost or temporary tunnel URLs as production endpoints.

---

## Ownership

**Insight Stack**

Owns:

```text
InsightFlow
InsightBridge
InsightCore
Insight Runtime
```

Platform-side dependencies:

```text
Platform Runtime
Platform Registry
Platform Discovery
Platform Capability SDK
```

For platform-side endpoint changes, coordinate with the Platform Runtime owner rather than changing Insight-side contracts independently.

---

**Document status: TEAM SHARING COPY - NOT PART OF THE REPOSITORY**
