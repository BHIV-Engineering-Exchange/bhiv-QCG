"""
scripts/generate_ganesh_evidence.py — Capture Live Evidence for Ganesh's Quantum Application Layer

Executes live against https://bhiv-quantum-application-layer.onrender.com:
1. Health check verification
2. Capability discovery across all 4 domains (VANA, MARINE, UCCIS, AIAIC) and backends
3. Workload creation and live execution on aer_simulator for VANA and MARINE
4. Validation of downstream hardware blocker on bhiv_runtime (MQR-01)
5. QCG sovereign bridge verification (contracts, ECDSA P-256 signatures, replay sequencing, Merkle tree inclusion)
6. Writes review_packets/evidence_packet/api_samples/ganesh_live_evidence.json
"""

import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# Ensure project root is on sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ganesh_live_client import (
    GaneshClient,
    GaneshWorkloadRequest,
    GaneshExecuteRequest,
)


def generate_evidence():
    client = GaneshClient()
    output_path = Path("review_packets/evidence_packet/api_samples/ganesh_live_evidence.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"Connecting to live Ganesh API: {client.base_url}...")
    evidence_data = {
        "_metadata": {
            "captured_at": datetime.now(timezone.utc).isoformat(),
            "description": "Complete live integration evidence for Ganesh BHIV Quantum Application Layer",
            "file": "ganesh_live_evidence.json",
            "participant": "Ganesh Bhiv (Quantum Application Team)",
            "federation_role": "Kanishk (QCG Platform Federation & SDK)",
            "service_id": "TANTRA-PSR-QAPP-001",
        },
        "service": "BHIV_QUANTUM_APPLICATION_LAYER",
        "base_url": client.base_url,
        "tests": [],
        "bridge_records": [],
    }

    # 1. Health check
    print("Executing: Health Check...")
    h = client.health()
    evidence_data["tests"].append({
        "test": "Health Check",
        "endpoint": "GET /health",
        "purpose": "Verify live service accessibility on Render",
        "expected_outcome": "Status HEALTHY, Service quantum-application-layer",
        "actual_outcome": f"Status={h.status}, Service={h.service}, Version={h.version}",
        "passed": h.status in ("HEALTHY", "OK"),
        "response": h.raw_response,
    })

    # 2. Capabilities
    print("Executing: Capability Discovery...")
    caps = client.get_capabilities()
    evidence_data["tests"].append({
        "test": "Capability Discovery",
        "endpoint": "GET /api/v1/capabilities",
        "purpose": "Discover supported domain optimization models and quantum backends",
        "expected_outcome": "4 domains (VANA, MARINE, UCCIS, AIAIC) and 3 backends",
        "actual_outcome": f"Found {len(caps.domains)} domains and {len(caps.backends)} backends",
        "passed": len(caps.domains) >= 4,
        "domains": caps.domains,
        "backends": caps.backends,
        "response": caps.raw_response,
    })

    # 3. Workload Creation & Execution: VANA (6 qubits)
    print("Executing: VANA Workload (6 qubits)...")
    vana_req = GaneshWorkloadRequest(
        domain="VANA",
        problem_id="PROB-VANA-ECOGRID-001",
        algorithm="QAOA",
        qubits_required=6,
        shots=256,
        formulation={"num_zones": 6, "cost_matrix": [[0, 1], [1, 0]]},
    )
    vana_w = client.create_workload(vana_req)
    vana_e = client.execute_workload(vana_w.workload_id, GaneshExecuteRequest(backend_target="aer_simulator", shots=256))
    vana_bridge = client.bridge_to_qcg_contract(vana_w, vana_e)

    evidence_data["tests"].append({
        "test": "VANA Workload & Execution",
        "endpoint": f"POST /api/v1/workloads/{vana_w.workload_id}/execute",
        "purpose": "Execute VANA environmental sensor optimization on aer_simulator",
        "expected_outcome": "Status SUCCESS with non-empty counts and candidate",
        "actual_outcome": f"Status={vana_e.status}, BestCandidate={vana_e.best_candidate}",
        "passed": vana_e.status == "SUCCESS",
        "workload_response": vana_w.raw_response,
        "execution_response": vana_e.raw_response,
    })
    evidence_data["bridge_records"].append(vana_bridge.to_dict())

    # 4. Workload Creation & Execution: MARINE (8 qubits)
    print("Executing: MARINE Workload (8 qubits)...")
    marine_req = GaneshWorkloadRequest(
        domain="MARINE",
        problem_id="PROB-MARINE-NW53-001",
        algorithm="QAOA",
        qubits_required=8,
        shots=256,
        formulation={"num_ports": 8, "logistics_factor": 1.4},
    )
    marine_w = client.create_workload(marine_req)
    marine_e = client.execute_workload(marine_w.workload_id, GaneshExecuteRequest(backend_target="aer_simulator", shots=256))
    marine_bridge = client.bridge_to_qcg_contract(marine_w, marine_e)

    evidence_data["tests"].append({
        "test": "MARINE Workload & Execution",
        "endpoint": f"POST /api/v1/workloads/{marine_w.workload_id}/execute",
        "purpose": "Execute NW-53 maritime waterway logistics optimization on aer_simulator",
        "expected_outcome": "Status SUCCESS with non-empty counts and candidate",
        "actual_outcome": f"Status={marine_e.status}, BestCandidate={marine_e.best_candidate}",
        "passed": marine_e.status == "SUCCESS",
        "workload_response": marine_w.raw_response,
        "execution_response": marine_e.raw_response,
    })
    evidence_data["bridge_records"].append(marine_bridge.to_dict())

    # 5. Workload Creation & Execution: UCCIS (9 qubits)
    print("Executing: UCCIS Workload (9 qubits)...")
    uccis_req = GaneshWorkloadRequest(
        domain="UCCIS",
        problem_id="PROB-UCCIS-DISPATCH-001",
        algorithm="QAOA",
        qubits_required=9,
        shots=256,
        formulation={"num_zones": 9, "priority_weight": 2.0},
    )
    uccis_w = client.create_workload(uccis_req)
    uccis_e = client.execute_workload(uccis_w.workload_id, GaneshExecuteRequest(backend_target="aer_simulator", shots=256))
    uccis_bridge = client.bridge_to_qcg_contract(uccis_w, uccis_e)

    evidence_data["tests"].append({
        "test": "UCCIS Workload & Execution",
        "endpoint": f"POST /api/v1/workloads/{uccis_w.workload_id}/execute",
        "purpose": "Execute Urban Command & Control dispatch optimization on aer_simulator",
        "expected_outcome": "Status SUCCESS with non-empty counts and candidate",
        "actual_outcome": f"Status={uccis_e.status}, BestCandidate={uccis_e.best_candidate}",
        "passed": uccis_e.status == "SUCCESS",
        "workload_response": uccis_w.raw_response,
        "execution_response": uccis_e.raw_response,
    })
    evidence_data["bridge_records"].append(uccis_bridge.to_dict())

    # 6. Workload Creation & Execution: AIAIC (16 qubits)
    print("Executing: AIAIC Workload (16 qubits)...")
    aiaic_req = GaneshWorkloadRequest(
        domain="AIAIC",
        problem_id="PROB-AIAIC-MANDI-001",
        algorithm="QAOA",
        qubits_required=16,
        shots=128,
        formulation={"mandi_count": 16, "perishability_penalty": 3.5},
    )
    aiaic_w = client.create_workload(aiaic_req)
    aiaic_e = client.execute_workload(aiaic_w.workload_id, GaneshExecuteRequest(backend_target="aer_simulator", shots=128))
    if aiaic_e.status != "SUCCESS":
        time.sleep(3)
        for ex in reversed(client.list_executions()):
            if ex.get("workload_id") == aiaic_w.workload_id:
                aiaic_e = GaneshExecuteResponse.from_dict(ex)
                break
    aiaic_bridge = client.bridge_to_qcg_contract(aiaic_w, aiaic_e)

    evidence_data["tests"].append({
        "test": "AIAIC Workload & Execution",
        "endpoint": f"POST /api/v1/workloads/{aiaic_w.workload_id}/execute",
        "purpose": "Execute Agricultural Mandi clearing optimization on aer_simulator",
        "expected_outcome": "Status SUCCESS with non-empty counts and candidate",
        "actual_outcome": f"Status={aiaic_e.status}, BestCandidate={aiaic_e.best_candidate}",
        "passed": aiaic_e.status == "SUCCESS",
        "workload_response": aiaic_w.raw_response,
        "execution_response": aiaic_e.raw_response,
    })
    evidence_data["bridge_records"].append(aiaic_bridge.to_dict())

    # 7. Hardware Backend Blocker Validation: bhiv_runtime
    print("Executing: Hardware Blocker Probe (bhiv_runtime)...")
    hw_w = client.create_workload(GaneshWorkloadRequest(
        domain="MARINE",
        problem_id="PROB-HW-PROBE",
        algorithm="QAOA",
        qubits_required=8,
    ))
    # Quick client with 5s timeout to probe blocked hardware adapter gracefully
    quick_client = GaneshClient(timeout=5)
    hw_e = quick_client.execute_workload(hw_w.workload_id, GaneshExecuteRequest(backend_target="bhiv_runtime"))
    evidence_data["tests"].append({
        "test": "Downstream Hardware Backend Probe (bhiv_runtime)",
        "endpoint": f"POST /api/v1/workloads/{hw_w.workload_id}/execute",
        "purpose": "Verify graceful status reporting on blocked downstream physical quantum runtime",
        "expected_outcome": "Blocked status or explicit downstream error without crash",
        "actual_outcome": f"Status={hw_e.status}, ErrorMessage={hw_e.error_message}",
        "passed": hw_e.status in ("FAILED", "BLOCKED", "EXECUTION_FAILED"),
        "response": hw_e.raw_response,
    })

    # Summary
    evidence_data["summary"] = {
        "total_tests": len(evidence_data["tests"]),
        "passed_tests": sum(1 for t in evidence_data["tests"] if t["passed"]),
        "total_contracts_bridged": len(evidence_data["bridge_records"]),
        "ledger_chain_length": client.ledger.get_snapshot().sequence_length,
        "merkle_root": client.ledger.get_snapshot().merkle_root,
        "chain_integrity_verified": client.ledger.verify_chain(),
    }
    evidence_data["api_call_log"] = client.log.entries

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(evidence_data, f, indent=2, default=str)

    print(f"Evidence successfully exported to {output_path}")
    print(f"Summary: {evidence_data['summary']}")


if __name__ == "__main__":
    generate_evidence()
