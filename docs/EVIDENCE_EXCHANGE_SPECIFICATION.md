# Evidence Exchange Specification

## 1. Overview
This specification details how Universal Solver Fabric and QCG format and exchange evidence with the live Bucket.

## 2. Standard Schema
Every published artifact adheres to the following JSON schema:
```json
{
  "artifact_id": "<uuid>",
  "trace_id": "<uuid>",
  "timestamp_utc": "YYYY-MM-DDTHH:MM:SSZ",
  "schema_version": "1.0.0",
  "source_module_id": "<string>",
  "artifact_type": "<string>",
  "parent_hash": "<hex-string>",
  "payload": { ... }
}
```

## 3. Idempotent Publishing
Publishing guarantees exactly-once semantics via cryptographic replay protection. If an `artifact_id` has already been ingested, the Bucket rejects the duplicate. The Bucket Client gracefully handles `429` rate limits and `5xx` transient errors via exponential backoff (up to 3 retries).

## 4. Continuity Assurance
Before publishing, the client fetches the latest chain hash to populate `parent_hash`. In concurrent environments, race conditions on the `parent_hash` are caught (HTTP 400 with a specific validation error), and the client automatically recalculates the continuity hash and retries.
