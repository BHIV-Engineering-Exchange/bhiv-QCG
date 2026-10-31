#!/usr/bin/env python3
"""
test_qcg_provenance.py — Cryptographic Provenance & Merkle Ledger Test Suite

Workstream D: Mechatronics, Instrumentation & Retained Cryptographic Provenance
Accountable Owner: Pritesh Patra (Lead Instrumentation Engineer & Cryptographic Provenance Architect)
Programme Identifier: BHQ-INFRA-001 (WS-D)
Subsystem: bhiv-QCG Cryptographic Provenance Engine
Remediates: BLK-QCG-003 (Provenance Integration Test Absence)

Test Objectives:
1. Generate ECDSA P-256 keypair and export PEM public key.
2. Sign 100 sequential quantum circuit execution records.
3. Verify 100% of ECDSA signatures against the public key.
4. Append 100 execution records sequentially into the pairwise SHA-256 EvidenceLedger.
5. Verify cryptographic chain continuity and compute deterministic Merkle root.
6. Perform single-bit tamper mutation test on a historical record (#42):
   - Assert signature verification failure on tampered payload.
   - Assert Merkle root invalidation (H_tampered != H_root).
   - Assert chain verification rejection on altered history.
7. Export comprehensive test log to evidence/02_PRITESH_PROVENANCE_TEST.json.
"""

from __future__ import annotations

import copy
import hashlib
import json
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

import pytest

# Ensure workspace root is in sys.path
WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

from node_signer import NodeSigner, NodeProof, verify_node_proof
from evidence_ledger import EvidenceLedger, LedgerSnapshot
from execution_record import ExecutionRecord


# ============================================================================
# HELPER / FIXTURE DATA GENERATOR
# ============================================================================

def generate_circuit_job_payload(sequence: int, trace_id: str) -> Dict[str, Any]:
    """Generates a realistic quantum circuit execution payload for job #sequence."""
    # Deterministic pseudo-circuit parameters
    qubit_count = 5 + (sequence % 20)  # 5 to 24 qubits
    circuit_depth = 12 + (sequence * 3) % 40
    shots = 4096
    
    # Canonical circuit representation hash
    circuit_repr = f"OPENQASM 2.0; qreg q[{qubit_count}]; creg c[{qubit_count}]; seq={sequence};"
    circuit_hash = hashlib.sha256(circuit_repr.encode("utf-8")).hexdigest()
    
    # Simulated execution metrics
    runtime_hash = hashlib.sha256(f"{circuit_hash}:shots={shots}:seq={sequence}".encode("utf-8")).hexdigest()
    
    return {
        "job_id": f"BHQ-JOB-2026-QPU-{sequence:04d}",
        "trace_id": trace_id,
        "execution_sequence": sequence,
        "circuit_name": f"transmon_dispersive_readout_seq_{sequence:04d}",
        "qubit_count": qubit_count,
        "circuit_depth": circuit_depth,
        "shots": shots,
        "circuit_hash": circuit_hash,
        "runtime_hash": runtime_hash,
        "execution_status": "COMPLETED_OPTIMAL",
        "timestamp": f"2026-10-31T14:{sequence % 60:02d}:00Z",
    }


# ============================================================================
# CORE TEST RUNNER & VERIFICATION LOGIC
# ============================================================================

def run_provenance_verification_suite(
    record_count: int = 100,
    tamper_index: int = 42,
) -> Dict[str, Any]:
    """
    Executes the full 100-job cryptographic provenance and Merkle tamper-detection run.
    Returns the comprehensive verification results dictionary.
    """
    results: Dict[str, Any] = {
        "test_suite_id": "BHQ-TEST-PROV-001",
        "subsystem": "bhiv-QCG Cryptographic Provenance Engine",
        "owner": "Pritesh Patra (Lead Instrumentation Engineer & Cryptographic Provenance Architect)",
        "remediates_blocker": "BLK-QCG-003",
        "executed_at": datetime.now(timezone.utc).isoformat(),
        "total_jobs_tested": record_count,
        "tamper_test_index": tamper_index,
    }

    # 1. Keypair Generation & Identity Setup
    signer = NodeSigner(
        node_id="BHQ_QPU_INSTRUMENTATION_NODE_01",
        node_role="INSTRUMENTATION_READOUT_ENGINE",
        version="1.1.0",
    )
    public_key_pem = signer.get_public_key_pem()
    public_key_hex = signer.public_key_hex

    results["node_identity"] = {
        "node_id": signer.node_id,
        "public_key_hex": public_key_hex,
        "public_key_pem": public_key_pem,
        "curve": "secp256r1 (ECDSA P-256)",
    }

    # 2. Batch Execution & Signing
    ledger = EvidenceLedger()
    signed_entries: List[Dict[str, Any]] = []
    signatures_verified_count = 0

    current_head = hashlib.sha256(b"GENESIS").hexdigest()

    for seq in range(1, record_count + 1):
        trace_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"bhq.qpu.job.{seq}"))
        payload = generate_circuit_job_payload(seq, trace_id)
        
        # Sign payload using ECDSA P-256
        proof = signer.sign_payload(payload)

        # Immediate cryptographic verification
        is_valid_sig = verify_node_proof(proof, public_key_hex, payload)
        if is_valid_sig:
            signatures_verified_count += 1
        else:
            raise AssertionError(f"Signature verification failed at sequence {seq}!")

        # Create ExecutionRecord bound to proof hash
        execution_record = ExecutionRecord(
            execution_id=payload["job_id"],
            trace_id=trace_id,
            replay_reference=f"REPLAY-REF-{seq:04d}",
            execution_sequence=seq,
            producer_identity=signer.node_id,
            runtime_identity="BHIV_CRYOGENIC_QPU_WS_D",
            governance_identity="GC_TANTRA_SOVEREIGN",
            execution_status="OK",
            runtime_hash=payload["runtime_hash"],
            execution_hash=proof.signed_hash,
            previous_execution_hash=current_head,
            execution_root_hash="",  # Updated by ledger Merkle root
            schema_version="2.0.0",
        )

        # Append to Evidence Ledger
        snapshot = ledger.append(execution_record)
        current_head = snapshot.latest_evidence_hash

        # Store entry log
        signed_entries.append({
            "sequence": seq,
            "job_id": payload["job_id"],
            "trace_id": trace_id,
            "signed_hash": proof.signed_hash,
            "signature_der_hex": proof.signature,
            "verified": is_valid_sig,
            "chain_head": current_head,
            "payload": payload,
        })

    canonical_merkle_root = ledger.get_merkle_root()
    chain_valid = ledger.verify_chain()

    results["batch_signing_summary"] = {
        "records_generated": record_count,
        "signatures_verified_count": signatures_verified_count,
        "signature_verification_rate": (signatures_verified_count / record_count) * 100.0,
        "chain_integrity_verified": chain_valid,
        "final_sequence_length": len(ledger._records),
        "final_chain_head": current_head,
        "canonical_merkle_root": canonical_merkle_root,
    }

    # 3. Determinism Replay Verification
    # Rebuilding ledger from identical records must yield identical Merkle root
    replay_ledger = EvidenceLedger()
    replay_head = hashlib.sha256(b"GENESIS").hexdigest()
    for rec in ledger._records:
        rec_copy = ExecutionRecord(
            execution_id=rec.execution_id,
            trace_id=rec.trace_id,
            replay_reference=rec.replay_reference,
            execution_sequence=rec.execution_sequence,
            producer_identity=rec.producer_identity,
            runtime_identity=rec.runtime_identity,
            governance_identity=rec.governance_identity,
            execution_status=rec.execution_status,
            runtime_hash=rec.runtime_hash,
            execution_hash=rec.execution_hash,
            previous_execution_hash=replay_head,
            execution_root_hash="",
            schema_version=rec.schema_version,
        )
        s = replay_ledger.append(rec_copy)
        replay_head = s.latest_evidence_hash

    replay_merkle_root = replay_ledger.get_merkle_root()
    determinism_match = (canonical_merkle_root == replay_merkle_root)
    results["determinism_verification"] = {
        "canonical_root": canonical_merkle_root,
        "replay_root": replay_merkle_root,
        "deterministic_match": determinism_match,
    }

    # 4. Tamper Detection Test (Single-Bit Mutation on Target Record)
    target_entry = signed_entries[tamper_index - 1]
    original_payload = target_entry["payload"]
    original_proof = NodeProof(
        node_id=signer.node_id,
        signature=target_entry["signature_der_hex"],
        signed_hash=target_entry["signed_hash"],
    )

    # Mutate a single field / bit in the historical payload: change shots 4096 -> 4097
    tampered_payload = copy.deepcopy(original_payload)
    tampered_payload["shots"] = 4097  # Single integer change altering SHA-256 hash completely

    # Test 4A: Signature verification on tampered payload must return False
    tampered_sig_valid = verify_node_proof(original_proof, public_key_hex, tampered_payload)

    # Test 4B: Recompute tampered hash and evaluate Merkle tree divergence
    tampered_str = json.dumps(tampered_payload, sort_keys=True, default=str)
    tampered_hash = hashlib.sha256(tampered_str.encode("utf-8")).hexdigest()

    tampered_ledger = EvidenceLedger()
    t_head = hashlib.sha256(b"GENESIS").hexdigest()
    for idx, rec in enumerate(ledger._records):
        exec_hash = tampered_hash if (idx == tamper_index - 1) else rec.execution_hash
        t_rec = ExecutionRecord(
            execution_id=rec.execution_id,
            trace_id=rec.trace_id,
            replay_reference=rec.replay_reference,
            execution_sequence=rec.execution_sequence,
            producer_identity=rec.producer_identity,
            runtime_identity=rec.runtime_identity,
            governance_identity=rec.governance_identity,
            execution_status=rec.execution_status,
            runtime_hash=rec.runtime_hash,
            execution_hash=exec_hash,
            previous_execution_hash=t_head,
            execution_root_hash="",
            schema_version=rec.schema_version,
        )
        s = tampered_ledger.append(t_rec)
        t_head = s.latest_evidence_hash

    tampered_merkle_root = tampered_ledger.get_merkle_root()
    merkle_divergence_detected = (canonical_merkle_root != tampered_merkle_root)

    # Test 4C: Direct payload tamper detection inside original ledger chain
    # Mutating an in-memory record's execution_hash directly invalidates verify_chain()
    in_memory_tamper_ledger = EvidenceLedger()
    for rec in ledger._records:
        in_memory_tamper_ledger._records.append(rec)
    in_memory_tamper_ledger._evidence_hashes = list(ledger._evidence_hashes)
    in_memory_tamper_ledger._current_head = ledger._current_head
    
    # Mutate record 42's execution hash in-place
    tampered_record = ExecutionRecord(
        execution_id=ledger._records[tamper_index - 1].execution_id,
        trace_id=ledger._records[tamper_index - 1].trace_id,
        replay_reference=ledger._records[tamper_index - 1].replay_reference,
        execution_sequence=ledger._records[tamper_index - 1].execution_sequence,
        producer_identity=ledger._records[tamper_index - 1].producer_identity,
        runtime_identity=ledger._records[tamper_index - 1].runtime_identity,
        governance_identity=ledger._records[tamper_index - 1].governance_identity,
        execution_status=ledger._records[tamper_index - 1].execution_status,
        runtime_hash=ledger._records[tamper_index - 1].runtime_hash,
        execution_hash=tampered_hash,  # Altered!
        previous_execution_hash=ledger._records[tamper_index - 1].previous_execution_hash,
        execution_root_hash="",
        schema_version="2.0.0",
    )
    in_memory_tamper_ledger._records[tamper_index - 1] = tampered_record
    chain_tamper_detected = not in_memory_tamper_ledger.verify_chain()

    results["tamper_detection_evidence"] = {
        "tampered_job_id": target_entry["job_id"],
        "tamper_mutation": "Payload field 'shots' modified: 4096 -> 4097 (1-bit data mutation)",
        "original_payload_hash": target_entry["signed_hash"],
        "tampered_payload_hash": tampered_hash,
        "signature_verification_on_tampered_payload": "REJECTED (False)" if not tampered_sig_valid else "FAILED_TO_DETECT",
        "canonical_merkle_root": canonical_merkle_root,
        "tampered_merkle_root": tampered_merkle_root,
        "merkle_root_divergence_detected": merkle_divergence_detected,
        "chain_verification_tamper_detected": chain_tamper_detected,
        "tamper_proof_passed": (not tampered_sig_valid) and merkle_divergence_detected and chain_tamper_detected,
    }

    # 5. Acceptance Evaluation (Criterion D3)
    criterion_d3_passed = (
        signatures_verified_count == record_count
        and chain_valid
        and determinism_match
        and (not tampered_sig_valid)
        and merkle_divergence_detected
        and chain_tamper_detected
    )

    results["acceptance_criteria"] = {
        "Criterion_D3_Cryptographic_Provenance": {
            "requirement": "Cryptographic provenance unit tests achieve 100% pass rate: ECDSA P-256 signatures verify and Merkle tree detects single-bit data tampering",
            "signatures_tested": record_count,
            "signatures_passed": signatures_verified_count,
            "merkle_tamper_detected": merkle_divergence_detected,
            "chain_tamper_detected": chain_tamper_detected,
            "passed": criterion_d3_passed,
        }
    }

    results["signed_execution_log"] = signed_entries
    return results


# ============================================================================
# PYTEST TEST FUNCTIONS
# ============================================================================

def test_ecdsa_keypair_generation():
    signer = NodeSigner(node_id="TEST_NODE")
    assert signer.node_id == "TEST_NODE"
    assert len(signer.public_key_hex) > 64
    assert "-----BEGIN PUBLIC KEY-----" in signer.get_public_key_pem()


def test_100_record_signing_and_merkle_provenance():
    results = run_provenance_verification_suite(record_count=100, tamper_index=42)
    assert results["acceptance_criteria"]["Criterion_D3_Cryptographic_Provenance"]["passed"] is True
    assert results["batch_signing_summary"]["signatures_verified_count"] == 100
    assert results["batch_signing_summary"]["chain_integrity_verified"] is True
    assert results["determinism_verification"]["deterministic_match"] is True


def test_single_bit_tamper_detection():
    results = run_provenance_verification_suite(record_count=50, tamper_index=25)
    evidence = results["tamper_detection_evidence"]
    assert evidence["tamper_proof_passed"] is True
    assert evidence["merkle_root_divergence_detected"] is True
    assert evidence["chain_verification_tamper_detected"] is True


# ============================================================================
# CLI MAIN FUNCTION & ARTIFACT EXPORT
# ============================================================================

def main() -> int:
    print("=" * 78)
    print("BHQ-INFRA-001 — Workstream D: Provenance & Merkle Ledger Test Suite")
    print("Owner: Pritesh Patra (Lead Instrumentation Engineer & Provenance Architect)")
    print("Subsystem: bhiv-QCG Cryptographic Provenance Engine")
    print("Remediates: BLK-QCG-003")
    print("=" * 78)

    print("\n[+] Generating ECDSA P-256 Keypair and Signing 100 Sequential Records...")
    results = run_provenance_verification_suite(record_count=100, tamper_index=42)

    summary = results["batch_signing_summary"]
    tamper = results["tamper_detection_evidence"]
    d3 = results["acceptance_criteria"]["Criterion_D3_Cryptographic_Provenance"]

    print(f"[+] Signatures Verified:        {summary['signatures_verified_count']} / {results['total_jobs_tested']} (100.0%)")
    print(f"[+] Chain Integrity:            {'VALID' if summary['chain_integrity_verified'] else 'INVALID'}")
    print(f"[+] Canonical Merkle Root:      {summary['canonical_merkle_root']}")
    print(f"[+] Determinism Replay Check:   {'PASS' if results['determinism_verification']['deterministic_match'] else 'FAIL'}")
    print(f"[+] Tampered Record Tested:     {tamper['tampered_job_id']}")
    print(f"[+] Signature on Tampered Data: {tamper['signature_verification_on_tampered_payload']}")
    print(f"[+] Merkle Root Divergence:     {'DETECTED (PASS)' if tamper['merkle_root_divergence_detected'] else 'FAIL'}")
    print(f"[+] Tampered Merkle Root:       {tamper['tampered_merkle_root']}")
    print(f"[+] Chain Alteration Rejected:  {'CONFIRMED (PASS)' if tamper['chain_verification_tamper_detected'] else 'FAIL'}")
    print(f"\n[+] Criterion D3 Overall:       {'PASS (100%)' if d3['passed'] else 'FAIL'}")

    if not d3["passed"]:
        print("\n[!] FATAL: Criterion D3 verification failed!", file=sys.stderr)
        return 1

    # Export canonical deliverable: evidence/02_PRITESH_PROVENANCE_TEST.json
    workspace_root = Path(__file__).resolve().parent.parent
    primary_target = workspace_root / "evidence" / "02_PRITESH_PROVENANCE_TEST.json"
    alignment_target = workspace_root / "BHQ_INFRA_001_PROGRAMME_ALIGNMENT" / "evidence" / "02_PRITESH_PROVENANCE_TEST.json"

    primary_target.parent.mkdir(parents=True, exist_ok=True)
    with open(primary_target, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"\n[SUCCESS] Primary Artifact Exported:    {primary_target}")

    alignment_target.parent.mkdir(parents=True, exist_ok=True)
    with open(alignment_target, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"[SUCCESS] Alignment Artifact Exported:  {alignment_target}")

    print("\n[SUCCESS] Step 2 Successfully Complete: BLK-QCG-003 Remediated.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

