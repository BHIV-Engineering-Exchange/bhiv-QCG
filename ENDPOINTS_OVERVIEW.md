# TANTRA Project: API Endpoints Overview

This document provides a comprehensive overview of all the API endpoints available in the QCG ecosystem project, split across the primary Operational Readiness Web Server and the Platform Service Discovery server.

## 1. Operational Readiness API (`web_server.py`)
This runs as a robust FastAPI server and serves as the main integration layer.

| Method | Endpoint | Purpose |
| ------ | -------- | ------- |
| `GET` | `/health`, `/health/live`, `/health/ready` | Provides health status, readiness indicators, and related metrics for the system. |
| `GET` | `/capabilities` | Retrieves the capability manifest and API contracts of the active integration layer. |
| `POST`| `/verify` | Synchronous end-to-end integration flow verification. Primary ingestion pipeline for BHIV contracts from Pravah/NICAI. |
| `POST`| `/gc/validate` | Live Governance (GC) validation flow. Applies strict constitutional policies without mutating state. |
| `GET` | `/evidence/certificate/{execution_id}`| Retrieves an execution certificate complete with a Merkle proof for MDU retrieval. |
| `GET` | `/evidence/trace/{trace_id}` | Retrieves the complete execution history lineage for a given trace ID. |
| `GET` | `/evidence/{hashed_trace}` | Live MDU provenance exchange endpoint that returns the Merkle Inclusion Proof for a given execution trace. |
| `GET` | `/replay/lineage/{trace_id}` | Replay authority integration API providing verifiable lineage paths for given execution artifacts. |

---

## 2. Platform Service Discovery API (`platform_service_discovery.py`)
This is the canonical REST API for the zero-configuration discovery of platform capabilities.

### Federation & Discovery Endpoints
| Method | Endpoint | Purpose |
| ------ | -------- | ------- |
| `GET` | `/platform/v1/services` | Lists all discovered platform services across the registry. |
| `GET` | `/platform/v1/health` | Overall health and uptime of the discovery server itself. |
| `GET` | `/platform/v1/readiness`| Indicates if the server is fully ready and has initialized the registry. |
| `GET` | `/platform/v1/metrics`  | Prometheus-compatible metrics output for requests, uptimes, and registry size. |
| `GET` | `/platform/v1/evidence` | Status of the discovery evidence chain (integrity and history of events). |
| `GET` | `/platform/v1/version`  | General version outputs for discovery server and registry implementation. |
| `POST`| `/platform/v1/register` | Authenticated endpoint to register a new platform service to the federation. |
| `POST`| `/platform/v1/heartbeat`| Allows a registered service to send a heartbeat and renew its lease in the registry. |
| `POST`| `/platform/v1/revoke`   | Revokes or de-registers an existing service from the registry. |

### Federation specific (Inter-node actions)
| Method | Endpoint | Purpose |
| ------ | -------- | ------- |
| `GET` | `/platform/v1/federation/status` | Current federation topology and synchronization state across nodes. |
| `GET` | `/platform/v1/federation/audit` | Retrieves the federation audit log of registration, syncing, and revocation events. |
| `POST`| `/platform/v1/federation/sync`  | Triggers a manual anti-entropy sync of capabilities between federated peers. |
| `GET` | `/platform/v1/certificates`     | Lists all active service certificates allocated by the federation CA. |

### Per-Service Endpoints (Querying a Specific Application)
| Method | Endpoint | Purpose |
| ------ | -------- | ------- |
| `GET` | `/platform/v1/services/{service_id}`             | Retrieves the specific registry record for the given service ID. |
| `GET` | `/platform/v1/services/{service_id}/versions`    | Get available versions of a specific service. |
| `GET` | `/platform/v1/services/{service_id}/metadata`    | Fetch the structural metadata associated with a service capability. |
| `GET` | `/platform/v1/services/{service_id}/contracts`   | Lists the input/output operation contracts bound to this service. |
| `GET` | `/platform/v1/services/{service_id}/endpoints`   | Fetches the live routed execution URLs mapped to this service. |
| `GET` | `/platform/v1/services/{service_id}/health`      | Proxy check to the specific service's heartbeat/health status. |
| `GET` | `/platform/v1/services/{service_id}/compatibility`| Views current deprecation & backward compatibility status of the service. |
| `POST`| `/platform/v1/negotiate` | Negotiates a compatible interaction version for a specific `service_id` via the payload. |
| `POST`| `/platform/v1/services/{service_id}` | Experimental mock mechanism simulating an execution against a given service ID. |
