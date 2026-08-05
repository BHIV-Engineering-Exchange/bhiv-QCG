"""
web_server.py — Phase 4: Operational Readiness Endpoints

Provides a lightweight, production-grade HTTP API for TANTRA ecosystem integration via FastAPI.
Endpoints:
- GET /health, /health/live, /health/ready : Health, readiness, and metrics.
- GET /capabilities   : Capability manifest and API contracts.
- POST /verify        : Synchronous end-to-end integration flow.
"""

import logging
from typing import Dict, Any

from fastapi import FastAPI, HTTPException, Request, Response, Header, Depends
from pydantic import BaseModel

from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter

# Setup OpenTelemetry
trace.set_tracer_provider(TracerProvider())
trace.get_tracer_provider().add_span_processor(
    BatchSpanProcessor(ConsoleSpanExporter())
)

from integration_harness import TANTRAIntegrationHarness
from integration_interfaces import CapabilityDiscoveryInterface

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

app = FastAPI(
    title="TANTRA Operational Readiness API",
    description="Quantum Communication Gateway (QCG) Ecosystem Integration API",
    version="1.0.0"
)

FastAPIInstrumentor.instrument_app(app)

# Global harness instance
harness = TANTRAIntegrationHarness()

class VerifyRequest(BaseModel):
    contract: Dict[str, Any]
    producer_public_key: str

@app.get("/health")
@app.get("/health/live")
@app.get("/health/ready")
async def health_check():
    """Returns health, readiness, and metrics for InsightFlow integration."""
    return harness.health_iface.get_health()

@app.get("/capabilities")
async def get_capabilities():
    """Serves the deterministic Capability Manifest for ecosystem discovery."""
    return CapabilityDiscoveryInterface.discover_capabilities()

@app.post("/verify")
async def verify_contract(payload: VerifyRequest):
    """
    Synchronous end-to-end integration flow.
    Primary ingestion pipeline for BHIV contracts from Pravah/NICAI.
    """
    success, result = harness.process_incoming_contract(payload.contract, payload.producer_public_key)
    
    if success:
        return result
    else:
        # If verification fails, return 422 Unprocessable Entity
        raise HTTPException(status_code=422, detail=result)

@app.get("/evidence/{hashed_trace}")
async def get_evidence(hashed_trace: str):
    """
    Evidence retrieval API (Live MDU provenance exchange).
    Returns the Merkle Inclusion Proof for a given execution trace.
    """
    # In a real deployed version, we query the live EvidenceLedger.
    # Currently simulating by providing a canonical proof mock for the requested trace.
    return {
        "trace_id": hashed_trace,
        "status": "INCLUDED",
        "merkle_proof": {
            "leaf_hash": f"{hashed_trace}_leaf",
            "sibling_hashes": ["hash_1", "hash_2"],
            "root_hash": "global_canonical_root"
        }
    }

@app.post("/gc/validate")
async def gc_validate_flow(payload: VerifyRequest, authorization: str = Header(None)):
    """
    Live GC validation flow.
    Applies strict constitutional policies without mutating state.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")
    
    # Delegate to the integration harness to verify cryptographic execution
    success, result = harness.process_incoming_contract(payload.contract, payload.producer_public_key, auth_token=authorization)
    if success:
        return {"status": "GC_APPROVED", "execution_result": result}
    else:
        raise HTTPException(status_code=403, detail={"status": "GC_REJECTED", "reason": result})

@app.get("/replay/lineage/{trace_id}")
async def replay_lineage(trace_id: str):
    """
    Replay authority integration API.
    Provides verifiable lineage paths for given execution artifacts.
    """
    verdict = harness.replay_auth.lookup(trace_id)
    if verdict:
        return {"message_id": trace_id, "verdict": verdict.to_dict()}
    raise HTTPException(status_code=404, detail="Trace ID not found in replay registry")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("web_server:app", host="0.0.0.0", port=8080, reload=False)
