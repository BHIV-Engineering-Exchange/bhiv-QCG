"""
photonics_rf_systems.architectural_taxonomy
===========================================
Formal Architectural Taxonomy & Operational Boundary Doctrine.
Separates Classical Analog Photonics from True Quantum Linear Optics (LOQC).

Doctrine Statement:
-------------------
Silicon photonic integrated circuits that perform coherent optical matrix-vector
multiplication (e.g., using Mach-Zehnder Interferometer meshes with continuous-wave lasers)
are CLASSICAL ANALOG ACCELERATORS. They operate in the high-photon-number limit (|alpha|^2 >> 1)
where quantum fluctuations are negligible and non-unitary measurement backaction does not occur.

TRUE QUANTUM LINEAR OPTICS (LOQC):
Operates in the discrete single-photon Fock state regime (|n=0>, |n=1>) or continuous-variable
non-classical squeezed state regime. It requires non-classical Hong-Ou-Mandel interference,
entanglement generation, non-linear conditional measurements, and quantum state tomography.
"""

from enum import Enum
from typing import Dict, Any, List


class OpticalTechnologyParadigm(str, Enum):
    CLASSICAL_ANALOG_PHOTONICS = "CLASSICAL_ANALOG_PHOTONICS"
    TRUE_QUANTUM_LINEAR_OPTICS = "TRUE_QUANTUM_LINEAR_OPTICS"


TAXONOMY_DECLARATIONS: Dict[str, Dict[str, Any]] = {
    "SILICON_PHOTONIC_MZI_MESH": {
        "paradigm": OpticalTechnologyParadigm.CLASSICAL_ANALOG_PHOTONICS,
        "carrier_state": "Continuous-wave classical laser light (coherent state |alpha>, |alpha|^2 >> 10^6)",
        "governing_physics": "Classical Maxwell equations & wave interference",
        "computational_primitive": "Matrix-Vector Multiplications (GEMM) via linear phase shifting",
        "quantum_advantage_claim": False,
        "is_quantum_state_prepared": False,
        "entanglement_present": False,
        "non_unitary_measurement": False,
    },
    "SUPERDENSE_CODING_OPTICAL_LINK": {
        "paradigm": OpticalTechnologyParadigm.TRUE_QUANTUM_LINEAR_OPTICS,
        "carrier_state": "Entangled Bell pair states (|Phi+> = (|00> + |11>) / sqrt(2))",
        "governing_physics": "Quantum electrodynamics, non-local quantum state projection",
        "computational_primitive": "Superdense 2-bit classical transmission per entangled qubit",
        "quantum_advantage_claim": True,
        "is_quantum_state_prepared": True,
        "entanglement_present": True,
        "non_unitary_measurement": True,
    },
    "QKD_SINGLE_PHOTON_LINK": {
        "paradigm": OpticalTechnologyParadigm.TRUE_QUANTUM_LINEAR_OPTICS,
        "carrier_state": "Single-photon Fock states (|1>) / attenuated coherent pulses (mu << 1)",
        "governing_physics": "No-cloning theorem, Heisenberg uncertainty principle",
        "computational_primitive": "Unconditionally secure cryptographic key expansion",
        "quantum_advantage_claim": True,
        "is_quantum_state_prepared": True,
        "entanglement_present": True,
        "non_unitary_measurement": True,
    },
}


def validate_optical_technology_boundary(technology_name: str) -> Dict[str, Any]:
    """
    Validates that a proposed technology is strictly classified and does not falsely
    claim quantum capability for classical photonic matrix multiplication.
    """
    if technology_name not in TAXONOMY_DECLARATIONS:
        raise ValueError(f"Unknown technology '{technology_name}'. Registered: {list(TAXONOMY_DECLARATIONS.keys())}")

    declaration = TAXONOMY_DECLARATIONS[technology_name]
    paradigm = declaration["paradigm"]

    if paradigm == OpticalTechnologyParadigm.CLASSICAL_ANALOG_PHOTONICS:
        assert declaration["quantum_advantage_claim"] is False, (
            "Violated Operational Boundary: Classical analog photonics cannot claim quantum advantage."
        )

    return declaration

