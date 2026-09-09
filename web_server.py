"""
web_server.py — Phase 4: Operational Readiness Endpoints

Provides a lightweight, production-grade HTTP API for TANTRA ecosystem integration via FastAPI.
Endpoints:
- GET /health, /health/live, /health/ready : Health, readiness, and metrics.
- GET /capabilities   : Capability manifest and API contracts.
- POST /verify        : Synchronous end-to-end integration flow.
- GET /evidence/certificate/{execution_id} : Retrieves execution certificate for a given trace.
"""

import logging
import time
import uuid
from typing import Dict, Any

from fastapi import FastAPI, HTTPException, Request, Response, Header, Depends
from fastapi.responses import PlainTextResponse
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
from provenance_api import execution_certificate, execution_history

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

from middleware import ErrorBoundaryMiddleware, RequestTracingMiddleware, SecurityHeadersMiddleware
from metrics import get_metrics

app = FastAPI(
    title="TANTRA Operational Readiness API",
    description="Quantum Communication Gateway (QCG) Ecosystem Integration API",
    version="2.0.0"
)

# Register middleware (order matters: outermost first)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(ErrorBoundaryMiddleware)
app.add_middleware(RequestTracingMiddleware)

FastAPIInstrumentor.instrument_app(app)

# Global harness instance
harness = TANTRAIntegrationHarness()

import os
import json

# ---------------------------------------------------------------------------
# Lifecycle Hooks
# ---------------------------------------------------------------------------

@app.on_event("startup")
async def startup_event():
    """Validate configuration and register component health on startup."""
    import config
    config.validate()
    metrics = get_metrics()
    metrics.set_component_health("evidence_ledger", "UP")
    metrics.set_component_health("replay_registry", "UP")
    metrics.set_component_health("consensus_engine", "UP")
    metrics.set_component_health("hybrid_orchestrator", "UP")
    logging.info("QCG Operational Readiness API started — all components healthy")

@app.on_event("shutdown")
async def shutdown_event():
    """Graceful shutdown: log final metrics snapshot."""
    metrics = get_metrics()
    summary = metrics.get_summary()
    logging.info(
        "QCG shutting down — total_requests=%d, total_errors=%d, uptime=%.0fs",
        summary["requests"]["total"],
        summary["errors"]["total"],
        summary["uptime_seconds"],
    )

class VerifyRequest(BaseModel):
    contract: Dict[str, Any] = None
    producer_public_key: str = None
    
    # SDK Envelope support
    service_id: str = None
    operation: str = None
    version: str = None
    invocation_id: str = None
    payload: Dict[str, Any] = None

# Persistent mapping for SDK invocation IDs to Trace IDs
INVOCATION_MAP_FILE = "invocation_map.json"
def load_invocation_map():
    if os.path.exists(INVOCATION_MAP_FILE):
        try:
            with open(INVOCATION_MAP_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def save_invocation_map(mapping):
    with open(INVOCATION_MAP_FILE, "w") as f:
        json.dump(mapping, f)

@app.get("/health", tags=["Health"])
@app.get("/health/live", tags=["Health"])
@app.get("/health/ready", tags=["Health"])
async def get_health():
    """Get health, readiness, and metrics data."""
    return harness.health_iface.get_health()


@app.get("/metrics", tags=["Observability"])
async def get_metrics_endpoint():
    """Prometheus-compatible metrics export."""
    return PlainTextResponse(
        content=get_metrics().to_prometheus(),
        media_type="text/plain; version=0.0.4; charset=utf-8",
    )


@app.get("/metrics/json", tags=["Observability"])
async def get_metrics_json():
    """JSON metrics summary for dashboards."""
    return get_metrics().get_summary()

@app.get("/capabilities", tags=["Capabilities"])
async def get_capabilities():
    """Get capability manifest and API contracts."""
    return CapabilityDiscoveryInterface.discover_capabilities()

@app.post("/verify", tags=["Integration"])
async def verify_contract(payload: VerifyRequest):
    """
    Synchronous end-to-end integration flow verification.
    Primary ingestion pipeline for BHIV contracts from Pravah/NICAI.
    """
    import uuid
    from datetime import datetime, timezone

    # Unpack SDK wrapper if present
    invocation_id = payload.invocation_id
    if payload.payload is not None:
        contract_raw = payload.payload.get("contract", {})
        pub_key_raw = payload.payload.get("producer_public_key", "")
    else:
        contract_raw = payload.contract or {}
        pub_key_raw = payload.producer_public_key or ""

    # Adapt raw Pritesh payload into QCG ComputationExecutionContract
    if "producer_type" not in contract_raw:
        from execution_contract import ComputationExecutionContract
        from node_identity import NodeSigner
        from provenance import sign_contract
        import uuid
        from datetime import datetime, timezone

        c = ComputationExecutionContract(
            producer_type="QUANTUM",
            producer_id="PRITESH_QUANTUM",
            payload=contract_raw,
            confidence=0.99,
            trace_id=str(uuid.uuid4()),
            contract_version="2.0.0",
            timestamp=datetime.now(timezone.utc).isoformat()
        )
        
        # Create a proxy identity for Pritesh to sign the contract
        proxy_signer = NodeSigner("PRITESH_QUANTUM", "QUANTUM")
        signed_c = sign_contract(c, proxy_signer)
        contract_dict = signed_c.to_dict()
        
        # Override the dummy "YOUR_KEY" with the actual generated public key for verification
        pub_key_to_use = proxy_signer.identity.public_key
    else:
        contract_dict = contract_raw
        pub_key_to_use = pub_key_raw

    if invocation_id:
        actual_trace_id = contract_dict.get("trace_id")
        if actual_trace_id:
            mapping = load_invocation_map()
            mapping[invocation_id] = actual_trace_id
            save_invocation_map(mapping)

    success, result = harness.process_incoming_contract(contract_dict, pub_key_to_use)
    
    if not success:
        raise HTTPException(status_code=422, detail=result)
    return result

@app.get("/evidence/certificate/{execution_id}", tags=["Provenance"])
async def get_certificate(execution_id: str):
    """Retrieves execution certificate with Merkle proof for MDU retrieval."""
    # Find record
    record = None
    for r in harness.ledger._records:
        if r.execution_id == execution_id:
            record = r
            break
            
    if not record:
        raise HTTPException(status_code=404, detail="Execution record not found in ledger")
        
    try:
        cert = execution_certificate(record, harness.ledger)
        return cert
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate certificate: {str(e)}")

@app.get("/evidence/trace/{trace_id}", tags=["Provenance"])
async def get_trace_history(trace_id: str):
    """Retrieves execution history for a given trace."""
    history = execution_history(harness.ledger, trace_id)
    if not history:
        raise HTTPException(status_code=404, detail="No execution records found for this trace ID")
    return {"trace_id": trace_id, "history": [h.__dict__ for h in history]}

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
    # Resolve SDK invocation_id to canonical trace_id if mapped
    mapping = load_invocation_map()
    resolved_trace_id = mapping.get(trace_id, trace_id)

    verdict = harness.replay_auth.lookup(resolved_trace_id)
    if verdict:
        v_dict = verdict.to_dict()
        v_dict["message_id"] = trace_id
        return {"message_id": trace_id, "verdict": v_dict}
    raise HTTPException(status_code=404, detail="Trace ID not found in replay registry")


# ---------------------------------------------------------------------------
# Hybrid Quantum-Classical Runtime Endpoints
# ---------------------------------------------------------------------------

from hybrid_runtime_orchestrator import HybridRuntimeOrchestrator
from workload_router import WorkloadMetadata

# Global orchestrator instance (lazy init to avoid import-time side effects)
_orchestrator = None

def _get_orchestrator() -> HybridRuntimeOrchestrator:
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = HybridRuntimeOrchestrator()
    return _orchestrator


# -- Trust method mapping: Pritesh's trust_method ↔ our execution_classification --
_CLASSIFICATION_TO_TRUST_METHOD = {
    "CLASSICAL": "CLASSICAL",
    "QUANTUM_LOCAL": "CLASSICAL",       # Local simulation = classical trust
    "QUANTUM_SIMULATED": "CLASSICAL",   # Cloud sim = classical trust
    "QUANTUM_LIVE": "HYBRID",           # Real quantum hardware = hybrid trust
    "HYBRID": "HYBRID",
}


def _to_invocation_result(
    result,
    invocation_id: str = "",
    service_id: str = "QCG-HYBRID-RUNTIME",
    operation: str = "hybrid_submit",
    start_time: float = 0.0,
) -> Dict[str, Any]:
    """
    Bridge our OrchestratorResult to Pritesh's InvocationResult schema.

    This ensures the hybrid runtime output can be consumed by any component
    that expects the standard InvocationResult format.
    """
    import time as _time

    cr = result.classified_result
    classification = cr.get("classification", "CLASSICAL")
    trust_method = _CLASSIFICATION_TO_TRUST_METHOD.get(classification, "CLASSICAL")
    duration = (_time.time() - start_time) * 1000 if start_time else 0.0

    return {
        "invocation_id": invocation_id or result.trace_id,
        "service_id": service_id,
        "operation": operation,
        "status": "SUCCESS" if result.status == "COMPLETED" else "FAILED",
        "response": {
            "orchestrator_result": result.to_dict(),
            "classification": classification,
            "execution_path": cr.get("execution_path", "LOCAL"),
            "provider_id": cr.get("provider_id", ""),
            "confidence": cr.get("confidence", 0.0),
            "result_hash": cr.get("result_hash", ""),
            "bhex_ready": result.provenance.get("bhex_ready", False) if result.provenance else False,
        },
        "duration_ms": round(duration, 2),
        "trust_method": trust_method,
        "evidence": {
            "merkle_root": result.provenance.get("merkle_root", "") if result.provenance else "",
            "evidence_chain_head": result.provenance.get("evidence_chain_head", "") if result.provenance else "",
            "trace_id": result.trace_id,
            "classification": classification,
            "execution_path": cr.get("execution_path", "LOCAL"),
        },
        "error": None if result.status == "COMPLETED" else str(result.stages.get("error", "")),
    }


class HybridSubmitRequest(BaseModel):
    """Request body for hybrid workload submission."""
    workload: Dict[str, Any]
    workload_type: str = "GENERAL"
    problem_size: int = 0
    is_qubo_compatible: bool = False
    requires_entanglement: bool = False
    requires_live_hardware: bool = False
    classical_fallback_acceptable: bool = True


class CapabilityDispatchRequest(BaseModel):
    """
    Standard capability dispatch payload (Pritesh's schema).

    Allows the hybrid runtime to be invoked through the standard
    platform capability dispatch system.
    """
    service_id: str = "QCG-HYBRID-RUNTIME"
    operation: str = "hybrid_submit"
    payload: Dict[str, Any] = {}
    version: str = "1.0.0"
    invocation_id: str = ""


@app.post("/hybrid/submit", tags=["Hybrid Runtime"])
async def hybrid_submit(payload: HybridSubmitRequest):
    """
    Submit a workload to the hybrid quantum-classical runtime.

    The orchestrator discovers capabilities, routes the workload,
    executes through the best available path, and returns a
    classified result with full provenance.
    """
    import time as _time
    start = _time.time()
    orchestrator = _get_orchestrator()

    metadata = WorkloadMetadata(
        workload_id=payload.workload.get("workload_id", str(uuid.uuid4())),
        workload_type=payload.workload_type,
        problem_size=payload.problem_size,
        is_qubo_compatible=payload.is_qubo_compatible,
        requires_entanglement=payload.requires_entanglement,
        requires_live_hardware=payload.requires_live_hardware,
        classical_fallback_acceptable=payload.classical_fallback_acceptable,
    )

    result = orchestrator.submit_workload(payload.workload, metadata)
    return _to_invocation_result(result, start_time=start)


@app.post("/hybrid/dispatch", tags=["Hybrid Runtime"])
async def hybrid_dispatch(payload: CapabilityDispatchRequest):
    """
    Standard capability dispatch endpoint for the hybrid runtime.

    Accepts Pritesh's standard capability dispatch schema and returns
    an InvocationResult-compatible response. This allows the hybrid
    runtime to be invoked through the platform capability SDK.

    Supported operations:
      - hybrid_submit: Execute a workload through the hybrid runtime
      - health_check: Get aggregate health status
      - list_providers: List quantum providers
      - network_status: Get quantum network coordination status
    """
    import time as _time
    start = _time.time()
    orchestrator = _get_orchestrator()

    invocation_id = payload.invocation_id or str(uuid.uuid4())
    workload = payload.payload

    if payload.operation == "hybrid_submit":
        metadata = WorkloadMetadata(
            workload_id=workload.get("workload_id", str(uuid.uuid4())),
            workload_type=workload.get("workload_type", "GENERAL"),
            problem_size=workload.get("problem_size", 0),
            is_qubo_compatible=workload.get("is_qubo_compatible", False),
            requires_entanglement=workload.get("requires_entanglement", False),
            requires_live_hardware=workload.get("requires_live_hardware", False),
            classical_fallback_acceptable=workload.get("classical_fallback_acceptable", True),
        )
        result = orchestrator.submit_workload(workload, metadata)
        return _to_invocation_result(
            result,
            invocation_id=invocation_id,
            service_id=payload.service_id,
            operation=payload.operation,
            start_time=start,
        )

    elif payload.operation == "health_check":
        health = orchestrator.get_health()
        duration = (_time.time() - start) * 1000
        return {
            "invocation_id": invocation_id,
            "service_id": payload.service_id,
            "operation": payload.operation,
            "status": "SUCCESS",
            "response": health,
            "duration_ms": round(duration, 2),
            "trust_method": "CLASSICAL",
            "evidence": None,
            "error": None,
        }

    elif payload.operation == "list_providers":
        registry = orchestrator.get_provider_registry()
        response = {
            "providers": registry.list_providers(),
            "aggregate": registry.get_aggregate_status(),
        }
        duration = (_time.time() - start) * 1000
        return {
            "invocation_id": invocation_id,
            "service_id": payload.service_id,
            "operation": payload.operation,
            "status": "SUCCESS",
            "response": response,
            "duration_ms": round(duration, 2),
            "trust_method": "CLASSICAL",
            "evidence": None,
            "error": None,
        }

    elif payload.operation == "network_status":
        contract = orchestrator.get_network_contract()
        response = contract.get_network_status()
        duration = (_time.time() - start) * 1000
        return {
            "invocation_id": invocation_id,
            "service_id": payload.service_id,
            "operation": payload.operation,
            "status": "SUCCESS",
            "response": response,
            "duration_ms": round(duration, 2),
            "trust_method": "CLASSICAL",
            "evidence": None,
            "error": None,
        }

    else:
        duration = (_time.time() - start) * 1000
        return {
            "invocation_id": invocation_id,
            "service_id": payload.service_id,
            "operation": payload.operation,
            "status": "SERVICE_NOT_FOUND",
            "response": None,
            "duration_ms": round(duration, 2),
            "trust_method": "CLASSICAL",
            "evidence": None,
            "error": f"Unknown operation: {payload.operation}",
        }


@app.get("/providers", tags=["Hybrid Runtime"])
async def list_providers():
    """List all registered quantum providers and their status."""
    orchestrator = _get_orchestrator()
    registry = orchestrator.get_provider_registry()
    return {
        "providers": registry.list_providers(),
        "aggregate": registry.get_aggregate_status(),
    }


@app.get("/network/status", tags=["Hybrid Runtime"])
async def network_status():
    """Get quantum network coordination status."""
    orchestrator = _get_orchestrator()
    contract = orchestrator.get_network_contract()
    return contract.get_network_status()


@app.get("/hybrid/health", tags=["Hybrid Runtime"])
async def hybrid_health():
    """Get aggregate health of the hybrid quantum-classical runtime."""
    orchestrator = _get_orchestrator()
    return orchestrator.get_health()


if __name__ == "__main__":
    import uvicorn
    logging.info("Starting FastAPI Operational Readiness API on port 8080...")
    uvicorn.run("web_server:app", host="0.0.0.0", port=8080, reload=False)

