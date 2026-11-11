"""
photonics_rf_tantra_bridge.py — WS-C (Photonics & Cryogenic RF) ↔ TANTRA ↔ VAJRA Bridge

Connects the simulated WS-C Photonics/Cryogenic-RF models (`photonics_rf_systems`)
to QCG's canonical TANTRA contract pipeline (`ComputationExecutionContract`,
`TANTRAIntegrationHarness`) and VAJRA cryptographic provenance (`NodeSigner`,
`EvidenceLedger`, `execution_certificate`) without duplicating runtime or ledger logic.

All executions are explicitly labeled as SIMULATED (`execution_path="SIMULATED"`)
and strictly enforce the Classical-vs-Quantum Optical Boundary Doctrine.
"""

from __future__ import annotations

import uuid
from dataclasses import asdict
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from execution_contract import ComputationExecutionContract, validate_contract
from integration_harness import TANTRAIntegrationHarness
from node_identity import NodeSigner
from photonics_rf_systems import (
    CryogenicRFLineModel,
    OpticalFiberParameters,
    SinglePhotonDetectorParameters,
    calculate_optical_link_budget,
    simulate_cryogenic_attenuation_chain,
    simulate_superdense_message,
    validate_optical_technology_boundary,
)
from photonics_rf_systems.architectural_taxonomy import OpticalTechnologyParadigm
from provenance import sign_contract
from provenance_api import execution_certificate, execution_history


class PhotonicRFBoundaryError(ValueError):
    """Raised when a WS-C optical/RF operation violates boundary or link-threshold rules."""


def build_ws_c_telemetry_payload(
    *,
    technology_name: str = "SUPERDENSE_CODING_OPTICAL_LINK",
    distance_km: float = 50.0,
    message_bits: str = "11",
    shots: int = 512,
    seed: int = 42,
    qubit_frequency_ghz: float = 5.0,
    claim_quantum: bool = True,
) -> Dict[str, Any]:
    """
    Execute WS-C simulated optical link budget, cryogenic RF thermal profile,
    and (when quantum optical paradigm is active) superdense coding simulation.
    """
    taxonomy = validate_optical_technology_boundary(technology_name)
    paradigm = taxonomy["paradigm"]

    if claim_quantum and paradigm == OpticalTechnologyParadigm.CLASSICAL_ANALOG_PHOTONICS:
        raise PhotonicRFBoundaryError(
            f"Technology '{technology_name}' is {paradigm.value} and cannot claim quantum execution."
        )

    link_budget = calculate_optical_link_budget(
        distance_km=distance_km,
        fiber=OpticalFiberParameters(),
        detector=SinglePhotonDetectorParameters(),
    )
    if not link_budget.within_security_threshold:
        raise PhotonicRFBoundaryError(
            f"Optical link QBER {link_budget.qber_percentage}% exceeds 11.0% security threshold at {distance_km} km."
        )

    cryo_profile = simulate_cryogenic_attenuation_chain(
        CryogenicRFLineModel(qubit_frequency_ghz=qubit_frequency_ghz)
    )
    if not cryo_profile["is_ground_state_preserved"]:
        raise PhotonicRFBoundaryError(
            "Cryogenic RF attenuation profile failed ground-state preservation (n_th >= 1e-3)."
        )

    superdense_result: Optional[Dict[str, Any]] = None
    if paradigm == OpticalTechnologyParadigm.TRUE_QUANTUM_LINEAR_OPTICS:
        superdense_result = simulate_superdense_message(message_bits=message_bits, shots=shots, seed=seed)
        if not superdense_result["verified"]:
            raise PhotonicRFBoundaryError(
                f"Superdense channel simulation failed verification for message '{message_bits}'."
            )

    return {
        "workstream": "WS-C",
        "technology_name": technology_name,
        "optical_paradigm": paradigm.value,
        "truth_classification": "SIMULATED AND TESTED",
        "hardware_status": "BLOCKED (Phase 1 Gate 1 procurement freeze; no physical photonic/RF hardware)",
        "optical_link_budget": asdict(link_budget),
        "cryogenic_rf_profile": {
            "qubit_frequency_ghz": cryo_profile["qubit_frequency_ghz"],
            "total_line_attenuation_db": cryo_profile["total_line_attenuation_db"],
            "base_plate_equilibrium_n_th": cryo_profile["base_plate_equilibrium_n_th"],
            "is_ground_state_preserved": cryo_profile["is_ground_state_preserved"],
        },
        "superdense_channel": superdense_result,
    }


def submit_ws_c_to_tantra(
    harness: TANTRAIntegrationHarness,
    *,
    trace_id: Optional[str] = None,
    producer_id: Optional[str] = None,
    technology_name: str = "SUPERDENSE_CODING_OPTICAL_LINK",
    distance_km: float = 50.0,
    message_bits: str = "11",
    shots: int = 512,
    seed: int = 42,
    qubit_frequency_ghz: float = 5.0,
    claim_quantum: bool = True,
) -> Dict[str, Any]:
    """
    Build a WS-C simulation payload, wrap it into a signed ComputationExecutionContract,
    run it through TANTRAIntegrationHarness, and return the VAJRA/Merkle certificate.
    """
    effective_trace_id = trace_id or f"wsc-trace-{uuid.uuid4().hex}"
    effective_producer = producer_id or f"WSC_PHOTONICS_RF_{uuid.uuid4().hex[:8]}"

    payload = build_ws_c_telemetry_payload(
        technology_name=technology_name,
        distance_km=distance_km,
        message_bits=message_bits,
        shots=shots,
        seed=seed,
        qubit_frequency_ghz=qubit_frequency_ghz,
        claim_quantum=claim_quantum,
    )

    is_quantum = payload["optical_paradigm"] == OpticalTechnologyParadigm.TRUE_QUANTUM_LINEAR_OPTICS.value
    producer_type = "QUANTUM" if is_quantum else "CLASSICAL"
    classification = "QUANTUM_SIMULATED" if is_quantum else "CLASSICAL"
    confidence = payload["superdense_channel"]["fidelity"] if payload["superdense_channel"] else 1.0

    contract = ComputationExecutionContract(
        producer_type=producer_type,
        producer_id=effective_producer,
        payload=payload,
        confidence=confidence,
        trace_id=effective_trace_id,
        contract_version="2.0.0",
        execution_constraints={
            "workstream": "WS-C",
            "provider": "PHOTONIC_SYSTEMS",
            "truth_classification": "SIMULATED AND TESTED",
            "distance_km": distance_km,
            "qubit_frequency_ghz": qubit_frequency_ghz,
        },
        execution_classification=classification,
        execution_path="SIMULATED",
        timestamp=datetime.now(timezone.utc).isoformat(),
    )
    validate_contract(contract)

    signer = NodeSigner(node_id=effective_producer, node_role=producer_type)
    signed_contract = sign_contract(contract, signer)

    success, pipeline_response = harness.process_incoming_contract(
        signed_contract.to_dict(),
        signer.identity.public_key,
    )

    certificate = None
    if success:
        records = execution_history(harness.ledger, effective_trace_id)
        if records:
            certificate = execution_certificate(records[-1], harness.ledger)

    return {
        "success": success,
        "trace_id": effective_trace_id,
        "producer_id": effective_producer,
        "producer_public_key": signer.identity.public_key,
        "signed_contract": signed_contract.to_dict(),
        "pipeline_response": pipeline_response,
        "certificate": certificate,
    }

