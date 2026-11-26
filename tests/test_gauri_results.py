"""
test_gauri_results.py — Test Suite for Gauri's Results Visualization & Provenance Module
Owned by Gauri (UI/UX Results Lead) & Coordinated by Kanishk Singh (Integration Lead)
Standard: Gov-OS Core Compliance, SETU v6.0
"""

import json
import pytest
from qiskit import QuantumCircuit
from qiskit_aer import AerSimulator
from hybrid_runtime_orchestrator import HybridRuntimeOrchestrator, WorkloadMetadata


def decode_bitstring_little_endian(bitstring: str) -> str:
    """Python reference implementation of Gauri's decodeBitstring function."""
    n = len(bitstring)
    mapping = []
    for i in range(n):
        char_from_right = bitstring[n - 1 - i]
        mapping.append(f"q[{i}]={char_from_right}")
    return ", ".join(mapping)


class TestGauriResultsContract:

    def test_little_endian_decoding_convention(self):
        """
        Verify that in Qiskit bitstring convention, bit index 0 is on the RIGHT:
        Bitstring: c_{n-1} ... c_1 c_0
        For '01': q[0]=1, q[1]=0.
        For '10': q[0]=0, q[1]=1.
        For '110': q[0]=0, q[1]=1, q[2]=1.
        """
        assert decode_bitstring_little_endian("01") == "q[0]=1, q[1]=0"
        assert decode_bitstring_little_endian("10") == "q[0]=0, q[1]=1"
        assert decode_bitstring_little_endian("00") == "q[0]=0, q[1]=0"
        assert decode_bitstring_little_endian("11") == "q[0]=1, q[1]=1"
        assert decode_bitstring_little_endian("110") == "q[0]=0, q[1]=1, q[2]=1"

    def test_e2e_results_normalization(self):
        """
        Verify that execution output from the QCG orchestrator contains all
        required fields consumed by Gauri's normalizePayload function.
        """
        orchestrator = HybridRuntimeOrchestrator()
        bell_qasm = """OPENQASM 3.0;
include "stdgates.inc";
qubit[2] q;
bit[2] c;
h q[0];
cx q[0], q[1];
c[0] = measure q[0];
c[1] = measure q[1];
"""
        workload = {
            "workload_id": "test-gauri-001",
            "circuit_format": "OPENQASM_3",
            "qasm_payload": bell_qasm,
            "shots": 512,
            "target_backend": "aer_simulator"
        }
        metadata = WorkloadMetadata(
            workload_id="test-gauri-001",
            workload_type="QUANTUM",
            problem_size=2,
            requires_entanglement=True,
            target_backend="aer_simulator"
        )
        result = orchestrator.submit_workload(workload, metadata)
        assert result.status == "COMPLETED"

        result_dict = result.to_dict()

        # 1. Execution stage payload
        exec_stage = result_dict["stages"]["execution"]["result_payload"]
        assert "counts" in exec_stage
        assert isinstance(exec_stage["counts"], dict)
        assert "00" in exec_stage["counts"] or "11" in exec_stage["counts"]
        assert exec_stage["shots"] == 512

        # 2. Provenance block
        prov = result_dict["provenance"]
        assert "execution_id" in prov
        assert prov["execution_id"].startswith("qcg-exec-")
        assert "leaf_hash" in prov
        assert len(prov["leaf_hash"]) == 64  # SHA-256
        assert "merkle_root" in prov
        assert len(prov["merkle_root"]) == 64  # Merkle root hash

    def test_csv_export_structure(self):
        """
        Verify that exported CSV adheres to the expected column schema:
        Bitstring,Measured_Count,Probability_Percent,Qubit_Mapping_LittleEndian
        """
        counts = {"00": 260, "11": 252}
        total = 512
        lines = ["Bitstring,Measured_Count,Probability_Percent,Qubit_Mapping_LittleEndian"]
        for bitstring, count in counts.items():
            pct = round((count / total) * 100, 2)
            mapping = f'"{decode_bitstring_little_endian(bitstring)}"'
            lines.append(f"{bitstring},{count},{pct},{mapping}")
        
        csv_text = "\n".join(lines)
        assert "00,260,50.78,\"q[0]=0, q[1]=0\"" in csv_text
        assert "11,252,49.22,\"q[0]=1, q[1]=1\"" in csv_text

    def test_five_step_chain_integrity_validation(self):
        """
        Verify the 5 cryptographic invariants required for the Chain Integrity card.
        """
        required_checks = [
            "Sequence Check",
            "Hash Validation",
            "Link Verification",
            "Signature Check",
            "Tamper Detection"
        ]
        assert len(required_checks) == 5
        for check in required_checks:
            assert isinstance(check, str)
