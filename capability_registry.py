"""
capability_registry.py - Dynamic Capability Registry and Discovery Client.
Upgraded to FastAPI for monolithic Render deployment.
"""

import json
import logging
import threading
from typing import Dict, Any, List, Optional
from fastapi import FastAPI, HTTPException, Request, Response
from pydantic import BaseModel

# Setup basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("qcg.capability_registry")

app = FastAPI(title="Capability Registry API")

# In-memory database of registered capabilities
_registry_db: Dict[str, Dict[str, Any]] = {}
_registry_lock = threading.Lock()

def validate_capability_payload(payload: Dict[str, Any]) -> tuple[bool, str]:
    required_keys = [
        "capability_id", "capability_name", "owner", "version", "status", 
        "scope", "dependencies", "attachment_rules", "authority_limits", 
        "inputs", "outputs", "consumers", "documentation_reference"
    ]
    for key in required_keys:
        if key not in payload:
            return False, f"Missing required key: {key}"
            
    # Validate nested structures
    owner = payload.get("owner", {})
    if not isinstance(owner, dict) or "team" not in owner or "contact" not in owner:
        return False, "Invalid 'owner' structure: must contain 'team' and 'contact'."
        
    attachment = payload.get("attachment_rules", {})
    if not isinstance(attachment, dict) or "attachment_type" not in attachment or "protocol" not in attachment:
        return False, "Invalid 'attachment_rules' structure: must contain 'attachment_type' and 'protocol'."
        
    auth = payload.get("authority_limits", {})
    if not isinstance(auth, dict) or "owns" not in auth or "does_not_own" not in auth:
        return False, "Invalid 'authority_limits' structure: must contain 'owns' and 'does_not_own'."
        
    return True, ""

@app.get("/capabilities")
async def list_capabilities():
    with _registry_lock:
        return list(_registry_db.values())

@app.get("/capabilities/{cap_id}")
async def get_capability(cap_id: str):
    with _registry_lock:
        if cap_id in _registry_db:
            return _registry_db[cap_id]
        raise HTTPException(status_code=404, detail=f"Capability {cap_id} not found")

@app.get("/discover/{cap_name}")
async def discover_capability(cap_name: str):
    with _registry_lock:
        for cap in _registry_db.values():
            if cap["capability_name"].upper() == cap_name.upper():
                return cap
    raise HTTPException(status_code=404, detail=f"Capability with name {cap_name} not found")

@app.post("/register")
async def register_capability(request: Request):
    try:
        payload = await request.json()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSON: {e}")

    valid, err_msg = validate_capability_payload(payload)
    if not valid:
        raise HTTPException(status_code=400, detail=f"Schema Validation Failure: {err_msg}")

    cap_id = payload["capability_id"]
    with _registry_lock:
        _registry_db[cap_id] = payload
    
    logger.info(f"Registered capability '{payload['capability_name']}' version {payload['version']} (ID: {cap_id})")
    return {"status": "REGISTERED", "capability_id": cap_id}

import urllib.request
import urllib.error

class CapabilityRegistryClient:
    def __init__(self, registry_url: str = "http://127.0.0.1:9000"):
        self.registry_url = registry_url

    def register(self, capability_data: Dict[str, Any]) -> bool:
        """Register a service capability with the centralized registry."""
        url = f"{self.registry_url}/register"
        data = json.dumps(capability_data).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={'Content-Type': 'application/json'}
        )
        try:
            with urllib.request.urlopen(req, timeout=5) as response:
                res_body = json.loads(response.read().decode("utf-8"))
                return res_body.get("status") == "REGISTERED"
        except Exception as e:
            logger.error(f"Failed to register capability: {e}")
            return False

    def discover(self, capability_name: str) -> Optional[Dict[str, Any]]:
        """Query the registry to resolve a capability's metadata and endpoint."""
        url = f"{self.registry_url}/discover/{capability_name}"
        try:
            with urllib.request.urlopen(url, timeout=5) as response:
                return json.loads(response.read().decode("utf-8"))
        except Exception as e:
            logger.error(f"Failed to discover capability '{capability_name}': {e}")
            return None
