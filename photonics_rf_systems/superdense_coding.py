"""
photonics_rf_systems.superdense_coding
======================================
Remediated Superdense Coding Protocol Engine (BLK-QCG-001 Fix).

Physical & Mathematical Foundations:
------------------------------------
Superdense coding allows Alice to transmit two classical bits (b1 b0) to Bob
by transmitting a single qubit of an entangled Bell pair:
    |Phi+> = (|00> + |11>) / sqrt(2)

Qiskit Measurement Ordering (Little-Endian):
    In Qiskit, measuring qubit 0 into classical bit 0 and qubit 1 into classical bit 1
    yields a classical register bitstring formatted as:
        Bitstring = "c[1] c[0]"
    where:
        c[0] = measurement outcome of q0 (LSB)
        c[1] = measurement outcome of q1 (MSB)

Alice's Local Pauli Encoding on q0:
    - Input "00": Apply I(q0)
        State remains: |Phi+> = (|00> + |11>) / sqrt(2)
        Bob's Bell measurement: CX(q0, q1) -> H(q0)
        CX(|00> + |11>) = |00> + |10> = (|0> + |1>)_0 |0>_1 = |+>_0 |0>_1
        H(|+>_0) = |0>_0
        State becomes |0>_0 |0>_1.
        Measurement: q0 -> c[0]=0, q1 -> c[1]=0. Output bitstring: "00".

    - Input "01": Apply Z(q0)
        State transforms to: |Phi-> = (|00> - |11>) / sqrt(2)
        CX(|00> - |11>) = |00> - |10> = (|0> - |1>)_0 |0>_1 = |->_0 |0>_1
        H(|->_0) = |1>_0
        State becomes |1>_0 |0>_1.
        Measurement: q0 -> c[0]=1, q1 -> c[1]=0. Output bitstring: "01".

    - Input "10": Apply X(q0)
        State transforms to: |Psi+> = (|10> + |01>) / sqrt(2)
        CX(|10> + |01>) = |11> + |01> = (|1> + |0>)_0 |1>_1 = |+>_0 |1>_1
        H(|+>_0) = |0>_0
        State becomes |0>_0 |1>_1.
        Measurement: q0 -> c[0]=0, q1 -> c[1]=1. Output bitstring: "10".

    - Input "11": Apply X(q0) followed by Z(q0) (or iY)
        State transforms to: -|Psi-> = (|01> - |10>) / sqrt(2)
        CX(|01> - |10>) = |01> - |11> = (|0> - |1>)_0 |1>_1 = |->_0 |1>_1
        H(|->_0) = |1>_0
        State becomes |1>_0 |1>_1.
        Measurement: q0 -> c[0]=1, q1 -> c[1]=1. Output bitstring: "11".
"""

from typing import Dict, List, Any, Tuple
from qiskit import QuantumCircuit
from qiskit_aer import AerSimulator

BELL_STATE_PHI_PLUS = "(|00> + |11>) / sqrt(2)"

SUPERDENSE_GATE_MAPPING: Dict[str, List[str]] = {
    "00": [],
    "01": ["z"],
    "10": ["x"],
    "11": ["x", "z"],
}


def create_superdense_circuit(message_bits: str) -> QuantumCircuit:
    """
    Creates a 2-qubit Superdense Coding quantum circuit with exact little-endian alignment.

    Args:
        message_bits: Two-bit classical message ('00', '01', '10', '11')

    Returns:
        QuantumCircuit: 2-qubit, 2-classical-bit circuit ready for execution.
    """
    if message_bits not in SUPERDENSE_GATE_MAPPING:
        raise ValueError(f"Invalid message bits '{message_bits}'. Must be one of '00', '01', '10', '11'.")

    qc = QuantumCircuit(2, 2, name=f"superdense_{message_bits}")

    # Step 1: Bell Pair Preparation on q0 (Alice) and q1 (Bob)
    qc.h(0)
    qc.cx(0, 1)
    qc.barrier(label="Bell Pair Ready")

    # Step 2: Alice's Local Encoding on q0
    gates = SUPERDENSE_GATE_MAPPING[message_bits]
    for g in gates:
        getattr(qc, g)(0)
    qc.barrier(label=f"Alice Encoded '{message_bits}'")

    # Step 3: Bob's Bell State Measurement Decoding
    # CX with control=q0, target=q1, followed by Hadamard on q0
    qc.cx(0, 1)
    qc.h(0)
    qc.barrier(label="Bob Decoded")

    # Step 4: Measurement into classical register
    # q0 -> c[0] (LSB), q1 -> c[1] (MSB)
    qc.measure([0, 1], [0, 1])

    return qc


def simulate_superdense_message(
    message_bits: str,
    shots: int = 1000,
    seed: int = 42
) -> Dict[str, Any]:
    """
    Simulates transmission of a superdense message using AerSimulator.

    Args:
        message_bits: Two-bit message ('00', '01', '10', '11')
        shots: Number of Monte Carlo measurement shots
        seed: Random seed for reproducibility

    Returns:
        Dict containing message, counts, decoded_dominant, and fidelity.
    """
    qc = create_superdense_circuit(message_bits)
    simulator = AerSimulator()
    job = simulator.run(qc, shots=shots, seed_simulator=seed)
    counts = dict(job.result().get_counts())

    dominant_bitstring = max(counts, key=counts.get)
    correct_shots = counts.get(message_bits, 0)
    fidelity = correct_shots / shots

    return {
        "input_message": message_bits,
        "encoded_gates_on_q0": SUPERDENSE_GATE_MAPPING[message_bits],
        "shots_requested": shots,
        "counts": counts,
        "decoded_dominant": dominant_bitstring,
        "fidelity": fidelity,
        "verified": (dominant_bitstring == message_bits and fidelity == 1.0),
    }


def run_comprehensive_superdense_verification(shots: int = 1000) -> Dict[str, Any]:
    """
    Runs full protocol verification across all 4 classical 2-bit vectors.
    """
    results = {}
    all_passed = True

    for msg in ["00", "01", "10", "11"]:
        res = simulate_superdense_message(msg, shots=shots)
        results[msg] = res
        if not res["verified"]:
            all_passed = False

    return {
        "protocol": "Superdense Coding (Remediated BLK-QCG-001)",
        "all_vectors_passed": all_passed,
        "shots_per_vector": shots,
        "vector_results": results,
    }

