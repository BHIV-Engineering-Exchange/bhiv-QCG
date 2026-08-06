# Replay Documentation

## Replay Safety in the Bucket
The Universal Solver Fabric is designed to be completely deterministic. If a transaction is replayed, the output is identical. However, the system must prevent accidental execution of stale messages or duplicate evidence ingestion.

## Duplicate Protection
When evidence is submitted to the Live Bucket:
1. The `artifact_id` is evaluated against the global ledger.
2. If the ID exists, the Bucket rejects the POST request.
3. The local `bucket_client.py` captures this rejection as a valid architectural constraint and marks the submission as a known duplicate.

## Deterministic Retrieval
During replay edge cases or node crashes, a recovery node can query the Bucket via `GET /bucket/artifact/{artifact_id}` or fetch the trace lineage via `/bucket/artifacts?trace_id={trace_id}`. This deterministic retrieval allows the local `ReplayEnforcer` to sync its state and resume tracking sequence numbers without local storage dependencies.
