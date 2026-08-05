# API Documentation: Live Bucket Integration

This document outlines the specific endpoints used by the USF/QCG to interface with the Live Bucket. All API calls are executed by `bucket_client.py`.

## 1. Health Check
`GET /docs` (or `/health`)
**Purpose**: Verifies bucket availability.
**Response**: HTTP 200 indicating the service is reachable.

## 2. Publish Evidence
`POST /bucket/artifact`
**Purpose**: Appends a new execution or runtime artifact to the canonical chain.
**Body Schema**:
```json
{
  "artifact_id": "<uuid>",
  "trace_id": "<uuid>",
  "timestamp_utc": "<iso-8601>",
  "schema_version": "1.0.0",
  "source_module_id": "usf",
  "artifact_type": "execution_evidence",
  "parent_hash": "<hex>",
  "payload": {}
}
```
**Response**: 
- `200 OK`: Contains assigned `hash`.
- `400 Bad Request`: Used for ValidationError (e.g., race condition on `parent_hash`).
- `409 Conflict`: If `artifact_id` is a duplicate.

## 3. Retrieve Evidence
`GET /bucket/artifact/{artifact_id}`
**Purpose**: Fetches a single artifact by its ID.
**Response**: The JSON artifact payload as submitted, plus bucket-assigned metadata (like `chain_verified`).

## 4. Retrieve Trace History
`GET /bucket/artifacts?trace_id={trace_id}`
**Purpose**: Fetches all artifacts associated with a single execution lineage.
**Response**: An array of artifacts in sequential order.

## 5. Validate Chain Continuity
`GET /bucket/validate-chain/{artifact_id}`
**Purpose**: Cryptographically verifies the unbroken chain of custody up to the specified artifact.
**Response**: 
```json
{
  "is_valid": true,
  "message": "Chain mathematically proven."
}
```
