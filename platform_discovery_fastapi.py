"""
platform_discovery_fastapi.py - FastAPI wrapper for Platform Service Discovery
"""

import time
from typing import Dict, Any, Optional, List
from fastapi import FastAPI, HTTPException, Request, Response
from pydantic import BaseModel

from platform_service_registry import PlatformServiceRegistry, RegistrationEvidenceRecorder, PLATFORM_REGISTRY_VERSION
from platform_lifecycle_manager import LifecycleManager

app = FastAPI(title="Platform Service Discovery API", version="2.0.0")

# Global instances for the Monolith
registry = PlatformServiceRegistry(evidence_recorder=RegistrationEvidenceRecorder())
lifecycle = LifecycleManager()
_start_time = time.time()
_request_count = 0

@app.middleware("http")
async def count_requests(request: Request, call_next):
    global _request_count
    _request_count += 1
    response = await call_next(request)
    response.headers["X-Platform-Version"] = "2.0.0"
    return response

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
    return {
        "status": "UP",
        "version": "2.0.0",
        "uptime_seconds": round(time.time() - _start_time, 2),
        "total_requests": _request_count,
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
async def get_metrics():
    uptime = time.time() - _start_time
    service_count = len(registry.list_services())
    metrics_text = (
        f"# HELP tantra_platform_uptime_seconds Discovery server uptime\n"
        f"# TYPE tantra_platform_uptime_seconds gauge\n"
        f"tantra_platform_uptime_seconds {uptime:.2f}\n"
        f"# HELP tantra_platform_requests_total Total requests to discovery server\n"
        f"# TYPE tantra_platform_requests_total counter\n"
        f"tantra_platform_requests_total {_request_count}\n"
        f"# HELP tantra_platform_services_registered Number of registered services\n"
        f"# TYPE tantra_platform_services_registered gauge\n"
        f"tantra_platform_services_registered {service_count}\n"
    )
    return Response(content=metrics_text, media_type="text/plain")

@app.get("/v1/evidence")
async def get_evidence():
    return {
        "chain_length": registry.evidence.get_chain_length(),
        "tail_hash": registry.evidence.get_tail_hash(),
        "entries": [e.to_dict() for e in registry.evidence.entries]
    }

# -- POST routes --

@app.post("/v1/register")
async def register(request: Request):
    try:
        data = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")
    
    service_id = data.get("service_id")
    if not service_id:
        raise HTTPException(status_code=400, detail="Missing service_id")

    # Convert incoming data to a PlatformServiceRecord
    try:
        # Filter out fields that are not part of the dataclass to avoid TypeError
        import inspect
        from platform_service_registry import PlatformServiceRecord
        
        valid_fields = set(inspect.signature(PlatformServiceRecord).parameters.keys())
        filtered_data = {k: v for k, v in data.items() if k in valid_fields}
        
        record = PlatformServiceRecord(**filtered_data)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid PlatformServiceRecord: {e}")

    try:
        # Call register_service which returns a dictionary, not a tuple
        result = registry.register_service(record)
        
        if result.get("status") == "REGISTERED" or result.get("status") == "ALREADY_REGISTERED":
            return result
        else:
            raise HTTPException(status_code=400, detail=result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Registration failed: {e}")

@app.post("/v1/heartbeat")
async def heartbeat(request: Request):
    try:
        data = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")
    service_id = data.get("service_id")
    status = data.get("status", "ACTIVE")
    if not service_id:
        raise HTTPException(status_code=400, detail="Missing service_id")
    
    registry.update_heartbeat(service_id, status)
    return {"status": "ACK", "service_id": service_id}

@app.post("/v1/revoke")
async def revoke(request: Request):
    try:
        data = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")
    service_id = data.get("service_id")
    reason = data.get("reason", "Revoked by request")
    if not service_id:
        raise HTTPException(status_code=400, detail="Missing service_id")
    
    success, msg = registry.revoke_service(service_id, reason)
    if success:
        return {"status": "REVOKED", "service_id": service_id}
    else:
        raise HTTPException(status_code=404, detail=msg)

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
