import requests
import json
import time

BASE_URL = "http://localhost:8080"

def run_tests():
    print("Testing Health Endpoint...")
    res = requests.get(f"{BASE_URL}/health")
    print(f"Health: {res.status_code}")
    
    print("\nTesting Capabilities Endpoint...")
    res = requests.get(f"{BASE_URL}/capabilities")
    print(f"Capabilities: {res.status_code}")
    
    print("\nTesting Live GC Validation Flow...")
    from node_identity import NodeSigner
    from provenance import sign_contract
    from execution_contract import ComputationExecutionContract
    
    signer = NodeSigner(node_id="SIMULATED_PRODUCER_LIVE", node_role="QUANTUM")
    
    base_contract = ComputationExecutionContract(
        producer_type="QUANTUM",
        payload={"decoded_message": "ECHO", "status": "OK"},
        confidence=0.95,
        trace_id="live-trace-001",
        contract_version="2.0.0"
    )
    
    signed_contract = sign_contract(base_contract, signer)
    
    payload = {
        "contract": signed_contract.to_dict(),
        "producer_public_key": signer.identity.public_key
    }
    
    headers = {"Authorization": "Bearer VALID_GC_TOKEN"}
    res = requests.post(f"{BASE_URL}/gc/validate", json=payload, headers=headers)
    print(f"GC Validate Status: {res.status_code}")
    try:
        print(json.dumps(res.json(), indent=2))
        execution_result = res.json().get("execution_result", {})
    except Exception as e:
        print("Error parsing JSON:", e)
        
    print("\nTesting Replay Lineage Flow...")
    res = requests.get(f"{BASE_URL}/replay/lineage/live-trace-001")
    print(f"Replay Lineage: {res.status_code}")
    print(res.text)
    
    print("\nTesting MDU Evidence Retrieval Flow...")
    if "execution_result" in locals() and "trace_continuity" in execution_result:
        thash = execution_result["trace_continuity"]["runtime_hash"]
        res = requests.get(f"{BASE_URL}/evidence/{thash}")
        print(f"MDU Evidence: {res.status_code}")
        print(json.dumps(res.json(), indent=2))

if __name__ == "__main__":
    run_tests()
