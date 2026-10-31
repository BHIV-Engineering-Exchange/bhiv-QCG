"""
tests/test_photonics_rf_systems.py
==================================
Unit and Integration Tests for Workstream C (WS-C):
- Remediated Superdense Coding Protocol (BLK-QCG-001)
- Optical Link Budget & QBER Simulation (BLK-PHO-001)
- Cryogenic RF Attenuation Profiles & Thermal Photon Occupancy
- Architectural Taxonomy & Operational Boundaries
"""

import pytest
from photonics_rf_systems.superdense_coding import (
    create_superdense_circuit,
    simulate_superdense_message,
    run_comprehensive_superdense_verification,
    SUPERDENSE_GATE_MAPPING,
)
from photonics_rf_systems.optical_link_budget import (
    OpticalFiberParameters,
    SinglePhotonDetectorParameters,
    calculate_optical_link_budget,
    sweep_optical_link_budget,
)
from photonics_rf_systems.cryogenic_rf_attenuation import (
    calculate_thermal_photon_occupation,
    simulate_cryogenic_attenuation_chain,
    CryogenicRFLineModel,
)
from photonics_rf_systems.architectural_taxonomy import (
    validate_optical_technology_boundary,
    OpticalTechnologyParadigm,
)


class TestSuperdenseCodingRemediation:
    """Verifies that all 4 classical 2-bit vectors produce 100% fidelity on AerSimulator."""

    @pytest.mark.parametrize("msg,expected_gates", [
        ("00", []),
        ("01", ["z"]),
        ("10", ["x"]),
        ("11", ["x", "z"]),
    ])
    def test_superdense_gate_mapping(self, msg, expected_gates):
        assert SUPERDENSE_GATE_MAPPING[msg] == expected_gates

    @pytest.mark.parametrize("msg", ["00", "01", "10", "11"])
    def test_superdense_message_simulation_fidelity(self, msg):
        res = simulate_superdense_message(msg, shots=500, seed=42)
        assert res["verified"] is True
        assert res["decoded_dominant"] == msg
        assert res["fidelity"] == 1.0
        assert res["counts"].get(msg) == 500

    def test_comprehensive_superdense_verification(self):
        report = run_comprehensive_superdense_verification(shots=250)
        assert report["all_vectors_passed"] is True
        for msg in ["00", "01", "10", "11"]:
            assert report["vector_results"][msg]["fidelity"] == 1.0


class TestOpticalLinkBudget:
    """Tests the fiber link budget and QBER threshold calculations."""

    def test_zero_distance_qber(self):
        res = calculate_optical_link_budget(0.0)
        assert res.attenuation_db == 0.0
        assert res.transmission_prob == 1.0
        assert res.qber_percentage < 0.001
        assert res.within_security_threshold is True

    def test_fifty_km_qber(self):
        res = calculate_optical_link_budget(50.0)
        assert res.attenuation_db == 10.0
        assert pytest.approx(res.transmission_prob, rel=1e-3) == 0.10
        # QBER at 50 km should be well below 11%
        assert res.qber_percentage < 1e-4
        assert res.within_security_threshold is True

    def test_sixty_km_threshold_criterion(self):
        # Criterion C2: QBER < 11% up to at least 60 km
        res = calculate_optical_link_budget(60.0)
        assert res.qber_percentage < 11.0
        assert res.within_security_threshold is True

    def test_distance_sweep_monotonic_loss(self):
        sweep = sweep_optical_link_budget(max_distance_km=100.0, step_km=10.0)
        assert len(sweep) == 11
        for i in range(len(sweep) - 1):
            assert sweep[i].attenuation_db < sweep[i + 1].attenuation_db
            assert sweep[i].transmission_prob > sweep[i + 1].transmission_prob
            assert sweep[i].qber_percentage <= sweep[i + 1].qber_percentage


class TestCryogenicRFAttenuation:
    """Tests thermal photon occupancy and the 50 dB attenuation cascade."""

    def test_room_temperature_thermal_occupancy(self):
        n_th = calculate_thermal_photon_occupation(300.0, frequency_ghz=5.0)
        # Should be approximately 1250 photons
        assert 1200.0 < n_th < 1300.0

    def test_base_plate_equilibrium_thermal_occupancy(self):
        n_th = calculate_thermal_photon_occupation(0.010, frequency_ghz=5.0)
        # Deep quantum regime: n_th << 1e-3
        assert n_th < 1e-10

    def test_cryogenic_attenuation_chain_ground_state(self):
        model = CryogenicRFLineModel(qubit_frequency_ghz=5.0)
        sim = simulate_cryogenic_attenuation_chain(model)
        assert sim["total_line_attenuation_db"] == 50.0
        assert sim["is_ground_state_preserved"] is True
        assert sim["base_plate_equilibrium_n_th"] < 1e-3


class TestArchitecturalTaxonomy:
    """Verifies operational boundary separating classical photonics from quantum optics."""

    def test_classical_photonic_cannot_claim_quantum_advantage(self):
        dec = validate_optical_technology_boundary("SILICON_PHOTONIC_MZI_MESH")
        assert dec["paradigm"] == OpticalTechnologyParadigm.CLASSICAL_ANALOG_PHOTONICS
        assert dec["quantum_advantage_claim"] is False
        assert dec["entanglement_present"] is False

    def test_superdense_true_quantum_optics(self):
        dec = validate_optical_technology_boundary("SUPERDENSE_CODING_OPTICAL_LINK")
        assert dec["paradigm"] == OpticalTechnologyParadigm.TRUE_QUANTUM_LINEAR_OPTICS
        assert dec["quantum_advantage_claim"] is True
        assert dec["entanglement_present"] is True

