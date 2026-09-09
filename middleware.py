"""
middleware.py — Phase 2: Production ASGI Middleware

Provides three composable middleware layers for the FastAPI web server:
1. ErrorBoundaryMiddleware — catches unhandled exceptions, returns structured JSON
2. RequestTracingMiddleware — assigns correlation IDs, measures latency, logs requests
3. SecurityHeadersMiddleware — adds hardened response headers

RESPONSIBILITY BOUNDARY
-----------------------
Middleware OWNS:
    - HTTP-level error formatting (never leak stack traces)
    - Request correlation ID assignment
    - Response header injection
    - Request/response latency measurement

Middleware does NOT OWN:
    - Business-logic error handling   → web_server.py / integration_harness.py
    - OpenTelemetry span creation     → FastAPIInstrumentor
    - Authentication / authorization  → sdk_auth.py / producer_verification.py
"""

from __future__ import annotations

import json
import logging
import time
import traceback
import uuid
from typing import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from metrics import get_metrics

logger = logging.getLogger("qcg.middleware")


class ErrorBoundaryMiddleware(BaseHTTPMiddleware):
    """
    Catches all unhandled exceptions and returns a structured JSON error.

    Never leaks stack traces, internal paths, or implementation details
    to the client. All errors are logged with full context server-side.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        try:
            response = await call_next(request)
            return response
        except Exception as exc:
            # Extract correlation ID if set by RequestTracingMiddleware
            request_id = request.state.request_id if hasattr(request.state, "request_id") else str(uuid.uuid4())

            # Log full details server-side
            logger.error(
                "Unhandled exception in %s %s [request_id=%s]: %s",
                request.method,
                request.url.path,
                request_id,
                str(exc),
                exc_info=True,
            )

            # Record error metric
            get_metrics().record_error("500_unhandled")

            # Return safe structured response
            return JSONResponse(
                status_code=500,
                content={
                    "error": "INTERNAL_SERVER_ERROR",
                    "message": "An unexpected error occurred. Contact the system administrator.",
                    "request_id": request_id,
                    "trace_id": request_id,
                },
                headers={"X-Request-ID": request_id},
            )


class RequestTracingMiddleware(BaseHTTPMiddleware):
    """
    Assigns a unique correlation ID to every request and records
    latency metrics.

    The correlation ID is:
    - Taken from the incoming X-Request-ID header if present
    - Generated as a UUID4 otherwise
    - Attached to the response as X-Request-ID
    - Stored in request.state.request_id for downstream access
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Assign or adopt correlation ID
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        request.state.request_id = request_id

        # Record request metric
        endpoint = request.url.path
        method = request.method
        metrics = get_metrics()
        metrics.record_request(endpoint, method)

        # Measure latency
        start_time = time.time()

        response = await call_next(request)

        duration_ms = (time.time() - start_time) * 1000
        metrics.record_latency(endpoint, duration_ms)

        # Attach headers
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Response-Time-Ms"] = f"{duration_ms:.2f}"

        # Record errors
        if response.status_code >= 400:
            metrics.record_error(f"{response.status_code}")

        # Log structured request summary
        logger.info(
            "request_complete endpoint=%s method=%s status=%d duration_ms=%.2f request_id=%s",
            endpoint,
            method,
            response.status_code,
            duration_ms,
            request_id,
        )

        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Adds hardened security response headers to every response.

    These headers protect against common web vulnerabilities
    (clickjacking, MIME sniffing, XSS).
    """

    SECURITY_HEADERS = {
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "X-XSS-Protection": "1; mode=block",
        "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
        "Cache-Control": "no-store, no-cache, must-revalidate",
        "Referrer-Policy": "strict-origin-when-cross-origin",
        "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
    }

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)
        for header, value in self.SECURITY_HEADERS.items():
            response.headers[header] = value
        return response
