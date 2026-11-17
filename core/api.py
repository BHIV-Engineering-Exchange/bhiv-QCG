"""FastAPI Router and Error Boundary for BHIV Enterprise Core.

Guarantees:
- Zero unhandled 500 exceptions on invalid or malformed inputs.
- Strict 400/422 responses with typed schema models.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict

from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from contracts.schemas import (
    EvidencePacket,
    ExecutionErrorResponse,
    ReviewPacketPayload,
    TaskDefinition,
    TaskExecutionRecord,
    TaskStatusEnum,
    ValidationErrorResponse,
)
from core.enterprise_engine import (
    EnterpriseCoreEngine,
    EnterpriseCoreException,
    EnterpriseCoreValidationError,
    ImmutabilityViolationError,
    StateTransitionViolationError,
    TaskNotFoundError,
)

router = APIRouter(prefix="/api/v1/enterprise-core", tags=["Enterprise Core"])
engine = EnterpriseCoreEngine()


@router.post(
    "/tasks",
    response_model=TaskExecutionRecord,
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"model": ValidationErrorResponse},
        422: {"model": ValidationErrorResponse},
    },
)
async def create_task(payload: Dict[str, Any]):
    """Register and initiate a task in the Enterprise Core."""
    try:
        record = engine.register_task(payload)
        return record
    except EnterpriseCoreValidationError as e:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=ValidationErrorResponse(
                error_code=e.error_code,
                message=e.message,
                invalid_fields=e.invalid_fields,
                timestamp_utc=datetime.now(timezone.utc).isoformat(),
            ).model_dump(),
        )
    except ImmutabilityViolationError as e:
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content=ExecutionErrorResponse(
                error_code=e.error_code,
                message=e.message,
                trace_id="system-conflict",
                timestamp_utc=datetime.now(timezone.utc).isoformat(),
            ).model_dump(),
        )
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=ValidationErrorResponse(
                error_code="INVALID_PAYLOAD",
                message=str(e),
                invalid_fields=[],
                timestamp_utc=datetime.now(timezone.utc).isoformat(),
            ).model_dump(),
        )


@router.post(
    "/tasks/{task_id}/transition",
    response_model=TaskExecutionRecord,
    status_code=status.HTTP_200_OK,
    responses={
        400: {"model": ExecutionErrorResponse},
        404: {"model": ExecutionErrorResponse},
    },
)
async def transition_task_state(task_id: str, payload: Dict[str, Any]):
    """Advance task state deterministically."""
    try:
        to_status_str = payload.get("to_status")
        if not to_status_str or to_status_str not in TaskStatusEnum.__members__:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content=ValidationErrorResponse(
                    error_code="INVALID_STATUS",
                    message=f"Invalid target status: '{to_status_str}'",
                    invalid_fields=["to_status"],
                    timestamp_utc=datetime.now(timezone.utc).isoformat(),
                ).model_dump(),
            )

        to_status = TaskStatusEnum(to_status_str)
        trigger = payload.get("trigger", "MANUAL_TRANSITION")
        actor = payload.get("actor", "system")
        context_payload = payload.get("payload", {})

        record = engine.transition_state(
            task_id=task_id,
            to_status=to_status,
            trigger=trigger,
            actor=actor,
            payload=context_payload,
        )
        return record
    except TaskNotFoundError as e:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content=ExecutionErrorResponse(
                error_code=e.error_code,
                message=e.message,
                trace_id=task_id,
                timestamp_utc=datetime.now(timezone.utc).isoformat(),
            ).model_dump(),
        )
    except StateTransitionViolationError as e:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=ExecutionErrorResponse(
                error_code=e.error_code,
                message=e.message,
                trace_id=task_id,
                timestamp_utc=datetime.now(timezone.utc).isoformat(),
            ).model_dump(),
        )
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=ExecutionErrorResponse(
                error_code="TRANSITION_FAILED",
                message=str(e),
                trace_id=task_id,
                timestamp_utc=datetime.now(timezone.utc).isoformat(),
            ).model_dump(),
        )


@router.get(
    "/tasks/{task_id}/evidence",
    response_model=EvidencePacket,
    status_code=status.HTTP_200_OK,
)
async def get_evidence(task_id: str):
    """Retrieve v1.0 standard evidence packet for a task."""
    try:
        return engine.generate_evidence_packet(task_id)
    except TaskNotFoundError as e:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content=ExecutionErrorResponse(
                error_code=e.error_code,
                message=e.message,
                trace_id=task_id,
                timestamp_utc=datetime.now(timezone.utc).isoformat(),
            ).model_dump(),
        )


@router.get(
    "/tasks/{task_id}/review-packet",
    response_model=ReviewPacketPayload,
    status_code=status.HTTP_200_OK,
)
async def get_review_packet(task_id: str):
    """Retrieve governed review packet payload."""
    try:
        return engine.assemble_review_packet(task_id)
    except TaskNotFoundError as e:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content=ExecutionErrorResponse(
                error_code=e.error_code,
                message=e.message,
                trace_id=task_id,
                timestamp_utc=datetime.now(timezone.utc).isoformat(),
            ).model_dump(),
        )
