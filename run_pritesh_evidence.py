"""
run_pritesh_evidence.py - Generates Deliverable Proof for Pritesh's Integration Tasks

This script demonstrates the end-to-end flow for Pritesh's responsibilities:
1. Emulate a hardware request.
2. Run it through the IBMQMockHardwareAdapter.
3. Adapt the raw hardware envelope into a ComputationExecutionContract.
4. Pass it to the Web Server `/verify` endpoint locally to prove integration.
5. Capture JSON and save it in the evidence_packet.
"""

import os
import json
import uuid
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from qiskit import QuantumCircuit

# Setup local paths
os.makedirs("evidence_packet/hardware_results", exist_ok=True)
os.makedirs("evidence_packet/screenshots", exist_ok=True)

from ibmq_hardware_adapter import IBMQMockHardwareAdapter
from adapters import HardwareAdapter
from web_server import app

def generate_hardware_evidence():
    print("=== [Pritesh Integration Task] Phase 5/6 Evidence Generation ===")
    
    # 1. Create a logical mock circuit (e.g. Bell state for network entanglement testing)
    qc = QuantumCircuit(2, 2)
    qc.h(0)
    qc.cx(0, 1)
    qc.measure([0, 1], [0, 1])
    
    print("\n[OK] Circuit prepared (2 qubits, depth 2)")
    
    # 2. Use the External Hardware Adapter
    hw_adapter = IBMQMockHardwareAdapter(backend_name="ibm_nazca")
    provider_record = hw_adapter.get_provider_record()
    
    print(f"\n[OK] Connected to Hardware Provider: {provider_record.provider_name} ({provider_record.backend_name})")
    
    envelope = hw_adapter.execute_circuit(qc, shots=5000)
    
    # Save the raw Phase 5/6 manifest exactly as requested
    manifest_path = "evidence_packet/hardware_results/hardware_execution_manifest.json"
    with open(manifest_path, "w") as f:
        json.dump(envelope, f, indent=2)
        
    print(f"\n[OK] Hardware Execution complete. Raw Manifest written to {manifest_path}")
    
    # 3. Adapt Envelope into Canonical Contract (Contract Adaptation)
    adapter = HardwareAdapter()
    contract, adapter_trace = adapter.adapt(envelope)
    
    contract_path = "evidence_packet/hardware_results/adapted_contract.json"
    with open(contract_path, "w") as f:
        json.dump(contract.to_dict(), f, indent=2)
        
    print(f"\n[OK] Envelope adapted. Trace ID: {contract.trace_id}")
    
    # 4. Integrate with Gateway Surface (/verify endpoint)
    # Using FastAPI TestClient to simulate HTTP external client ingestion
    client = TestClient(app)
    
    print("\n[OK] Sending adapted payload to the /verify local endpoint...")
    response = client.post("/verify", json={
        "contract": contract.to_dict(),
        "producer_public_key": "MOCK_PRITESH_CLIENT_KEY"
    })
    
    if response.status_code == 200:
        result = response.json()
        print(f"\n[OK] Web server successfully verified payload. Status: {result.get('status')}")
        
        # Save integration trace
        trace_path = "evidence_packet/hardware_results/verification_response.json"
        with open(trace_path, "w") as f:
            json.dump(result, f, indent=2)
            
        print(f"\n[OK] Evidence saved to {trace_path}")
    else:
        print(f"\n[FAIL] Verification failed: {response.text}")

if __name__ == "__main__":
    generate_hardware_evidence()
