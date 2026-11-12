"""
tests/test_vajra_integration.py — Unit and Live Integration Tests for VAJRA Client

Covers:
1. Unit tests (mocked HTTP) for VajraClient health, chain-integrity, fail-closed auth,
   Bearer secret redaction in evidence logs, and TANTRAIntegrationHarness wiring.
2. Live read-only and negative fail-closed tests against https://vajra.blackholeinfiverse.com.
"""

import io
import json
import uuid
from datetime import datetime, timezone
from unittest.mock import patch
import urllib.error

import pytest

import config
from canonical_replay_authority import CanonicalReplayAuthority
from evidence_ledger import EvidenceLedger
from execution_contract import ComputationExecutionContract
from integration_harness import TANTRAIntegrationHarness
from integration_interfaces import HealthStatusInterface, ReplayVerifierInterface, TrustVerifierInterface
from node_identity import NodeSigner
from producer_verification import ProducerRegistry, ProducerVerificationLayer
from provenance import sign_contract
from vajra_client import VajraClient


class _DummyHTTPResponse:
    def __init__(self, payload: dict, status: int = 200):
        self._body = json.dumps(payload).encode("utf-8")
        self._status = status

    def getcode(self) -> int:
        return self._status

    def read(self) -> bytes:
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


def _make_isolated_harness(monkeypatch, tmp_path, *, vajra_enabled: bool) -> TANTRAIntegrationHarness:
    monkeypatch.setattr(config, "KESHAV_ENABLED", False)
    monkeypatch.setattr(config, "PRANA_ENABLED", False)
    monkeypatch.setattr(config, "VAJRA_ENABLED", vajra_enabled)

    harness = TANTRAIntegrationHarness()
    harness.replay_registry = harness.replay_registry.__class__(path=tmp_path / "replay.json")
    harness.trust_registry = ProducerRegistry(path=tmp_path / "trust.json")
    harness.ledger = EvidenceLedger(persistence_path=str(tmp_path / "ledger.json"))
    harness.replay_auth = CanonicalReplayAuthority(harness.replay_registry)
    harness.verifier_layer = ProducerVerificationLayer(harness.trust_registry)
    harness.replay_iface = ReplayVerifierInterface(harness.replay_auth)
    harness.trust_iface = TrustVerifierInterface(harness.verifier_layer)
    harness.health_iface = HealthStatusInterface(harness.replay_registry)
    return harness


def _make_signed_contract(trace_id: str | None = None):
    trace_id = trace_id or f"vajra-test-{uuid.uuid4().hex[:12]}"
    node_id = f"NODE_VAJRA_{uuid.uuid4().hex[:8]}"
    signer = NodeSigner(node_id=node_id, node_role="QUANTUM")
    contract = ComputationExecutionContract(
        producer_type="QUANTUM",
        producer_id=node_id,
        payload={"domain": "VANA", "shots": 256, "best_bitstring": "110101"},
        confidence=0.99,
        trace_id=trace_id,
        contract_version="2.0.0",
        execution_classification="QUANTUM_SIMULATED",
        execution_path="SIMULATED",
        timestamp=datetime.now(timezone.utc).isoformat(),
    )
    signed = sign_contract(contract, signer)
    return signed.to_dict(), signer.identity.public_key, trace_id


# ---------------------------------------------------------------------------
# Unit Tests (Mocked HTTP)
# ---------------------------------------------------------------------------

def test_vajra_client_health_parsing():
    client = VajraClient(base_url="https://vajra.example.test", tantra_secret="")
    mock_payload = {
        "data": {"block_height": 7, "pending_txs": 2, "total_supply": 1000000000},
        "message": "Blockchain API is running",
        "status": "healthy",
        "success": True,
    }
    with patch("urllib.request.urlopen", return_value=_DummyHTTPResponse(mock_payload, 200)):
        health = client.health()

    assert health.status == "OK"
    assert health.success is True
    assert health.block_height == 7
    assert health.pending_txs == 2


def test_vajra_client_chain_integrity_parsing():
    client = VajraClient(base_url="https://vajra.example.test", tantra_secret="")
    mock_payload = {
        "intact": True,
        "message": "truth store chain is intact — no tampering detected",
        "success": True,
    }
    with patch("urllib.request.urlopen", return_value=_DummyHTTPResponse(mock_payload, 200)):
        res = client.chain_integrity()

    assert res.intact is True
    assert res.success is True
    assert res.http_status == 200


def test_vajra_client_fails_closed_without_secret(monkeypatch):
    monkeypatch.setattr(config, "VAJRA_TANTRA_SECRET", "")
    client = VajraClient(base_url="https://vajra.example.test", tantra_secret="")
    res = client.record_provenance({"trace_id": "t-1", "execution_id": "e-1"})

    assert res.status == "REQUIRES_EXTERNAL_ACCESS"
    assert res.authenticated is False
    assert res.http_status == 0


def test_vajra_client_redacts_secret_in_evidence_log():
    secret = "super-secret-token-value"
    client = VajraClient(base_url="https://vajra.example.test", tantra_secret=secret)
    with patch("urllib.request.urlopen", return_value=_DummyHTTPResponse({"success": True}, 200)):
        res = client.record_provenance({"trace_id": "t-2", "execution_id": "e-2"})

    assert res.status == "RECORDED"
    assert res.authenticated is True
    evidence_json = client.get_evidence_log()
    assert secret not in evidence_json
    assert "Bearer ***REDACTED***" in evidence_json


def test_vajra_client_401_negative_handling():
    client = VajraClient(base_url="https://vajra.example.test", tantra_secret="")
    err_body = io.BytesIO(b'{"error":"UNAUTHORIZED","message":"Missing or malformed Authorization: Bearer header."}')
    http_err = urllib.error.HTTPError(
        url="https://vajra.example.test/api/vajra/provenance/retrieval",
        code=401,
        msg="Unauthorized",
        hdrs={},
        fp=err_body,
    )
    with patch("urllib.request.urlopen", side_effect=http_err):
        res = client.record_provenance({"trace_id": "t-unauth"}, allow_unauthenticated=True)

    assert res.status == "UNAUTHORIZED"
    assert res.http_status == 401
    assert res.authenticated is False


def test_harness_skips_vajra_when_disabled(monkeypatch, tmp_path):
    harness = _make_isolated_harness(monkeypatch, tmp_path, vajra_enabled=False)
    contract_dict, pub_key, _ = _make_signed_contract()
    ok, resp = harness.process_incoming_contract(contract_dict, pub_key)

    assert ok is True
    assert resp["flow_status"] == "COMPLETED"
    assert resp["stages"]["vajra_anchor"]["status"] == "SKIPPED"


# ---------------------------------------------------------------------------
# Live Integration Tests (https://vajra.blackholeinfiverse.com)
# ---------------------------------------------------------------------------

def test_vajra_live_health_and_chain_integrity():
    client = VajraClient()
    health = client.health()
    assert health.status == "OK", f"VAJRA /api/health failed: {health.raw_response}"
    assert health.block_height >= 1

    integrity = client.chain_integrity()
    assert integrity.success is True
    assert integrity.intact is True


def test_vajra_live_provenance_rejects_unauthenticated():
    client = VajraClient(tantra_secret="")
    res = client.record_provenance(
        {"trace_id": "unauth-probe", "execution_id": "unauth-probe"},
        allow_unauthenticated=True,
    )
    assert res.http_status == 401
    assert res.status == "UNAUTHORIZED"
    assert res.authenticated is False


def test_harness_live_e2e_anchors_to_vajra_chain_integrity(monkeypatch, tmp_path):
    monkeypatch.setattr(config, "VAJRA_TANTRA_SECRET", "")
    harness = _make_isolated_harness(monkeypatch, tmp_path, vajra_enabled=True)
    contract_dict, pub_key, trace_id = _make_signed_contract()

    ok, resp = harness.process_incoming_contract(contract_dict, pub_key)
    assert ok is True
    assert resp["flow_status"] == "COMPLETED"
    vajra_stage = resp["stages"]["vajra_anchor"]
    assert vajra_stage["live"] is True
    assert vajra_stage["chain_intact"] is True
    assert vajra_stage["status"] == "REQUIRES_EXTERNAL_ACCESS"
    assert resp["trace_continuity"]["vajra_chain_intact"] is True
    assert resp["trace_continuity"]["vajra_status"] == "REQUIRES_EXTERNAL_ACCESS"
    assert len(json.loads(harness.get_vajra_evidence())) >= 1

