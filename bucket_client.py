"""
bucket_client.py — Live Bucket Integration Client

Provides a production-grade HTTP client for the Live Bucket (Canonical Truth Layer).
Handles evidence publishing, health checks, timeout handling, and retry logic.
"""

import json
import logging
import time
import urllib.request
import urllib.error
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Optional, Tuple, Any

import config

logger = logging.getLogger("qcg.bucket")

# ---------------------------------------------------------------------------
# Data Models
# ---------------------------------------------------------------------------

@dataclass
class BucketHealthResponse:
    """Parsed response from Bucket /health endpoint."""
    status: str
    raw_response: dict = field(default_factory=dict)
    
    @classmethod
    def from_dict(cls, data: dict, status_code: int) -> "BucketHealthResponse":
        return cls(
            status="HEALTHY" if status_code == 200 else "UNHEALTHY",
            raw_response=data
        )

# ---------------------------------------------------------------------------
# Integration Log — captures all request/response pairs for evidence
# ---------------------------------------------------------------------------

class IntegrationLog:
    """Structured log of all Bucket API interactions for evidence collection."""

    def __init__(self):
        self.entries: list = []

    def record(self, method: str, endpoint: str, request_body: Optional[dict],
               status_code: int, response_body: Optional[dict],
               latency_ms: float, error: Optional[str] = None):
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "method": method,
            "endpoint": endpoint,
            "url": f"{config.BUCKET_API_URL}{endpoint}",
            "request_body": request_body,
            "status_code": status_code,
            "response_body": response_body,
            "latency_ms": round(latency_ms, 2),
            "error": error,
            "success": error is None and 200 <= status_code < 300,
        }
        self.entries.append(entry)
        logger.info("Bucket API call: %s %s -> %d (%.1fms)",
                     method, endpoint, status_code, latency_ms)
        return entry

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.entries, indent=indent, default=str)


# ---------------------------------------------------------------------------
# Bucket Client
# ---------------------------------------------------------------------------

class BucketClient:
    """
    Production-grade HTTP client for the live Bucket API.
    """

    def __init__(self, base_url: str = None, timeout: int = None, retries: int = 3):
        self.base_url = (base_url or config.BUCKET_API_URL).rstrip("/")
        self.timeout = timeout or config.BUCKET_TIMEOUT_SECONDS
        self.retries = retries
        self.log = IntegrationLog()
        self._available: Optional[bool] = None

    def _request_with_retry(self, method: str, endpoint: str,
                            body: Optional[dict] = None) -> Tuple[int, dict]:
        """
        Execute an HTTP request with built-in retry backoff mechanism.
        Returns (status_code, response_body_dict).
        """
        url = f"{self.base_url}{endpoint}"
        
        for attempt in range(self.retries + 1):
            start = time.monotonic()
            try:
                if method == "POST" and body is not None:
                    data = json.dumps(body).encode("utf-8")
                    req = urllib.request.Request(
                        url, data=data,
                        headers={"Content-Type": "application/json"},
                        method="POST"
                    )
                else:
                    req = urllib.request.Request(url, method="GET")

                with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                    latency = (time.monotonic() - start) * 1000
                    response_body = json.loads(resp.read().decode("utf-8"))
                    self.log.record(method, endpoint, body, resp.status,
                                    response_body, latency)
                    return resp.status, response_body

            except urllib.error.HTTPError as e:
                latency = (time.monotonic() - start) * 1000
                try:
                    error_body = json.loads(e.read().decode("utf-8"))
                except Exception:
                    error_body = {"raw_error": str(e)}
                self.log.record(method, endpoint, body, e.code,
                                error_body, latency, error=str(e))
                # Only retry on 5xx errors or 429
                if attempt < self.retries and (e.code >= 500 or e.code == 429):
                    time.sleep(2 ** attempt) # Exponential backoff
                    continue
                return e.code, error_body

            except Exception as e:
                latency = (time.monotonic() - start) * 1000
                self.log.record(method, endpoint, body, 0, None, latency,
                                error=str(e))
                if attempt < self.retries:
                    time.sleep(2 ** attempt)
                    continue
                return 0, {"error": str(e)}

    # -- Public API -----------------------------------------------------------

    def health(self) -> BucketHealthResponse:
        """Check Bucket service health. (Assuming GET /docs or /health)"""
        # Testing the base or docs endpoint just for reachability
        url = f"{self.base_url}/docs"
        try:
            req = urllib.request.Request(url, method="GET")
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                self._available = True
                return BucketHealthResponse(status="HEALTHY", raw_response={"message": "docs available"})
        except Exception as e:
            self._available = False
            return BucketHealthResponse(status="UNREACHABLE", raw_response={"error": str(e)})

    def get_latest_hash(self) -> str:
        """
        Retrieves the latest hash from the canonical chain.
        GET /bucket/latest-hash
        """
        status, body = self._request_with_retry("GET", "/bucket/latest-hash")
        if status == 200 and isinstance(body, dict):
            return body.get("hash", "")
        return ""

    def validate_chain(self, artifact_id: str) -> Optional[dict]:
        """
        Validates the mathematical continuity of the chain up to a specific artifact.
        GET /bucket/validate-chain/{artifact_id}
        """
        status, body = self._request_with_retry("GET", f"/bucket/validate-chain/{artifact_id}")
        if status == 200:
            return body
        logger.error(f"Failed to validate chain for {artifact_id}: {status} - {body}")
        return None

    def publish_artifact(self, artifact_payload: dict) -> Tuple[bool, dict]:
        """
        Publish an artifact to the bucket.
        POST /bucket/artifact
        Handles parent_hash trace continuity proactively by fetching the latest hash,
        and dynamically retrying if it races with another publication.
        """
        # Proactive Trace Continuity
        if not artifact_payload.get("parent_hash"):
            latest = self.get_latest_hash()
            if latest:
                artifact_payload["parent_hash"] = latest

        status, body = self._request_with_retry("POST", "/bucket/artifact", artifact_payload)
        
        # Dynamic Trace Continuity: Catch Invalid parent_hash errors (e.g. race conditions) and retry
        if status == 400 and body and "detail" in body:
            detail = body["detail"]
            if detail.get("error") == "ValidationError":
                msg = detail.get("message", "")
                if "Invalid parent_hash" in msg and "Expected:" in msg:
                    # Parse out the Expected hash
                    import re
                    match = re.search(r"Expected:\s*([a-f0-9]{64})", msg)
                    if match:
                        expected_hash = match.group(1)
                        logger.info("Trace continuity auto-correct: Updating parent_hash to %s", expected_hash)
                        artifact_payload["parent_hash"] = expected_hash
                        # Retry the request with the correct hash
                        status, body = self._request_with_retry("POST", "/bucket/artifact", artifact_payload)
        
        return (200 <= status < 300), body

    def is_available(self) -> bool:
        if self._available is None:
            self.health()
        return self._available is True

    def get_artifact(self, artifact_id: str) -> Optional[dict]:
        """
        Retrieve a specific artifact (execution evidence, certificate, etc) by ID.
        GET /bucket/artifact/{artifact_id}
        """
        status, body = self._request_with_retry("GET", f"/bucket/artifact/{artifact_id}")
        if status == 200:
            return body
        logger.error(f"Failed to retrieve artifact {artifact_id}: {status} - {body}")
        return None

    def get_trace_history(self, trace_id: str) -> list[dict]:
        """
        Retrieve the full chain of custody for a trace.
        GET /bucket/artifacts?trace_id={trace_id} (or whatever query param is supported)
        We will pass trace_id as a query param.
        """
        import urllib.parse
        query = urllib.parse.urlencode({"trace_id": trace_id})
        status, body = self._request_with_retry("GET", f"/bucket/artifacts?{query}")
        if status == 200:
            # Assuming it returns a list directly or a 'data'/'artifacts' key
            if isinstance(body, list):
                return body
            return body.get("artifacts", body.get("data", []))
        logger.error(f"Failed to retrieve trace history for {trace_id}: {status} - {body}")
        return []

    def get_evidence_log(self) -> str:
        return self.log.to_json()

# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

_default_client: Optional[BucketClient] = None

def get_client() -> BucketClient:
    global _default_client
    if _default_client is None:
        _default_client = BucketClient()
    return _default_client


if __name__ == "__main__":
    import uuid
    logging.basicConfig(level=logging.INFO)
    
    client = BucketClient()
    print("=" * 60)
    print("Bucket Live Integration Test")
    print(f"Target: {client.base_url}")
    print("=" * 60)

    # 1. Health check
    print("\n--- Health Check ---")
    h = client.health()
    print(f"Status: {h.status}")
    print(f"Available: {client.is_available()}")

    # 2. Publish Artifact
    print("\n--- Publish Evidence ---")
    payload = {
        "artifact_id": str(uuid.uuid4()),
        "trace_id": str(uuid.uuid4()),
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "schema_version": "1.0.0",
        "source_module_id": "usf_evidence_publisher",
        "artifact_type": "execution_evidence",
        "parent_hash": "1774a1cde9800ff4087ed455078f7fd9874db8c2ae1dbc886fa4f64c09181367",
        "payload": {
            "status": "success",
            "message": "Test execution evidence from Phase 1."
        }
    }
    success, resp = client.publish_artifact(payload)
    print(f"Publish Success: {success}")
    print(f"Response: {resp}")

    # 3. Retrieve Evidence
    if success and resp and "artifact_id" in resp:
        print("\n--- Retrieve Evidence ---")
        time.sleep(2) # Give the bucket a moment to index
        artifact_id = resp["artifact_id"]
        print(f"Retrieving artifact_id: {artifact_id}")
        retrieved = client.get_artifact(artifact_id)
        if retrieved:
            print("Retrieve Success: True")
            print(f"Retrieved Data: {json.dumps(retrieved, indent=2)}")
        else:
            print("Retrieve Success: False")

    # 4. Print evidence log
    print("\n--- Integration Evidence Log ---")
    print(client.get_evidence_log())
