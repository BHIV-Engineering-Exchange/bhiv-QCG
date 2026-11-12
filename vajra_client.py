"""
vajra_client.py — Live VAJRA Trust Substrate Integration Client

Provides an HTTP client for the external VAJRA Blockchain / TruthStore service,
aligned with the QCG ecosystem client pattern (prana_client.py / bucket_client.py).

VAJRA Service: https://vajra.blackholeinfiverse.com
Verified Endpoints:
  GET  /api/health                        — Node health, block height, mempool count
  GET  /api/tantra/chain-integrity        — TruthStore SHA-256 chain continuity check
  POST /api/vajra/provenance/retrieval    — Governed provenance append (Bearer VAJRA_TANTRA_SECRET)
  POST /api/replay/equality               — Parallel deterministic verification equality gate
  POST /api/relay/submit                  — Canonical VAJRA transaction relay
"""

import json
import logging
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import config

logger = logging.getLogger("qcg.vajra")


# ---------------------------------------------------------------------------
# Data Models
# ---------------------------------------------------------------------------

@dataclass
class VajraHealthResponse:
    """Parsed response from VAJRA /api/health endpoint."""
    status: str
    block_height: int
    pending_txs: int
    total_supply: int
    message: str
    success: bool
    raw_response: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: Dict[str, Any], status_code: int) -> "VajraHealthResponse":
        inner = data.get("data") or {}
        healthy = status_code == 200 and bool(data.get("success")) and data.get("status") == "healthy"
        return cls(
            status="OK" if healthy else "UNHEALTHY",
            block_height=int(inner.get("block_height", 0)),
            pending_txs=int(inner.get("pending_txs", 0)),
            total_supply=int(inner.get("total_supply", 0)),
            message=str(data.get("message", "")),
            success=bool(data.get("success", False)),
            raw_response=data,
        )


@dataclass
class VajraChainIntegrityResponse:
    """Parsed response from VAJRA /api/tantra/chain-integrity endpoint."""
    intact: bool
    success: bool
    message: str
    http_status: int
    raw_response: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None


@dataclass
class VajraProvenanceResponse:
    """Parsed response from VAJRA /api/vajra/provenance/retrieval endpoint."""
    status: str
    http_status: int
    authenticated: bool
    raw_response: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None


# ---------------------------------------------------------------------------
# Integration Log — captures request/response pairs with redacted auth
# ---------------------------------------------------------------------------

def _redact_headers(headers: Dict[str, str]) -> Dict[str, str]:
    """Strip Bearer secrets before persisting request headers in evidence logs."""
    redacted: Dict[str, str] = {}
    for k, v in headers.items():
        if k.lower() == "authorization":
            redacted[k] = "Bearer ***REDACTED***"
        else:
            redacted[k] = v
    return redacted


class VajraIntegrationLog:
    """Structured log of all VAJRA API interactions for evidence collection."""

    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")
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
    ) -> Dict[str, Any]:
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "method": method,
            "endpoint": endpoint,
            "url": f"{self.base_url}{endpoint}",
            "request_headers": _redact_headers(headers or {}),
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
# VAJRA HTTP Client
# ---------------------------------------------------------------------------

class VajraClient:
    """
    Production HTTP client for the external VAJRA Trust Substrate service.
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        timeout: Optional[int] = None,
        tantra_secret: Optional[str] = None,
    ):
        resolved_url = base_url or getattr(config, "VAJRA_API_URL", "https://vajra.blackholeinfiverse.com")
        self.base_url = resolved_url.rstrip("/")
        self.timeout = timeout if timeout is not None else getattr(config, "VAJRA_TIMEOUT_SECONDS", 15)
        self.tantra_secret = (
            tantra_secret if tantra_secret is not None else getattr(config, "VAJRA_TANTRA_SECRET", "")
        )
        self.log = VajraIntegrationLog(self.base_url)

    def _request(
        self,
        method: str,
        endpoint: str,
        body: Optional[dict] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> Tuple[int, Any, float, Optional[str]]:
        """Execute HTTP request with timing, error capture, and redacted logging."""
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

    def health(self) -> VajraHealthResponse:
        """Query VAJRA /api/health endpoint."""
        status_code, body, _, err = self._request("GET", "/api/health")
        if err or status_code != 200 or not isinstance(body, dict):
            return VajraHealthResponse(
                status="UNHEALTHY",
                block_height=0,
                pending_txs=0,
                total_supply=0,
                message=err or f"HTTP {status_code}",
                success=False,
                raw_response=body if isinstance(body, dict) else {"error": err or f"HTTP {status_code}"},
            )
        return VajraHealthResponse.from_dict(body, status_code)

    def chain_integrity(self) -> VajraChainIntegrityResponse:
        """Query VAJRA /api/tantra/chain-integrity endpoint."""
        status_code, body, _, err = self._request("GET", "/api/tantra/chain-integrity")
        if err or status_code != 200 or not isinstance(body, dict):
            return VajraChainIntegrityResponse(
                intact=False,
                success=False,
                message=err or f"HTTP {status_code}",
                http_status=status_code,
                raw_response=body if isinstance(body, dict) else {"error": err or f"HTTP {status_code}"},
                error=err,
            )
        return VajraChainIntegrityResponse(
            intact=bool(body.get("intact", False)),
            success=bool(body.get("success", False)),
            message=str(body.get("message", "")),
            http_status=status_code,
            raw_response=body,
        )

    def record_provenance(
        self,
        payload: Dict[str, Any],
        allow_unauthenticated: bool = False,
    ) -> VajraProvenanceResponse:
        """
        Submit provenance record to /api/vajra/provenance/retrieval.

        Fails closed cleanly when VAJRA_TANTRA_SECRET is unset unless
        allow_unauthenticated=True is passed explicitly to test 401 rejection.
        """
        secret = self.tantra_secret or getattr(config, "VAJRA_TANTRA_SECRET", "")
        if not secret and not allow_unauthenticated:
            return VajraProvenanceResponse(
                status="REQUIRES_EXTERNAL_ACCESS",
                http_status=0,
                authenticated=False,
                raw_response={},
                error="VAJRA_TANTRA_SECRET not configured",
            )

        headers: Dict[str, str] = {}
        if secret:
            headers["Authorization"] = f"Bearer {secret}"

        status_code, body, _, err = self._request(
            "POST",
            "/api/vajra/provenance/retrieval",
            body=payload,
            headers=headers,
        )
        parsed = body if isinstance(body, dict) else {"raw": body}
        if err or status_code not in (200, 201):
            status_label = "UNAUTHORIZED" if status_code == 401 else "ERROR"
            return VajraProvenanceResponse(
                status=status_label,
                http_status=status_code,
                authenticated=False,
                raw_response=parsed,
                error=err or f"HTTP {status_code}",
            )
        return VajraProvenanceResponse(
            status="RECORDED",
            http_status=status_code,
            authenticated=True,
            raw_response=parsed,
        )

    def check_replay_equality(self, payload: Dict[str, Any]) -> Tuple[int, Any, Optional[str]]:
        """Submit hash equality payload to /api/replay/equality."""
        status_code, body, _, err = self._request("POST", "/api/replay/equality", body=payload)
        return status_code, body, err

    def submit_relay(self, payload: Dict[str, Any]) -> Tuple[int, Any, Optional[str]]:
        """Submit canonical transaction payload to /api/relay/submit."""
        status_code, body, _, err = self._request("POST", "/api/relay/submit", body=payload)
        return status_code, body, err

    def get_evidence_log(self) -> str:
        """Return all logged interactions as JSON string."""
        return self.log.to_json()
