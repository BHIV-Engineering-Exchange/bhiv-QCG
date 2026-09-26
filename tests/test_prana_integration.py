"""
test_prana_integration.py — Production Integration Tests for TANTRA -> PRANA

Tests:
1. PRANA Health Check
2. PRANA System Health Check
3. PRANA Event Ingestion via PranaClient
4. Replay Record Retrieval from MongoDB via PRANA /replay/{trace_id}
5. Full TANTRA Contract Verification Pipeline -> PRANA Ingest Stage
6. Trace continuity end-to-end (trace_id preserved from TANTRA to PRANA and MongoDB)
7. Failure handling (unreachable / invalid payload / 4xx handling)
"""

import time
import uuid
import pytest
from datetime import datetime, timezone

from prana_client import PranaClient
from integration_harness import TANTRAIntegrationHarness
from execution_contract import ComputationExecutionContract
from provenance import sign_contract
from node_identity import NodeSigner


@pytest.fixture(scope="module")
def prana_client():
    return PranaClient()


@pytest.fixture(scope="module")
def harness():
    return TANTRAIntegrationHarness()


def test_prana_live_health(prana_client):
    """Verify PRANA /health endpoint returns 200 and healthy MongoDB connection."""
    health = prana_client.health()
    assert health.status == "OK", f"PRANA health failed: {health.raw_response}"
    assert health.service == "bhiv-prana"
    assert health.mongodb_connected is True
    assert health.database_name == "prana"


def test_prana_live_system_health(prana_client):
    """Verify PRANA /prana/system/health returns 200 with stateful mode."""
    sys_health = prana_client.system_health()
    assert sys_health.status == "OK"
    assert sys_health.mode == "stateful"
    assert sys_health.mongodb_connected is True
    assert sys_health.replay_records_count >= 0


def test_prana_event_ingestion(prana_client):
    """Verify PRANA /prana/ingest accepts a TANTRA event and returns forwarded status."""
    trace_id = f"tantra-test-{uuid.uuid4().hex}"
    payload = {
        "producer_id": "TANTRA_PRODUCER_TEST",
        "producer_type": "QUANTUM",
        "confidence": 0.99,
        "runtime_hash": f"hash_{uuid.uuid4().hex[:16]}",
        "test_marker": "tantra_prana_integration",
    }

    res = prana_client.ingest_event(
        payload=payload,
        trace_id=trace_id,
        event_type="truth_classification",
        source_system="bhiv-qcg",
        certification_status="CERTIFIED",
    )

    assert res.status == "forwarded"
    assert res.http_status == 200
    assert len(res.event_id) > 0
    assert res.trace_id == trace_id


def test_prana_mongodb_replay_persistence(prana_client):
    """Verify that an ingested event can be retrieved from PRANA's MongoDB replay store."""
    trace_id = f"tantra-replay-{uuid.uuid4().hex}"
    payload = {
        "producer_id": "TANTRA_REPLAY_TEST",
        "runtime_hash": f"hash_{uuid.uuid4().hex[:16]}",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    ingest_res = prana_client.ingest_event(
        payload=payload,
        trace_id=trace_id,
        event_type="truth_classification",
        source_system="bhiv-qcg",
        certification_status="CERTIFIED",
    )
    assert ingest_res.status == "forwarded"

    # Give MongoDB a moment to commit
    time.sleep(0.5)

    replay = prana_client.get_replay(trace_id)
    assert replay is not None, f"Replay record not found for trace_id={trace_id}"
    assert replay["trace_id"] == trace_id
    assert replay["certification_status"] == "CERTIFIED"
    assert replay["payload"]["payload"]["producer_id"] == "TANTRA_REPLAY_TEST"


def test_tantra_harness_e2e_prana_flow(harness):
    """Verify full TANTRA integration harness processes contract and forwards to PRANA."""
    trace_id = f"tantra-harness-{uuid.uuid4().hex}"
    signer = NodeSigner(node_id="NODE_PRANA_E2E", node_role="CLASSICAL")

    contract = ComputationExecutionContract(
        producer_type="CLASSICAL",
        producer_id="NODE_PRANA_E2E",
        payload={"task": "prana_production_verification", "value": 42},
        confidence=0.98,
        trace_id=trace_id,
        contract_version="2.0.0",
        timestamp=datetime.now(timezone.utc).isoformat(),
    )

    signed_c = sign_contract(contract, signer)
    success, response = harness.process_incoming_contract(
        signed_c.to_dict(),
        signer.identity.public_key,
    )

    assert success is True
    assert response["flow_status"] == "COMPLETED"
    assert "prana_ingest" in response["stages"]
    prana_stage = response["stages"]["prana_ingest"]
    assert prana_stage["status"] == "forwarded"
    assert prana_stage["live"] is True
    assert len(prana_stage["event_id"]) > 0

    # Trace continuity verification
    assert response["trace_continuity"]["prana_event_id"] == prana_stage["event_id"]
    assert response["trace_continuity"]["prana_status"] == "forwarded"


def test_prana_failure_handling_invalid_url():
    """Verify failure handling when PRANA URL is unreachable."""
    client = PranaClient(base_url="http://127.0.0.1:9999", timeout=1)
    health = client.health()
    assert health.status == "UNHEALTHY"

    res = client.ingest_event(payload={"data": "test"}, trace_id="fail-trace-001")
    assert res.status == "FAILED"
    assert res.error is not None
