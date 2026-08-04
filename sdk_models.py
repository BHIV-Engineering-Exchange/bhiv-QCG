"""
sdk_models.py — Platform Capability SDK Data Models

All data models returned by the PlatformCapabilitySDK.
Immutable, serializable, and deterministically hashable.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Invocation Result
# ---------------------------------------------------------------------------

@dataclass
class InvocationResult:
    """Result of a capability invocation through the SDK."""
    invocation_id: str
    service_id: str
    operation: str
    status: str                     # SUCCESS | FAILED | TIMEOUT | CIRCUIT_OPEN
    response: Dict[str, Any]
    duration_ms: float
    trust_method: str               # CLASSICAL | POST_QUANTUM | HYBRID
    evidence: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    retry_count: int = 0
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> dict:
        return asdict(self)


# ---------------------------------------------------------------------------
# Negotiation Result
# ---------------------------------------------------------------------------

@dataclass
class NegotiationResult:
    """Result of a version negotiation."""
    service_id: str
    status: str                     # COMPATIBLE | DEPRECATED | UNSUPPORTED | UNKNOWN_SERVICE
    requested_version: str
    negotiated_version: Optional[str] = None
    suggested_versions: List[str] = field(default_factory=list)
    message: str = ""
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> dict:
        return asdict(self)


# ---------------------------------------------------------------------------
# Validation Result
# ---------------------------------------------------------------------------

@dataclass
class ValidationResult:
    """Result of a manifest / contract validation."""
    service_id: str
    valid: bool
    errors: List[str] = field(default_factory=list)
    manifest_hash: str = ""
    operations_validated: int = 0
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> dict:
        return asdict(self)


# ---------------------------------------------------------------------------
# Health Result
# ---------------------------------------------------------------------------

@dataclass
class HealthResult:
    """Result of a health check."""
    service_id: str
    status: str                     # UP | DOWN | UNKNOWN
    version: str = ""
    uptime_seconds: float = 0.0
    dependencies: Dict[str, str] = field(default_factory=dict)
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> dict:
        return asdict(self)


# ---------------------------------------------------------------------------
# Invocation Evidence
# ---------------------------------------------------------------------------

@dataclass
class InvocationEvidence:
    """
    Evidence record for a single SDK invocation.

    Forms an append-only hash chain, enabling tamper detection
    and replay verification across the SDK's invocation history.
    """
    invocation_id: str
    service_id: str
    operation: str
    request_hash: str
    response_hash: str
    trust_method: str
    duration_ms: float
    status: str
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    evidence_hash: str = ""
    previous_evidence_hash: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    @staticmethod
    def compute_hash(payload: dict) -> str:
        """Compute SHA-256 over a dict (deterministic)."""
        canonical = json.dumps(payload, sort_keys=True, default=str)
        return hashlib.sha256(canonical.encode()).hexdigest()
