from locust import HttpUser, task, between
import json

class EvidenceAPIUser(HttpUser):
    wait_time = between(1, 2)
    
    @task(3)
    def test_health(self):
        self.client.get("/health")
        
    @task(1)
    def test_capabilities(self):
        self.client.get("/capabilities")
        
    @task(2)
    def test_gc_validate(self):
        payload = {
            "contract": {
                "producer_type": "QUANTUM",
                "payload": {"decoded_message": "LOAD_TEST", "status": "OK"},
                "confidence": 0.95,
                "trace_id": "load-test-trace-001",
                "contract_version": "2.0.0"
            },
            "producer_public_key": "dummy_key_not_checked_by_mock"
        }
        
        # In a real environment, node_identity module is used to sign.
        # This will fail GC validation (403/422) due to invalid sig, but we are benching the API throughput, not logical success here.
        headers = {"Authorization": "Bearer VALID_GC_TOKEN"}
        with self.client.post("/gc/validate", json=payload, headers=headers, catch_response=True) as response:
            if response.status_code in [200, 422, 403]:
                response.success()
            else:
                response.failure(f"Unexpected status: {response.status_code}")
