"""
tests/test_ws_c_tantra_vajra_integration.py

End-to-end positive and negative integration tests verifying that Workstream C
(Photonics & Cryogenic RF Systems) integrates cleanly through TANTRA contracts,
TANTRAIntegrationHarness, Replay Authority, and Merkle/VAJRA provenance.
"""

import uuid
import pytest

import config
from integration_harness import TANTRAIntegrationHarness
from photonics_rf_tantra_bridge import (
    PhotonicRFBoundaryError,
    build_ws_c_telemetry_payload,
    submit_ws_c_to_tantra,
)


@pytest.fixture
def isolated_harness(monkeypatch, tmp_path):
    """Create a harness using isolated temp stores and disabled remote calls."""
    monkeypatch.setattr(config, "KESHAV_ENABLED", False)
    monkeypatch.setattr(config, "PRANA_ENABLED", False)
    monkeypatch.setattr(config, "VAJRA_ENABLED", False)

    harness = TANTRAIntegrationHarness()
    # Isolate replay, trust, and ledger stores to tmp_path so tests never mutate repo state
    from canonical_replay_authority import CanonicalReplayAuthority
    from evidence_ledger import EvidenceLedger
    from integration_interfaces import ReplayVerifierInterface, TrustVerifierInterface, HealthStatusInterface
    from producer_verification import ProducerRegistry, ProducerVerificationLayer

    harness.replay_registry = harness.replay_registry.__class__(path=tmp_path / "replay.json")
    harness.trust_registry = ProducerRegistry(path=tmp_path / "trust.json")
    harness.ledger = EvidenceLedger(persistence_path=str(tmp_path / "ledger.json"))
    harness.replay_auth = CanonicalReplayAuthority(harness.replay_registry)
    harness.verifier_layer = ProducerVerificationLayer(harness.trust_registry)
    harness.replay_iface = ReplayVerifierInterface(harness.replay_auth)
    harness.trust_iface = TrustVerifierInterface(harness.verifier_layer)
    harness.health_iface = HealthStatusInterface(harness.replay_registry)
    return harness


def test_ws_c_e2e_tantra_vajra_flow(isolated_harness):
    """WS-C simulated optical/RF payload flows end-to-end into a Merkle certificate."""
    trace_id = f"wsc-e2e-{uuid.uuid4().hex[:12]}"
    res = submit_ws_c_to_tantra(
        isolated_harness,
        trace_id=trace_id,
        distance_km=50.0,
        message_bits="11",
        shots=256,
    )

    assert res["success"] is True
    assert res["trace_id"] == trace_id
    pipeline = res["pipeline_response"]
    assert pipeline["flow_status"] == "COMPLETED"
    assert pipeline["trace_id"] == trace_id
    assert pipeline["stages"]["replay"]["is_valid"] is True
    assert pipeline["stages"]["trust"]["passed"] is True
    assert pipeline["stages"]["consensus"]["consensus_reached"] is True

    cert = res["certificate"]
    assert cert is not None
    assert cert["execution_record"]["trace_id"] == trace_id
    assert len(cert["merkle_root"]) == 64
    assert res["signed_contract"]["execution_path"] == "SIMULATED"


def test_ws_c_rejects_classical_photonics_quantum_claim():
    """Silicon photonic MZI mesh cannot falsely claim quantum execution."""
    with pytest.raises(PhotonicRFBoundaryError, match="CLASSICAL_ANALOG_PHOTONICS"):
        build_ws_c_telemetry_payload(
            technology_name="SILICON_PHOTONIC_MZI_MESH",
            claim_quantum=True,
        )


def test_ws_c_rejects_excessive_qber_optical_link():
    """Optical link exceeding the 11% QBER threshold must fail closed."""
    with pytest.raises(PhotonicRFBoundaryError, match="QBER"):
        build_ws_c_telemetry_payload(
            technology_name="SUPERDENSE_CODING_OPTICAL_LINK",
            distance_km=500.0,
            claim_quantum=True,
        )


def test_ws_c_rejects_duplicate_replay(isolated_harness):
    """Re-submitting the exact same signed WS-C contract must fail replay protection."""
    trace_id = f"wsc-dup-{uuid.uuid4().hex[:12]}"
    first = submit_ws_c_to_tantra(isolated_harness, trace_id=trace_id, shots=128)
    assert first["success"] is True

    ok_dup, dup_resp = isolated_harness.process_incoming_contract(
        first["signed_contract"],
        first["producer_public_key"],
    )
    assert ok_dup is False
    assert dup_resp["flow_status"] == "HALTED"
    assert "REPLAY_" in dup_resp["halt_reason"]


def test_ws_c_rejects_tampered_payload(isolated_harness):
    """Mutating the WS-C payload after signing must halt at contract/trust validation."""
    first = submit_ws_c_to_tantra(isolated_harness, shots=128)
    assert first["success"] is True

    tampered = dict(first["signed_contract"])
    tampered["trace_id"] = f"wsc-tamper-{uuid.uuid4().hex[:12]}"
    tampered["payload"] = {"tampered": True}

    ok_tamper, tamper_resp = isolated_harness.process_incoming_contract(
        tampered,
        first["producer_public_key"],
    )
    assert ok_tamper is False
    assert tamper_resp["flow_status"] == "HALTED"
    assert "INVALID_SIGNATURE" in tamper_resp["halt_reason"]
