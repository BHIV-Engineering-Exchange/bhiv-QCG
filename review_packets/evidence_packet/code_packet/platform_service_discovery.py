"""
platform_service_discovery.py — Platform Service Discovery API Server

Exposes canonical REST endpoints for zero-configuration discovery of
TANTRA Platform Services.  Runs as an HTTP server and auto-registers
itself with the existing CapabilityRegistryServer.

All endpoints are validated and published in the capability manifest.

RESPONSIBILITY BOUNDARY
-----------------------
DiscoveryServer OWNS:
    - HTTP endpoint publication
    - Service discovery API
    - Version negotiation endpoint
    - Health/readiness/metrics publication
    - Federation status / audit / sync endpoints
    - Authenticated registration endpoint
    - Heartbeat / revocation endpoints

DiscoveryServer does NOT OWN:
    - Service registration logic       → PlatformServiceRegistry
    - Lifecycle management             → LifecycleManager
    - Solver execution                 → Universal Solver Fabric
    - Contract validation              → RuntimeCore
    - Federation protocol              → FederatedRegistryNode
    - Certificate issuance             → ServiceCertificateAuthority
"""

from __future__ import annotations

import json
import logging
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any, Dict, Optional
from urllib.parse import urlparse, parse_qs

from platform_service_registry import (
    PlatformServiceRegistry,
    PlatformServiceRecord,
    RegistrationEvidenceRecorder,
    PLATFORM_REGISTRY_VERSION,
)
from platform_lifecycle_manager import LifecycleManager

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("tantra.platform.discovery")

# Module-level state — set by start_discovery_server()
_registry: Optional[PlatformServiceRegistry] = None
_lifecycle: Optional[LifecycleManager] = None
_federation_node = None  # Optional FederatedRegistryNode
_start_time = time.time()
_request_count = 0
_request_lock = threading.Lock()

DISCOVERY_SERVER_VERSION = "2.0.0"


# ---------------------------------------------------------------------------
# Request handler
# ---------------------------------------------------------------------------

class PlatformDiscoveryHandler(BaseHTTPRequestHandler):
    """HTTP request handler for the Platform Service Discovery API."""

    def log_message(self, format, *args):
        pass  # Suppress default logging

    def _set_json_headers(self, status: int = 200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("X-Platform-Version", DISCOVERY_SERVER_VERSION)
        self.end_headers()

    def _write_json(self, data: Any, status: int = 200):
        self._set_json_headers(status)
        self.wfile.write(json.dumps(data, default=str).encode("utf-8"))

    def _read_body(self) -> dict:
        content_length = int(self.headers.get("Content-Length", 0))
        if content_length == 0:
            return {}
        body = self.rfile.read(content_length).decode("utf-8")
        return json.loads(body)

    def _increment_request_count(self):
        global _request_count
        with _request_lock:
            _request_count += 1

    # -- GET routes ---------------------------------------------------------

    def do_GET(self):
        self._increment_request_count()
        path = self.path.split("?")[0].rstrip("/")  # strip query + trailing slash

        # --- Top-level platform endpoints ---
        if path == "/platform/v1/services":
            return self._handle_list_services()

        if path == "/platform/v1/health":
            return self._handle_server_health()

        if path == "/platform/v1/readiness":
            return self._handle_server_readiness()

        if path == "/platform/v1/metrics":
            return self._handle_metrics()

        if path == "/platform/v1/evidence":
            return self._handle_evidence()

        if path == "/platform/v1/version":
            return self._handle_version()

        # --- Federation endpoints (GET) ---
        if path == "/platform/v1/federation/status":
            return self._handle_federation_status()

        if path == "/platform/v1/federation/audit":
            return self._handle_federation_audit()

        if path == "/platform/v1/certificates":
            return self._handle_list_certificates()

        # --- Per-service endpoints ---
        # /platform/v1/services/{service_id}
        # /platform/v1/services/{service_id}/versions
        # /platform/v1/services/{service_id}/metadata
        # /platform/v1/services/{service_id}/contracts
        # /platform/v1/services/{service_id}/endpoints
        # /platform/v1/services/{service_id}/health
        # /platform/v1/services/{service_id}/compatibility
        parts = path.split("/")
        if len(parts) >= 5 and parts[1] == "platform" and parts[2] == "v1" and parts[3] == "services":
            service_id = parts[4]
            if len(parts) == 5:
                return self._handle_get_service(service_id)
            if len(parts) == 6:
                sub = parts[5]
                if sub == "versions":
                    return self._handle_get_versions(service_id)
                if sub == "metadata":
                    return self._handle_get_metadata(service_id)
                if sub == "contracts":
                    return self._handle_get_contracts(service_id)
                if sub == "endpoints":
                    return self._handle_get_endpoints(service_id)
                if sub == "health":
                    return self._handle_get_health(service_id)
                if sub == "compatibility":
                    return self._handle_get_compatibility(service_id)

        # Not found
        self._write_json({"error": "Endpoint not found", "path": self.path}, 404)

    # -- POST routes --------------------------------------------------------

    def do_POST(self):
        self._increment_request_count()
        path = self.path.split("?")[0].rstrip("/")

        if path == "/platform/v1/negotiate":
            return self._handle_negotiate()

        if path == "/platform/v1/register":
            return self._handle_register()

        if path == "/platform/v1/heartbeat":
            return self._handle_heartbeat()

        if path == "/platform/v1/revoke":
            return self._handle_revoke()

        if path == "/platform/v1/federation/sync":
            return self._handle_federation_sync()

        # Handle mock execution POST request to service endpoints
        parts = path.split("/")
        if len(parts) == 5 and parts[1] == "platform" and parts[2] == "v1" and parts[3] == "services":
            service_id = parts[4]
            record = _registry.get_service(service_id) if _registry else None
            if record:
                self._write_json({
                    "status": "EXECUTED",
                    "service_id": service_id,
                    "ack": True,
                    "payload_received": True,
                    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S+00:00", time.gmtime())
                })
                return
            else:
                self._write_json({"error": f"Service '{service_id}' not found"}, 404)
                return

        self._write_json({"error": "Endpoint not found", "path": self.path}, 404)

    # -- Handler implementations --------------------------------------------

    def _handle_list_services(self):
        services = _registry.list_services() if _registry else []
        self._write_json({
            "services": services,
            "count": len(services),
            "registry_version": PLATFORM_REGISTRY_VERSION,
        })

    def _handle_get_service(self, service_id: str):
        record = _registry.get_service(service_id) if _registry else None
        if record:
            self._write_json(record)
        else:
            self._write_json({"error": f"Service '{service_id}' not found"}, 404)

    def _handle_get_versions(self, service_id: str):
        record = _registry.get_service(service_id) if _registry else None
        if not record:
            self._write_json({"error": f"Service '{service_id}' not found"}, 404)
            return
        versions = _registry.get_versions(service_id) if _registry else {}
        self._write_json(versions)

    def _handle_get_metadata(self, service_id: str):
        metadata = _registry.get_metadata(service_id) if _registry else None
        if metadata:
            self._write_json(metadata)
        else:
            self._write_json({"error": f"Service '{service_id}' not found"}, 404)

    def _handle_get_contracts(self, service_id: str):
        manifest = _registry.get_manifest(service_id) if _registry else None
        if manifest:
            operations = manifest.get("supported_operations", [])
            self._write_json({
                "service_id": service_id,
                "contracts": operations,
                "count": len(operations),
            })
        else:
            self._write_json({"error": f"Manifest for '{service_id}' not found"}, 404)

    def _handle_get_endpoints(self, service_id: str):
        endpoints = _registry.get_endpoints(service_id) if _registry else None
        if endpoints is not None:
            self._write_json({
                "service_id": service_id,
                "endpoints": endpoints,
            })
        else:
            self._write_json({"error": f"Service '{service_id}' not found"}, 404)

    def _handle_get_health(self, service_id: str):
        health = _registry.get_health(service_id) if _registry else {"status": "UNKNOWN"}
        self._write_json(health)

    def _handle_get_compatibility(self, service_id: str):
        compat = _registry.get_compatibility(service_id) if _registry else {"status": "UNKNOWN"}
        self._write_json(compat)

    def _handle_server_health(self):
        uptime = time.time() - _start_time
        with _request_lock:
            count = _request_count
        self._write_json({
            "status": "UP",
            "version": DISCOVERY_SERVER_VERSION,
            "uptime_seconds": round(uptime, 2),
            "total_requests": count,
            "registry_version": PLATFORM_REGISTRY_VERSION,
        })

    def _handle_server_readiness(self):
        ready = _registry is not None and _lifecycle is not None
        service_count = len(_registry.list_services()) if _registry else 0
        self._write_json({
            "ready": ready,
            "services_registered": service_count,
            "version": DISCOVERY_SERVER_VERSION,
        })

    def _handle_metrics(self):
        uptime = time.time() - _start_time
        with _request_lock:
            count = _request_count
        service_count = len(_registry.list_services()) if _registry else 0
        evidence_count = _registry.evidence.get_chain_length() if _registry else 0

        # Prometheus-compatible text format
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; version=0.0.4; charset=utf-8")
        self.end_headers()
        metrics_text = (
            f"# HELP tantra_platform_uptime_seconds Discovery server uptime\n"
            f"# TYPE tantra_platform_uptime_seconds gauge\n"
            f"tantra_platform_uptime_seconds {uptime:.2f}\n"
            f"# HELP tantra_platform_requests_total Total requests to discovery server\n"
            f"# TYPE tantra_platform_requests_total counter\n"
            f"tantra_platform_requests_total {count}\n"
            f"# HELP tantra_platform_services_registered Number of registered platform services\n"
            f"# TYPE tantra_platform_services_registered gauge\n"
            f"tantra_platform_services_registered {service_count}\n"
            f"# HELP tantra_platform_evidence_chain_length Length of evidence chain\n"
            f"# TYPE tantra_platform_evidence_chain_length gauge\n"
            f"tantra_platform_evidence_chain_length {evidence_count}\n"
        )
        self.wfile.write(metrics_text.encode("utf-8"))

    def _handle_evidence(self):
        if _registry:
            evidence = _registry.evidence.get_all()
            chain_valid = _registry.evidence.verify_chain()
            self._write_json({
                "evidence": evidence,
                "chain_length": len(evidence),
                "chain_valid": chain_valid,
                "head_hash": _registry.evidence.get_head_hash(),
            })
        else:
            self._write_json({"evidence": [], "chain_length": 0, "chain_valid": True})

    def _handle_version(self):
        self._write_json({
            "discovery_server_version": DISCOVERY_SERVER_VERSION,
            "registry_version": PLATFORM_REGISTRY_VERSION,
            "api_version": "v1",
        })

    def _handle_negotiate(self):
        try:
            body = self._read_body()
        except Exception as e:
            self._write_json({"error": f"Invalid request body: {e}"}, 400)
            return

        service_id = body.get("service_id")
        requested_version = body.get("requested_version")

        if not service_id or not requested_version:
            self._write_json(
                {"error": "Missing 'service_id' and/or 'requested_version'"},
                400,
            )
            return

        result = _registry.negotiate_version(service_id, requested_version) if _registry else {
            "status": "UNKNOWN_SERVICE",
            "message": "Registry not initialised",
        }
        self._write_json(result)

    # -- Federation handler implementations ---------------------------------

    def _handle_register(self):
        """Authenticated service registration."""
        if not _federation_node:
            self._write_json({"error": "Federation not enabled"}, 503)
            return
        try:
            body = self._read_body()
        except Exception as e:
            self._write_json({"error": f"Invalid request body: {e}"}, 400)
            return

        record_data = body.get("record")
        if not record_data:
            self._write_json({"error": "Missing 'record' in body"}, 400)
            return

        try:
            record = PlatformServiceRecord(
                platform_service_id=record_data["platform_service_id"],
                capability_id=record_data.get("capability_id", ""),
                service_name=record_data.get("service_name", ""),
                version=record_data.get("version", "1.0.0"),
                provider=record_data.get("provider", ""),
                owner=record_data.get("owner", {}),
                runtime_type=record_data.get("runtime_type", "PROCESS"),
                service_classification=record_data.get("service_classification", "PLATFORM_SERVICE"),
                capability_category=record_data.get("capability_category", "VERIFICATION"),
                status=record_data.get("status", "ACTIVE"),
            )
        except (KeyError, TypeError) as e:
            self._write_json({"error": f"Invalid record: {e}"}, 400)
            return

        result = _federation_node.register_service_authenticated(record)
        status_code = 200 if result.get("status") in ("REGISTERED", "ALREADY_REGISTERED") else 403
        self._write_json(result, status_code)

    def _handle_heartbeat(self):
        """Lease renewal heartbeat."""
        if not _federation_node:
            self._write_json({"error": "Federation not enabled"}, 503)
            return
        try:
            body = self._read_body()
        except Exception as e:
            self._write_json({"error": f"Invalid request body: {e}"}, 400)
            return

        service_id = body.get("service_id")
        if not service_id:
            self._write_json({"error": "Missing 'service_id'"}, 400)
            return

        accepted = _federation_node.heartbeat.receive_heartbeat(service_id)
        if accepted:
            lease = _federation_node.heartbeat.get_lease(service_id)
            self._write_json({
                "status": "HEARTBEAT_ACCEPTED",
                "service_id": service_id,
                "lease": lease.to_dict() if lease else None,
            })
        else:
            self._write_json({
                "status": "HEARTBEAT_REJECTED",
                "service_id": service_id,
                "reason": "No active lease",
            }, 404)

    def _handle_revoke(self):
        """Service revocation."""
        if not _federation_node:
            self._write_json({"error": "Federation not enabled"}, 503)
            return
        try:
            body = self._read_body()
        except Exception as e:
            self._write_json({"error": f"Invalid request body: {e}"}, 400)
            return

        service_id = body.get("service_id")
        reason = body.get("reason", "Revoked via API")
        if not service_id:
            self._write_json({"error": "Missing 'service_id'"}, 400)
            return

        result = _federation_node.revoke_service(service_id, reason)
        self._write_json(result)

    def _handle_federation_status(self):
        """Federation topology and sync state."""
        if not _federation_node:
            self._write_json({"status": "STANDALONE", "federation_enabled": False})
            return
        self._write_json(_federation_node.get_federation_status())

    def _handle_federation_audit(self):
        """Federation audit log."""
        if not _federation_node:
            self._write_json({"events": [], "chain_valid": True})
            return
        events = _federation_node.get_audit_log()
        self._write_json({
            "events": events,
            "count": len(events),
            "chain_valid": _federation_node.audit_log.verify_chain(),
        })

    def _handle_federation_sync(self):
        """Trigger federation sync with all peers."""
        if not _federation_node:
            self._write_json({"error": "Federation not enabled"}, 503)
            return
        results = _federation_node.anti_entropy_sync()
        self._write_json({
            "status": "SYNC_COMPLETED",
            "results": results,
        })

    def _handle_list_certificates(self):
        """List active service certificates."""
        if not _federation_node:
            self._write_json({"certificates": []})
            return
        certs = _federation_node.ca.list_active_certificates()
        self._write_json({
            "certificates": [c.to_dict() for c in certs],
            "count": len(certs),
        })


# ---------------------------------------------------------------------------
# Server lifecycle
# ---------------------------------------------------------------------------

class PlatformDiscoveryServer:
    """Manages the HTTP server for the Platform Discovery API."""

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 9010,
        registry: PlatformServiceRegistry = None,
        lifecycle: LifecycleManager = None,
        federation_node=None,
    ):
        self.host = host
        self.port = port
        self.registry = registry
        self.lifecycle = lifecycle
        self.federation_node = federation_node
        self.server: Optional[HTTPServer] = None
        self.thread: Optional[threading.Thread] = None

    def start(self):
        """Start the discovery server in a background thread."""
        global _registry, _lifecycle, _federation_node, _start_time, _request_count
        _registry = self.registry
        _lifecycle = self.lifecycle
        _federation_node = self.federation_node
        _start_time = time.time()
        _request_count = 0

        self.server = HTTPServer((self.host, self.port), PlatformDiscoveryHandler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        logger.info(
            f"Platform Discovery Server v{DISCOVERY_SERVER_VERSION} started on "
            f"http://{self.host}:{self.port}/platform/v1/"
        )

    def stop(self):
        """Stop the discovery server."""
        if self.server:
            self.server.shutdown()
            self.server.server_close()
            self.server = None
        if self.thread:
            self.thread.join(timeout=5)
            self.thread = None
        logger.info("Platform Discovery Server stopped")

    @property
    def base_url(self) -> str:
        return f"http://{self.host}:{self.port}"
