"""
tests/test_ganesh_live_integration.py — Live Integration Test Suite for Ganesh's Quantum Application Layer

Validates:
1. Live / Simulated health check and capability discovery
2. Supported domain models: VANA, MARINE, UCCIS, AIAIC
3. Backend targets: aer_simulator (available), bhiv_runtime (correctly identified as blocked)
4. Workload creation & execution workflows
5. QCG Sovereign Bridge verification:
   - ComputationExecutionContract generation & schema validation
   - ECDSA P-256 signature verification via verify_node_proof
   - CanonicalReplayAuthority sequence ordering and duplicate detection
   - EvidenceLedger Merkle root calculation and chain integrity (verify_chain)
6. Graceful failure / offline fallback when network is unavailable
"""

import hashlib
import json
import os
import sys
import tempfile
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch, MagicMock

# Ensure project root is on sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ganesh_live_client import (
    GaneshClient,
    GaneshHealthResponse,
    GaneshCapabilitiesResponse,
    GaneshWorkloadRequest,
    GaneshWorkloadResponse,
    GaneshExecuteRequest,
    GaneshExecuteResponse,
    GaneshQCGBridgeResult,
    get_client,
)
from execution_contract import validate_contract, ContractValidationError
from node_identity import NodeSigner, verify_node_proof
from canonical_replay_authority import CanonicalReplayAuthority
from replay_registry import ReplayRegistry
from evidence_ledger import EvidenceLedger


class TestGaneshLiveIntegration(unittest.TestCase):
    """Test suite for Ganesh Quantum Application Layer client and QCG bridge."""

    def setUp(self):
        # Dedicated isolated registry & ledger for each test
        self.tmp_dir = tempfile.mkdtemp()
        self.replay_reg = ReplayRegistry(path=os.path.join(self.tmp_dir, "replay.json"))
        self.replay_auth = CanonicalReplayAuthority(registry=self.replay_reg)
        self.ledger = EvidenceLedger(persistence_path=os.path.join(self.tmp_dir, "ledger.json"))
        self.signer = NodeSigner(node_id="TEST-GANESH-NODE-001")
        self.client = GaneshClient(
            signer=self.signer,
            replay_authority=self.replay_auth,
            ledger=self.ledger,
        )

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_health_check_live_or_fallback(self):
        """Verify health check returns valid structure."""
        resp = self.client.health()
        self.assertIsInstance(resp, GaneshHealthResponse)
        self.assertIn(resp.status, ("HEALTHY", "OK", "UNREACHABLE"))
        self.assertTrue(len(resp.service) > 0)

    def test_capabilities_parsing(self):
        """Verify capabilities parser extracts domains and backends correctly."""
        sample_caps = {
            "status": "HEALTHY",
            "service": "quantum-application-layer",
            "version": "0.1.0",
            "domains": [
                {"domain_id": "VANA", "display_title": "VANA Eco-Grid", "default_qubit_count": 6},
                {"domain_id": "MARINE", "display_title": "NW-53 Logistics", "default_qubit_count": 8},
                {"domain_id": "UCCIS", "display_title": "Urban Command Dispatch", "default_qubit_count": 9},
                {"domain_id": "AIAIC", "display_title": "Agmarknet Mandi Allocation", "default_qubit_count": 16},
            ],
            "backends": [
                {"backend_name": "aer_simulator", "status": "AVAILABLE", "max_qubits": 32},
                {"backend_name": "bhiv_runtime", "status": "BLOCKED", "max_qubits": 127},
            ],
        }

        with patch.object(self.client, "_request", return_value=(200, sample_caps)):
            caps = self.client.get_capabilities()
            self.assertEqual(caps.status, "HEALTHY")
            self.assertEqual(len(caps.domains), 4)
            self.assertEqual(len(caps.backends), 2)
            backend_names = [b["backend_name"] for b in caps.backends]
            self.assertIn("aer_simulator", backend_names)
            self.assertIn("bhiv_runtime", backend_names)

    def test_workload_creation_and_execution_simulation(self):
        """Verify workload registration and execution flows."""
        sample_workload = {
            "workload_id": "workload-vana-12345",
            "domain": "VANA",
            "problem_id": "PROB-VANA-001",
            "algorithm": "QAOA",
            "qubits_required": 6,
            "shots": 512,
            "status": "CREATED",
        }
        sample_execution = {
            "execution_id": "exec-vana-98765",
            "workload_id": "workload-vana-12345",
            "backend_target": "aer_simulator",
            "shots": 512,
            "status": "SUCCESS",
            "result": {
                "counts": {"000000": 120, "111111": 392},
                "probabilities": {"000000": 0.234, "111111": 0.766},
                "best_candidate": "111111",
            },
            "execution_time_ms": 42.5,
        }

        with patch.object(self.client, "_request") as mock_req:
            mock_req.side_effect = [
                (201, sample_workload),
                (200, sample_execution),
            ]

            w_req = GaneshWorkloadRequest(
                domain="VANA",
                problem_id="PROB-VANA-001",
                algorithm="QAOA",
                qubits_required=6,
                shots=512,
            )
            w_resp = self.client.create_workload(w_req)
            self.assertEqual(w_resp.workload_id, "workload-vana-12345")
            self.assertEqual(w_resp.status, "CREATED")

            e_req = GaneshExecuteRequest(backend_target="aer_simulator", shots=512)
            e_resp = self.client.execute_workload(w_resp.workload_id, e_req)
            self.assertEqual(e_resp.execution_id, "exec-vana-98765")
            self.assertEqual(e_resp.status, "SUCCESS")
            self.assertEqual(e_resp.best_candidate, "111111")
            self.assertIn("111111", e_resp.counts)

    def test_qcg_bridge_full_lifecycle(self):
        """
        Verify end-to-end QCG Sovereign bridging:
        - Contract creation & schema validation
        - NodeSigner ECDSA P-256 signature verification
        - CanonicalReplayAuthority sequence ordering
        - EvidenceLedger Merkle inclusion & chain integrity
        """
        w_resp = GaneshWorkloadResponse(
            workload_id="workload-marine-001",
            domain="MARINE",
            problem_id="NW-53-LOGISTICS",
            algorithm="QAOA",
            qubits_required=8,
            shots=1024,
            status="CREATED",
        )
        e_resp = GaneshExecuteResponse(
            execution_id="exec-marine-001",
            workload_id="workload-marine-001",
            backend_target="aer_simulator",
            shots=1024,
            status="SUCCESS",
            counts={"10101010": 750, "01010101": 274},
            probabilities={"10101010": 0.7324, "01010101": 0.2676},
            best_candidate="10101010",
            execution_time_ms=55.0,
        )

        bridge = self.client.bridge_to_qcg_contract(w_resp, e_resp)

        # 1. Contract validation
        self.assertIsInstance(bridge, GaneshQCGBridgeResult)
        validate_contract(bridge.contract)
        self.assertEqual(bridge.contract.producer_type, "QUANTUM")
        self.assertEqual(bridge.contract.execution_classification, "QUANTUM_SIMULATED")
        self.assertEqual(bridge.contract.execution_path, "SIMULATED")
        self.assertGreaterEqual(bridge.contract.confidence, 0.70)

        # 2. Cryptographic Node Signature verification
        pub_hex = self.signer.identity.public_key
        is_sig_valid = verify_node_proof(
            bridge.node_proof,
            pub_hex,
            payload=bridge.contract.to_dict(),
        )
        self.assertTrue(is_sig_valid, "NodeSigner ECDSA signature must verify successfully.")

        # 3. Canonical Replay Authority
        self.assertEqual(bridge.replay_verdict.status, "VALID")
        self.assertGreater(bridge.replay_verdict.sequence_number, 0)

        # Re-submitting identical payload must NOT be considered fresh/duplicate
        second_verdict = self.replay_auth.submit(
            message_id=bridge.contract.payload_hash,
            issued_at=None,
        )
        self.assertNotEqual(second_verdict.status, "VALID")

        # 4. Evidence Ledger & Merkle proof
        self.assertEqual(bridge.ledger_snapshot.sequence_length, 1)
        self.assertTrue(len(bridge.ledger_snapshot.merkle_root) == 64)
        self.assertTrue(self.ledger.verify_chain(), "Evidence chain must maintain full cryptographic integrity.")

    def test_all_four_domain_workloads_bridgeable(self):
        """Ensure all 4 target domains (VANA, MARINE, UCCIS, AIAIC) bridge cleanly."""
        domains = [
            ("VANA", "QAOA", 6),
            ("MARINE", "QAOA", 8),
            ("UCCIS", "QAOA", 9),
            ("AIAIC", "QAOA", 16),
        ]

        for domain, algo, qubits in domains:
            w = GaneshWorkloadResponse(
                workload_id=f"workload-{domain.lower()}",
                domain=domain,
                problem_id=f"PROB-{domain}-001",
                algorithm=algo,
                qubits_required=qubits,
                shots=512,
                status="CREATED",
            )
            e = GaneshExecuteResponse(
                execution_id=f"exec-{domain.lower()}",
                workload_id=w.workload_id,
                backend_target="aer_simulator",
                shots=512,
                status="SUCCESS",
                counts={"0" * qubits: 512},
                probabilities={"0" * qubits: 1.0},
                best_candidate="0" * qubits,
            )

            bridge = self.client.bridge_to_qcg_contract(w, e)
            self.assertEqual(bridge.contract.payload["domain"], domain)
            self.assertEqual(bridge.contract.payload["qubits_required"], qubits)
            self.assertEqual(bridge.replay_verdict.status, "VALID")

        self.assertEqual(self.ledger.get_snapshot().sequence_length, 4)
        self.assertTrue(self.ledger.verify_chain())

    def test_offline_unreachable_fallback(self):
        """Verify client gracefully reports UNREACHABLE without throwing unhandled exceptions."""
        offline_client = GaneshClient(base_url="http://127.0.0.1:59999", timeout=1)
        health = offline_client.health()
        self.assertEqual(health.status, "UNREACHABLE")
        self.assertFalse(offline_client.is_available())


if __name__ == "__main__":
    unittest.main()
