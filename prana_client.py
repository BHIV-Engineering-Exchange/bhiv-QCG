"""
prana_client.py — Live PRANA Ecosystem Integration Client

Provides a production-grade HTTP client for the PRANA Service (TANTRA pipeline).
Handles event ingestion, trace propagation, MongoDB replay verification,
health checks, timeout handling, and graceful fallback.

PRANA Service: http://163.128.209.18:8103
Endpoints:
  POST /prana/ingest          — Stateless event ingestion & MongoDB provenance
  GET  /health                — Liveness & MongoDB connectivity check
  GET  /ready                 — Readiness check
  GET  /prana/system/health   — Full system health & replay record count
  GET  /replay/{trace_id}     — Replay record retrieval from MongoDB
"""

import json
import logging
import time
import urllib.request
import urllib.error
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple, List

import config

logger = logging.getLogger("qcg.prana")


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

PRANA_API_URL: str = getattr(config, "PRANA_API_URL", "http://163.128.209.18:8103")
PRANA_TIMEOUT: int = getattr(config, "PRANA_TIMEOUT_SECONDS", 10)
PRANA_ENABLED: bool = getattr(config, "PRANA_ENABLED", True)


# ---------------------------------------------------------------------------
# Data Models
# ---------------------------------------------------------------------------

@dataclass
class PranaHealthResponse:
    """Parsed response from PRANA /health endpoint."""
    status: str
    service: str
    forwarding_enabled: bool
    mongodb_connected: bool
    database_name: str
    raw_response: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: Dict[str, Any], status_code: int) -> "PranaHealthResponse":
        mongo = data.get("mongodb", {})
        return cls(
            status="OK" if status_code == 200 and data.get("status") == "healthy" else "UNHEALTHY",
            service=data.get("service", "bhiv-prana"),
            forwarding_enabled=data.get("forwarding_enabled", False),
            mongodb_connected=mongo.get("mongodb_connected", False),
            database_name=mongo.get("database_name", "prana"),
            raw_response=data,
        )


@dataclass
class PranaSystemHealthResponse:
    """Parsed response from PRANA /prana/system/health endpoint."""
    status: str
    mode: str
    forwarding_enabled: bool
    mongodb_connected: bool
    database_name: str
    replay_records_count: int
    last_replay_timestamp: Optional[str]
    raw_response: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: Dict[str, Any], status_code: int) -> "PranaSystemHealthResponse":
        mongo = data.get("mongodb", {})
        return cls(
            status="OK" if status_code == 200 and data.get("status") == "healthy" else "UNHEALTHY",
            mode=data.get("mode", "stateful"),
            forwarding_enabled=data.get("forwarding_enabled", False),
            mongodb_connected=mongo.get("mongodb_connected", False),
            database_name=mongo.get("database_name", "prana"),
            replay_records_count=data.get("replay_records_count", 0),
            last_replay_timestamp=data.get("last_replay_timestamp"),
            raw_response=data,
        )


@dataclass
class PranaIngestResponse:
    """Parsed response from PRANA /prana/ingest endpoint."""
    status: str
    event_id: str
    total_elapsed_ms: int
    trace_id: str
    http_status: int
    raw_response: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None


# ---------------------------------------------------------------------------
# Integration Log — captures all request/response pairs for evidence
# ---------------------------------------------------------------------------

class PranaIntegrationLog:
    """Structured log of all PRANA API interactions for evidence collection."""

    def __init__(self):
        self.entries: List[Dict[str, Any]] = []

    def record(
        self,
        method: str,
        endpoint: str,
        request_body: Optional[dict],
        status_code: int,
        response_body: Optional[Any],
        latency_ms: float,
        headers: Optional[dict] = None,
        error: Optional[str] = None,
    ):
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "method": method,
            "endpoint": endpoint,
            "url": f"{PRANA_API_URL.rstrip('/')}{endpoint}",
            "request_headers": headers or {},
            "request_body": request_body,
            "status_code": status_code,
            "response_body": response_body,
            "latency_ms": round(latency_ms, 2),
            "error": error,
        }
        self.entries.append(entry)
        return entry

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.entries, indent=indent, default=str)


# ---------------------------------------------------------------------------
# PRANA HTTP Client
# ---------------------------------------------------------------------------

class PranaClient:
    """
    Production-grade HTTP client for the PRANA service.

    Provides:
      - Health checks (/health, /ready, /prana/system/health)
      - Event ingestion (/prana/ingest)
      - Replay record queries (/replay/{trace_id})
      - Automatic W3C trace context propagation & x-trace-id
      - Structured evidence logging
    """

    def __init__(self, base_url: Optional[str] = None, timeout: Optional[int] = None):
        self.base_url = (base_url or PRANA_API_URL).rstrip("/")
        self.timeout = timeout or PRANA_TIMEOUT
        self.log = PranaIntegrationLog()

    def _request(
        self,
        method: str,
        endpoint: str,
        body: Optional[dict] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> Tuple[int, Any, float, Optional[str]]:
        """Execute HTTP request with timing, error capture, and logging."""
        url = f"{self.base_url}{endpoint}"
        req_headers = {"User-Agent": "BHIV-TANTRA-QCG/2.0.0"}
        if headers:
            req_headers.update(headers)

        data = None
        if body is not None:
            data = json.dumps(body).encode("utf-8")
            req_headers["Content-Type"] = "application/json"

        req = urllib.request.Request(url, data=data, headers=req_headers, method=method)
        start = time.monotonic()
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                latency_ms = (time.monotonic() - start) * 1000
                status_code = resp.getcode()
                raw = resp.read().decode("utf-8", errors="replace")
                try:
                    resp_body = json.loads(raw)
                except json.JSONDecodeError:
                    resp_body = raw
                self.log.record(method, endpoint, body, status_code, resp_body, latency_ms, req_headers)
                return status_code, resp_body, latency_ms, None
        except urllib.error.HTTPError as exc:
            latency_ms = (time.monotonic() - start) * 1000
            status_code = exc.code
            raw = exc.read().decode("utf-8", errors="replace")
            try:
                resp_body = json.loads(raw)
            except json.JSONDecodeError:
                resp_body = raw
            err_msg = f"HTTP {status_code}: {raw}"
            self.log.record(method, endpoint, body, status_code, resp_body, latency_ms, req_headers, error=err_msg)
            return status_code, resp_body, latency_ms, err_msg
        except urllib.error.URLError as exc:
            latency_ms = (time.monotonic() - start) * 1000
            err_msg = f"Network error: {exc.reason}"
            self.log.record(method, endpoint, body, 0, None, latency_ms, req_headers, error=err_msg)
            return 0, None, latency_ms, err_msg
        except Exception as exc:
            latency_ms = (time.monotonic() - start) * 1000
            err_msg = f"Unexpected error: {str(exc)}"
            self.log.record(method, endpoint, body, 0, None, latency_ms, req_headers, error=err_msg)
            return 0, None, latency_ms, err_msg

    def health(self) -> PranaHealthResponse:
        """Call PRANA /health endpoint."""
        status_code, body, _, err = self._request("GET", "/health")
        if err or status_code != 200 or not isinstance(body, dict):
            return PranaHealthResponse(
                status="UNHEALTHY",
                service="bhiv-prana",
                forwarding_enabled=False,
                mongodb_connected=False,
                database_name="",
                raw_response={"error": err or f"HTTP {status_code}"},
            )
        return PranaHealthResponse.from_dict(body, status_code)

    def system_health(self) -> PranaSystemHealthResponse:
        """Call PRANA /prana/system/health endpoint."""
        status_code, body, _, err = self._request("GET", "/prana/system/health")
        if err or status_code != 200 or not isinstance(body, dict):
            return PranaSystemHealthResponse(
                status="UNHEALTHY",
                mode="unknown",
                forwarding_enabled=False,
                mongodb_connected=False,
                database_name="",
                replay_records_count=0,
                last_replay_timestamp=None,
                raw_response={"error": err or f"HTTP {status_code}"},
            )
        return PranaSystemHealthResponse.from_dict(body, status_code)

    def ingest_event(
        self,
        payload: Dict[str, Any],
        trace_id: Optional[str] = None,
        traceparent: Optional[str] = None,
        tracestate: Optional[str] = None,
        event_type: str = "truth_classification",
        source_system: str = "bhiv-qcg",
        submission_id: Optional[str] = None,
        certification_status: Optional[str] = "CERTIFIED",
    ) -> PranaIngestResponse:
        """
        Ingest a TANTRA event into PRANA.

        Formats request according to PRANA event contract:
          - submission_id
          - event_type
          - source_system
          - timestamp
          - payload
          - trace_id
          - certification_status
        """
        now = datetime.now(timezone.utc).isoformat()
        final_trace_id = trace_id or payload.get("trace_id") or f"tantra-qcg-{time.time()}"
        sub_id = submission_id or payload.get("execution_id") or f"sub-{final_trace_id}"

        body = {
            "submission_id": sub_id,
            "event_type": event_type,
            "source_system": source_system,
            "timestamp": now,
            "payload": payload,
            "trace_id": final_trace_id,
            "certification_status": certification_status,
        }

        headers: Dict[str, str] = {
            "x-trace-id": final_trace_id,
        }
        if traceparent:
            headers["traceparent"] = traceparent
        if tracestate:
            headers["tracestate"] = tracestate

        status_code, resp_data, _, err = self._request("POST", "/prana/ingest", body=body, headers=headers)

        if err or status_code != 200 or not isinstance(resp_data, dict):
            logger.error("[PRANA] Ingest failed: status=%s error=%s", status_code, err)
            return PranaIngestResponse(
                status="FAILED",
                event_id="",
                total_elapsed_ms=0,
                trace_id=final_trace_id,
                http_status=status_code,
                raw_response=resp_data if isinstance(resp_data, dict) else {"raw": resp_data},
                error=err or f"HTTP {status_code}",
            )

        return PranaIngestResponse(
            status=resp_data.get("status", "forwarded"),
            event_id=resp_data.get("event_id", ""),
            total_elapsed_ms=resp_data.get("total_elapsed_ms", 0),
            trace_id=final_trace_id,
            http_status=status_code,
            raw_response=resp_data,
            error=None,
        )

    def get_replay(self, trace_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve persisted replay record for a given trace_id from PRANA."""
        status_code, body, _, err = self._request("GET", f"/replay/{trace_id}?latest=true&include_headers=true&include_payload=true")
        if status_code == 200 and isinstance(body, dict):
            return body
        return None

    def get_evidence_log(self) -> str:
        """Return all logged interactions as JSON string."""
        return self.log.to_json()
