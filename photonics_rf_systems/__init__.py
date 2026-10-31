"""
photonics_rf_systems - Workstream C (WS-C)
Photonics, Electromagnetics, RF Systems & Retained QCG Gateway Protocols
BHQ-INFRA-001 Sovereign Quantum Programme
"""

from .superdense_coding import (
    create_superdense_circuit,
    simulate_superdense_message,
    run_comprehensive_superdense_verification,
    BELL_STATE_PHI_PLUS,
    SUPERDENSE_GATE_MAPPING,
)
from .optical_link_budget import (
    OpticalFiberParameters,
    SinglePhotonDetectorParameters,
    OpticalLinkBudgetResult,
    calculate_optical_link_budget,
    sweep_optical_link_budget,
    export_link_budget_csv,
)
from .cryogenic_rf_attenuation import (
    CryogenicTemperatureStage,
    CryogenicRFLineModel,
    calculate_thermal_photon_occupation,
    simulate_cryogenic_attenuation_chain,
)
from .architectural_taxonomy import (
    validate_optical_technology_boundary,
    TAXONOMY_DECLARATIONS,
)

__all__ = [
    "create_superdense_circuit",
    "simulate_superdense_message",
    "run_comprehensive_superdense_verification",
    "BELL_STATE_PHI_PLUS",
    "SUPERDENSE_GATE_MAPPING",
    "OpticalFiberParameters",
    "SinglePhotonDetectorParameters",
    "OpticalLinkBudgetResult",
    "calculate_optical_link_budget",
    "sweep_optical_link_budget",
    "export_link_budget_csv",
    "CryogenicTemperatureStage",
    "CryogenicRFLineModel",
    "calculate_thermal_photon_occupation",
    "simulate_cryogenic_attenuation_chain",
    "validate_optical_technology_boundary",
    "TAXONOMY_DECLARATIONS",
]

