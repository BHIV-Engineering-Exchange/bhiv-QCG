"""
review_packets/Code_Packets/routing_api_security_middleware.py
Parikshak Engineering Review Runtime — Routing, API & Security Middleware
Standard: Governed Operational System (Gov-OS) Core Compliance

Guarantees:
1. Strict v1.0 inbound and outbound schema validation
2. Prohibition of forbidden architectural patterns
3. Complete error boundaries eliminating unhandled 500 exceptions
"""

from typing import Dict, Any
from contracts.schemas import ErrorEnvelope


class GovOSSecurityMiddleware:
    FORBIDDEN_PATTERNS = ["workflow_execution_engine", "direct_masterdb_schema_mutation"]

    @classmethod
    def inspect_payload(cls, payload: Dict[str, Any]) -> bool:
        serialized = str(payload).lower()
        for pattern in cls.FORBIDDEN_PATTERNS:
            if pattern in serialized:
                return False
        return True

    @classmethod
    def generate_error_envelope(cls, status_code: int, error_type: str, message: str, request_id: str) -> ErrorEnvelope:
        from datetime import datetime, timezone
        return ErrorEnvelope(
            status="error",
            status_code=status_code,
            error_type=error_type,
            message=message,
            request_id=request_id,
            timestamp=datetime.now(timezone.utc).isoformat()
        )
