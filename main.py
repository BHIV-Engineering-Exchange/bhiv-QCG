"""main.py — Parikshak Engineering Review Runtime Server.

Standard: Governed Operational System (Gov-OS) Core Compliance
Authority: Parikshak Engineering Review Runtime x Niyantran Task Orchestration
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List

from fastapi import FastAPI, HTTPException, Request, Response, status
from fastapi.responses import JSONResponse

from contracts.schemas import (
    EvaluationRequest,
    EvaluationRuleItem,
    EvaluationVerdict,
    ExecutionErrorResponse,
    ValidationErrorResponse,
)
from evaluation_engine.rule_engine import (
    EvaluationEngineException,
    EvaluationRuleEngine,
    EvaluationValidationError,
    ForbiddenPatternViolationError,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
log = logging.getLogger("parikshak.runtime")

app = FastAPI(
    title="PARIKSHAK Engineering Review Runtime API",
    description="Gov-OS Core Compliant Automated Verification & Review Engine",
    version="1.0.0",
)

engine = EvaluationRuleEngine()


@app.get("/health", tags=["System"])
async def health_check():
    """System health check endpoint."""
    return {
        "status": "UP",
        "service": "PARIKSHAK_EVALUATION_RUNTIME",
        "standard": "Gov-OS Core Compliance",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    }


@app.get(
    "/api/v1/parikshak/rules",
    response_model=List[EvaluationRuleItem],
    tags=["Evaluation Rules"],
)
async def list_evaluation_rules():
    """Retrieve canonical Gov-OS default evaluation rules."""
    return engine.DEFAULT_RULES


@app.post(
    "/api/v1/parikshak/evaluate",
    response_model=EvaluationVerdict,
    status_code=status.HTTP_200_OK,
    responses={
        400: {"model": ValidationErrorResponse},
        403: {"model": ExecutionErrorResponse},
        422: {"model": ValidationErrorResponse},
    },
    tags=["Evaluation Engine"],
)
async def evaluate_submission(payload: Dict[str, Any]):
    """Execute evaluation and compute deterministic verdict and score."""
    try:
        verdict = engine.evaluate_submission(payload)
        return verdict
    except EvaluationValidationError as e:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=ValidationErrorResponse(
                error_code=e.error_code,
                message=e.message,
                invalid_fields=e.invalid_fields,
                timestamp_utc=datetime.now(timezone.utc).isoformat(),
            ).model_dump(),
        )
    except ForbiddenPatternViolationError as e:
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content=ExecutionErrorResponse(
                error_code=e.error_code,
                message=e.message,
                trace_id=f"forbidden-{e.pattern_name}",
                timestamp_utc=datetime.now(timezone.utc).isoformat(),
            ).model_dump(),
        )
    except Exception as e:
        log.error("Unhandled error intercepted by Gov-OS error boundary: %s", str(e))
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=ValidationErrorResponse(
                error_code="INVALID_PAYLOAD",
                message=str(e),
                invalid_fields=[],
                timestamp_utc=datetime.now(timezone.utc).isoformat(),
            ).model_dump(),
        )


if __name__ == "__main__":
    import uvicorn
    log.info("Starting PARIKSHAK Review Runtime API on port 8081...")
    uvicorn.run("main:app", host="0.0.0.0", port=8081, reload=False)
