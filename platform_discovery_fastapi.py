"""
platform_discovery_fastapi.py - FastAPI wrapper for Platform Service Discovery
"""

import time
import logging
import re
from typing import Dict, Any, Optional, List
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel
import config
from metrics import get_metrics
from middleware import ErrorBoundaryMiddleware, RequestTracingMiddleware, SecurityHeadersMiddleware

from platform_service_registry import PlatformServiceRegistry, RegistrationEvidenceRecorder, PLATFORM_REGISTRY_VERSION
from platform_lifecycle_manager import LifecycleManager

app = FastAPI(title="Platform Service Discovery API", version="2.0.0")

# Register middleware (order matters)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(ErrorBoundaryMiddleware)
app.add_middleware(RequestTracingMiddleware)

# Global instances for the Monolith
registry = PlatformServiceRegistry(evidence_recorder=RegistrationEvidenceRecorder())
lifecycle = LifecycleManager()
_start_time = time.time()

@app.on_event("startup")
async def startup_event():
    config.validate()
    metrics = get_metrics()
    metrics.set_component_health("platform_registry", "UP")
    logging.info("Platform Service Discovery API started")

@app.on_event("shutdown")
async def shutdown_event():
    logging.info("Platform Service Discovery API shutting down")

def _validate_payload_bounds(data: dict):
    def count_keys(d):
        count = 0
        if isinstance(d, dict):
            for k, v in d.items():
                count += 1 + count_keys(v)
        elif isinstance(d, list):
            for item in d:
                count += count_keys(item)
        return count
    if count_keys(data) > config.INPUT_PAYLOAD_MAX_KEYS:
        raise HTTPException(status_code=413, detail="Payload exceeds maximum keys limit")

def _sanitize_id(id_str: str) -> str:
    if not id_str:
        return ""
    id_str = str(id_str)[:config.INPUT_TRACE_ID_MAX_LENGTH]
    id_str = re.sub(r'[\x00-\x1f\x7f]', '', id_str)
    return id_str.strip()

# -- GET routes --

@app.get("/v1/services")
async def list_services():
    services = registry.list_services()
    return {
        "services": services,
        "count": len(services),
        "registry_version": PLATFORM_REGISTRY_VERSION,
    }

@app.get("/v1/services/{service_id}")
async def get_service(service_id: str):
    record = registry.get_service(service_id)
    if record:
        return record
    raise HTTPException(status_code=404, detail=f"Service '{service_id}' not found")

@app.get("/v1/services/{service_id}/versions")
async def get_versions(service_id: str):
    if not registry.get_service(service_id):
        raise HTTPException(status_code=404, detail=f"Service '{service_id}' not found")
    return registry.get_versions(service_id)

@app.get("/v1/services/{service_id}/metadata")
async def get_metadata(service_id: str):
    metadata = registry.get_metadata(service_id)
    if metadata:
        return metadata
    raise HTTPException(status_code=404, detail=f"Service '{service_id}' not found")

@app.get("/v1/services/{service_id}/contracts")
async def get_contracts(service_id: str):
    manifest = registry.get_manifest(service_id)
    if manifest:
        operations = manifest.get("supported_operations", [])
        return {
            "service_id": service_id,
            "contracts": operations,
            "count": len(operations),
        }
    raise HTTPException(status_code=404, detail=f"Manifest for '{service_id}' not found")

@app.get("/v1/services/{service_id}/endpoints")
async def get_endpoints(service_id: str):
    endpoints = registry.get_endpoints(service_id)
    if endpoints is not None:
        return {
            "service_id": service_id,
            "endpoints": endpoints,
        }
    raise HTTPException(status_code=404, detail=f"Service '{service_id}' not found")

@app.get("/v1/services/{service_id}/health")
async def get_service_health(service_id: str):
    return registry.get_health(service_id) or {"status": "UNKNOWN"}

@app.get("/v1/services/{service_id}/compatibility")
async def get_compatibility(service_id: str):
    return registry.get_compatibility(service_id) or {"status": "UNKNOWN"}

@app.get("/v1/health")
async def server_health():
    metrics = get_metrics()
    return {
        "status": "UP",
        "version": "2.0.0",
        "uptime_seconds": round(time.time() - _start_time, 2),
        "total_requests": metrics.total_requests,
        "registry_version": PLATFORM_REGISTRY_VERSION,
    }

@app.get("/v1/health/live")
async def server_readiness():
    return {
        "ready": True,
        "services_registered": len(registry.list_services()),
        "version": "2.0.0",
    }

@app.get("/v1/metrics")
async def get_metrics_endpoint():
    metrics = get_metrics()
    uptime = time.time() - _start_time
    service_count = len(registry.list_services())
    registry_metrics = (
        f"# HELP tantra_platform_services_registered Number of registered services\n"
        f"# TYPE tantra_platform_services_registered gauge\n"
        f"tantra_platform_services_registered {service_count}\n"
    )
    combined = metrics.to_prometheus() + "\n" + registry_metrics
    return PlainTextResponse(content=combined, media_type="text/plain; version=0.0.4; charset=utf-8")

@app.get("/v1/evidence")
async def get_evidence():
    return {
        "chain_length": registry.evidence.get_chain_length(),
        "head_hash": registry.evidence.get_head_hash(),
        "chain_valid": registry.evidence.verify_chain(),
        "entries": registry.evidence.get_all(),
    }

# -- POST routes --

@app.post("/v1/negotiate")
async def negotiate_version(request: Request):
    """Version negotiation endpoint — delegates to registry.negotiate_version()."""
    if int(request.headers.get("content-length", 0)) > config.MAX_REQUEST_BODY_SIZE:
        raise HTTPException(status_code=413, detail="Request body too large")
    try:
        data = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")
    
    _validate_payload_bounds(data)

    service_id = _sanitize_id(data.get("service_id"))
    requested_version = data.get("version") or data.get("requested_version")
    if not service_id or not requested_version:
        raise HTTPException(
            status_code=400,
            detail="Missing required fields: 'service_id' and 'version' (or 'requested_version')"
        )

    record = registry.get_service(service_id)
    if not record:
        return {
            "service_id": service_id,
            "status": "UNKNOWN_SERVICE",
            "requested_version": requested_version,
            "negotiated_version": None,
            "message": f"Service '{service_id}' not found in registry",
        }

    result = registry.negotiate_version(service_id, requested_version)
    return result


@app.post("/v1/register")
async def register(request: Request):
    if int(request.headers.get("content-length", 0)) > config.MAX_REQUEST_BODY_SIZE:
        raise HTTPException(status_code=413, detail="Request body too large")
    try:
        data = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")
    
    _validate_payload_bounds(data)
    
    record_data = data.get("record", data)
    service_id = _sanitize_id(record_data.get("platform_service_id") or record_data.get("service_id") or data.get("service_id"))
    if not service_id:
        raise HTTPException(status_code=400, detail="Missing service_id or platform_service_id")

    try:
        from platform_service_registry import PlatformServiceRecord
        record = PlatformServiceRecord(
            platform_service_id=service_id,
            capability_id=record_data.get("capability_id", service_id),
            service_name=record_data.get("service_name", service_id),
            version=record_data.get("version", "1.0.0"),
            provider=record_data.get("provider", "Generic Provider"),
            owner=record_data.get("owner", {}),
            runtime_type=record_data.get("runtime_type", "PROCESS"),
            service_classification=record_data.get("service_classification", "DOMAIN_SERVICE"),
            capability_category=record_data.get("capability_category", "EXECUTION"),
            status=record_data.get("status", "ACTIVE"),
            description=record_data.get("description", ""),
            tags=record_data.get("tags", []),
            endpoints=record_data.get("endpoints", {}),
            dependencies=record_data.get("dependencies", []),
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid PlatformServiceRecord: {str(e)}")

    try:
        result = registry.register_service(record)
        if isinstance(result, dict) and "status" in result:
            if result.get("status") in ["REGISTERED", "ALREADY_REGISTERED"]:
                return result
            else:
                raise HTTPException(status_code=400, detail=result)
        return {"status": "REGISTERED", "service_id": service_id, "details": result}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Registration failed: {str(e)}")

@app.post("/v1/heartbeat")
async def heartbeat(request: Request):
    if int(request.headers.get("content-length", 0)) > config.MAX_REQUEST_BODY_SIZE:
        raise HTTPException(status_code=413, detail="Request body too large")
    try:
        data = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")
    _validate_payload_bounds(data)
    service_id = _sanitize_id(data.get("service_id"))
    status = data.get("status", "ACTIVE")
    if not service_id:
        raise HTTPException(status_code=400, detail="Missing service_id")
    
    registry.set_status(service_id, status)
    return {"status": "ACK", "service_id": service_id}

@app.post("/v1/revoke")
async def revoke(request: Request):
    if int(request.headers.get("content-length", 0)) > config.MAX_REQUEST_BODY_SIZE:
        raise HTTPException(status_code=413, detail="Request body too large")
    try:
        data = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")
    _validate_payload_bounds(data)
    service_id = _sanitize_id(data.get("service_id"))
    reason = data.get("reason", "Revoked by request")
    if not service_id:
        raise HTTPException(status_code=400, detail="Missing service_id")
    
    result = registry.remove_service(service_id, reason)
    if result.get("status") == "REMOVED":
        return {"status": "REVOKED", "service_id": service_id}
    else:
        raise HTTPException(status_code=404, detail="Service not found")

@app.post("/v1/services/{service_id}")
async def mock_execute(service_id: str):
    record = registry.get_service(service_id)
    if record:
        return {
            "status": "EXECUTED",
            "service_id": service_id,
            "ack": True,
            "payload_received": True,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S+00:00", time.gmtime())
        }
    raise HTTPException(status_code=404, detail=f"Service '{service_id}' not found")
