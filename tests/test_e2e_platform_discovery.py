"""
tests/test_e2e_platform_discovery.py — Phase 2: Platform Discovery E2E Tests

Validates the full capability registration lifecycle and quantum network 
routing negotiation over the HTTP discovery API.
"""

import pytest
import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from platform_discovery_fastapi import app, registry

client = TestClient(app)

@pytest.fixture(autouse=True)
def clear_registry():
    """Ensure a clean registry before each test."""
    registry._services.clear()
    yield
    registry._services.clear()


class TestE2ECapabilityLifecycle:

    def test_full_capability_lifecycle(self):
        """
        E2E Test: External system discovers, registers, heartbeats, 
        negotiates, and revokes a capability.
        """
        service_id = "e2e-quantum-solver"
        
        # 1. Check health/live
        assert client.get("/v1/health/live").status_code == 200
        
        # 2. Register new capability
        register_payload = {
            "service_id": service_id,
            "record": {
                "capability_id": "cap-quantum-solve",
                "service_name": "E2E Quantum Solver",
                "version": "1.5.0",
                "status": "ACTIVE",
                "runtime_type": "QUANTUM",
                "endpoints": {
                    "execute": "https://q-solver.example.com/execute"
                }
            }
        }
        reg_resp = client.post("/v1/register", json=register_payload)
        assert reg_resp.status_code == 200
        assert reg_resp.json()["status"] == "REGISTERED"

        # 3. Verify it appears in discovery list
        list_resp = client.get("/v1/services")
        assert list_resp.status_code == 200
        assert list_resp.json()["count"] == 1

        # 4. Heartbeat check-in
        hb_resp = client.post("/v1/heartbeat", json={"service_id": service_id, "status": "ACTIVE"})
        assert hb_resp.status_code == 200

        # 5. External system negotiates a compatible version
        neg_resp = client.post("/v1/negotiate", json={"service_id": service_id, "version": "1.5.0"})
        assert neg_resp.status_code == 200
        assert neg_resp.json()["status"] == "COMPATIBLE"
        
        # 6. Service revocation
        rev_resp = client.post("/v1/revoke", json={"service_id": service_id, "reason": "Maintenance"})
        assert rev_resp.status_code == 200
        
        # 7. Verify status is revoked (removed from registry)
        final_resp = client.get(f"/v1/services/{service_id}")
        assert final_resp.status_code == 404


class TestE2EQuantumNetworkRouting:

    def test_quantum_node_registration(self):
        """
        E2E Test: Quantum nodes register with specific supported protocols 
        and capabilities (like QKD and Teleportation).
        """
        qnode_id = "qnet-node-alpha"
        
        # Register a quantum node
        register_payload = {
            "service_id": qnode_id,
            "record": {
                "capability_id": "q-route",
                "service_name": "Quantum Router Alpha",
                "version": "2.0.0",
                "runtime_type": "QUANTUM_ROUTER",
                "tags": ["QKD", "BB84"],
                "endpoints": {
                    "classical_control": "https://qalpha.network/api"
                }
            }
        }
        
        resp = client.post("/v1/register", json=register_payload)
        assert resp.status_code == 200
        
        # Validate metadata retrieval
        meta_resp = client.get(f"/v1/services/{qnode_id}/metadata")
        assert meta_resp.status_code == 200
        meta = meta_resp.json()
        
        assert "QKD" in meta.get("service", {}).get("tags", [])
        assert meta.get("service", {}).get("runtime_type") == "QUANTUM_ROUTER"


class TestE2ESecurityBoundaries:

    def test_giant_payload_rejection_e2e(self):
        """
        E2E Test: Ensure giant payloads are strictly rejected by the API
        before ever hitting the registry.
        """
        import config
        # Create a payload exceeding the key limit
        huge_payload = {"service_id": "malicious-node", "record": {}}
        for i in range(config.INPUT_PAYLOAD_MAX_KEYS + 10):
            huge_payload["record"][f"junk_key_{i}"] = "junk_value"
            
        resp = client.post("/v1/register", json=huge_payload)
        assert resp.status_code == 413
        assert "Payload exceeds maximum keys" in resp.text
        
        # Verify the service was NOT registered
        list_resp = client.get("/v1/services")
        assert list_resp.json()["count"] == 0
