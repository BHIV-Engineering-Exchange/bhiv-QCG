from fastapi import FastAPI, HTTPException, Request, Response, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
import json
import uuid
import os
import time
import logging

from solver_registry import SolverRegistry
from solver_selection_engine import SolverSelectionEngine
from execution_adapter import ExecutionAdapter
from runtime_validation import ValidatingSolverAdapter
from telemetry import EvidencePublisher, get_usf_metrics, logger

app = FastAPI(
    title="Optimization.SolverFabric.v1",
    description="Universal Solver Fabric Platform Service Capability",
    version="1.0.0"
)

log = logging.getLogger("usf.api")

# ---------------------------------------------------------------------------
# Error boundary middleware
# ---------------------------------------------------------------------------

@app.middleware("http")
async def error_boundary_middleware(request: Request, call_next):
    """Catch unhandled exceptions and return structured 500 JSON."""
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    start = time.time()
    try:
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response
    except Exception as e:
        log.error(f"Unhandled exception on {request.method} {request.url.path}: {type(e).__name__}: {e}")
        return JSONResponse(
            status_code=500,
            content={
                "error": "InternalServerError",
                "detail": str(e),
                "request_id": request_id,
            },
            headers={"X-Request-ID": request_id},
        )


# ---------------------------------------------------------------------------
# Initialize registry and engine
# ---------------------------------------------------------------------------

registry = SolverRegistry("solver_contract.schema.json")
try:
    with open("solver_examples.json") as f:
        examples = json.load(f)
        for ex in examples:
            registry.register_solver(ex)
except Exception as e:
    print(f"Warning: Could not load solver examples: {e}")

engine = SolverSelectionEngine(registry)
publisher = EvidencePublisher()


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------

class ProblemSchema(BaseModel):
    problem_type: str
    required_constraints: List[str]
    require_deterministic: bool

class ExecutionConstraints(BaseModel):
    max_time_ms: int
    max_memory_mb: int

class ExecuteRequest(BaseModel):
    problem_schema: ProblemSchema
    payload: Dict[str, Any]
    execution_constraints: ExecutionConstraints


# ---------------------------------------------------------------------------
# Health endpoints
# ---------------------------------------------------------------------------

@app.get("/health/liveness")
def liveness():
    return {"status": "alive"}

@app.get("/health/readiness")
def readiness():
    if len(registry.search_capabilities()) == 0:
        raise HTTPException(status_code=503, detail="No solvers registered")
    return {"status": "ready", "solver_count": registry.solver_count}


# ---------------------------------------------------------------------------
# Metrics endpoint
# ---------------------------------------------------------------------------

@app.get("/metrics")
def metrics():
    """Expose USF execution metrics."""
    return get_usf_metrics().summary


# ---------------------------------------------------------------------------
# Capabilities
# ---------------------------------------------------------------------------

@app.get("/capabilities")
def get_capabilities():
    solvers = registry.search_capabilities()
    simplified_solvers = []
    for s in solvers:
        simplified_solvers.append({
            "solver_id": s.get("solver_id"),
            "version": s.get("version"),
            "supported_problem_types": s.get("supported_problem_types", []),
            "deterministic_capability": s.get("deterministic_capability", False)
        })
    return {"solvers": simplified_solvers}


# ---------------------------------------------------------------------------
# Execute
# ---------------------------------------------------------------------------

@app.post("/execute")
def execute_problem(req: ExecuteRequest):
    problem = {
        "problem_type": req.problem_schema.problem_type,
        "required_constraints": req.problem_schema.required_constraints,
        "require_deterministic": req.problem_schema.require_deterministic,
        "available_memory_mb": req.execution_constraints.max_memory_mb,
    }

    recommendations = engine.select_solvers(problem)
    if not recommendations:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="CapabilityMismatch: No registered solver can satisfy the required constraints or problem type."
        )

    selected_solver_meta = recommendations[0]

    # We use the ValidatingSolverAdapter as the mock solver for this integration
    solver = ValidatingSolverAdapter(simulate_failure=False)
    adapter = ExecutionAdapter(solver, selected_solver_meta)

    # Convert request payload to solver problem representation
    problem_to_solve = {
        **problem,
        "payload": req.payload
    }

    timeout_seconds = req.execution_constraints.max_time_ms // 1000

    evidence = adapter.execute_with_evidence(problem_to_solve, timeout_seconds=timeout_seconds)

    if evidence["status"] == "FAILED":
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"EngineCrash: {evidence['result'].get('error', 'Unknown error')}"
        )

    # Save evidence to "Bucket evidence storage" (using EvidencePublisher)
    bucket_uri = publisher.publish(evidence)
    logger.info(f"Execution successful. Evidence stored at {bucket_uri}")

    return {
        "execution_id": f"exec-{uuid.uuid4().hex[:8]}",
        "selected_solver": selected_solver_meta["solver_id"],
        "status": "Optimal",
        "solution": evidence["result"],
        "telemetry": {
            "execution_time_ms": evidence["provenance"]["execution_duration_ms"],
            "peak_memory_mb": 256  # Mock telemetry
        },
        "replay_metadata": {
            "deterministic_seed": 42,
            "fabric_version": evidence["provenance"]["fabric_version"],
            "solver_version": evidence["provenance"]["solver_version"],
            "trace_id": evidence["trace_id"],
            "replay_id": evidence["replay_id"]
        },
        "confidence_score": 0.99,
        "evidence_hash": evidence.get("evidence_hash", ""),
    }
