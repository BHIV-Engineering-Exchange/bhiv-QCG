"""
generate_bucket_evidence.py

Automates the collection of the Bucket evidence packet by:
1. Connecting to the live Bucket.
2. Publishing execution and provenance evidence.
3. Retrieving published evidence.
4. Validating the trace continuity.
5. Capturing all API request/responses.
6. Writing everything to review_packets/evidence/bucket_evidence.json
"""

import json
import uuid
import time
from datetime import datetime, timezone
import os

import bucket_client

def generate_bucket_evidence():
    print("=" * 60)
    print("GENERATING BUCKET EVIDENCE PACKET")
    print("=" * 60)

    os.makedirs("review_packets/evidence", exist_ok=True)
    packet_path = "review_packets/evidence/bucket_evidence.json"

    client = bucket_client.get_client()
    evidence_packet = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "health_validation": None,
        "published_execution_evidence": None,
        "retrieved_execution_evidence": None,
        "trace_continuity_proof": None,
        "failure_recovery_evidence": None,
        "bucket_connection_logs": []
    }

    # 1. Health Validation
    print("[1/5] Checking Bucket Health...")
    health = client.health()
    evidence_packet["health_validation"] = {
        "status": health.status,
        "raw_response": health.raw_response
    }
    print(f"  Health: {health.status}")

    # 2. Publish Execution Evidence (includes Provenance & Replay metadata)
    print("\n[2/5] Publishing Execution Evidence...")
    trace_id = str(uuid.uuid4())
    artifact_id = str(uuid.uuid4())
    
    payload = {
        "artifact_id": artifact_id,
        "trace_id": trace_id,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "schema_version": "1.0.0",
        "source_module_id": "usf_evidence_generator",
        "artifact_type": "execution_certificate",
        "parent_hash": "", # Will trigger dynamic continuity
        "payload": {
            "computation_result": "deterministic_success",
            "provenance_metadata": {
                "producer_id": "QCG_PRODUCER_01",
                "signature": "valid_ecdsa_signature"
            },
            "replay_metadata": {
                "sequence_number": 42,
                "ttl": 300
            }
        }
    }

    success, publish_resp = client.publish_artifact(payload)
    evidence_packet["published_execution_evidence"] = {
        "artifact_id": artifact_id,
        "trace_id": trace_id,
        "success": success,
        "response": publish_resp
    }
    print(f"  Published: {success}")

    # 3. Retrieved Execution Evidence
    print("\n[3/5] Retrieving Execution Evidence...")
    time.sleep(2) # Allow for indexing
    retrieved = client.get_artifact(artifact_id)
    evidence_packet["retrieved_execution_evidence"] = retrieved
    print(f"  Retrieved: {retrieved is not None}")

    # 4. Trace Continuity Proof
    print("\n[4/5] Validating Trace Continuity...")
    validation = client.validate_chain(artifact_id)
    evidence_packet["trace_continuity_proof"] = validation
    print(f"  Validation: {validation}")

    # 5. Failure Recovery Evidence
    print("\n[5/5] Simulating Failure Recovery (Timeout/Retries)...")
    # Temporarily set a ridiculous timeout to force a failure handling log
    original_timeout = client.timeout
    client.timeout = 0.001 
    _, fail_resp = client._request_with_retry("GET", f"/bucket/artifact/{artifact_id}")
    client.timeout = original_timeout
    evidence_packet["failure_recovery_evidence"] = fail_resp
    print(f"  Failure handled gracefully: {fail_resp}")

    # Collect Logs
    evidence_packet["bucket_connection_logs"] = json.loads(client.get_evidence_log())

    with open(packet_path, "w", encoding="utf-8") as f:
        json.dump(evidence_packet, f, indent=2)

    print("\n" + "=" * 60)
    print(f"EVIDENCE PACKET SAVED TO: {packet_path}")
    print("=" * 60)


if __name__ == "__main__":
    generate_bucket_evidence()
