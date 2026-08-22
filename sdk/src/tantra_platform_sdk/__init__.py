"""
tantra_platform_sdk — Official Platform Capability SDK
=======================================================

Provides external participants with:
  - PlatformCapabilitySDK  — main entry point for discovery, negotiation, invocation
  - SDK data models        — InvocationResult, NegotiationResult, etc.
  - SDKAuthenticator       — request signing & response verification
  - TrustProvider          — pluggable trust interface (Classical / PQ / Hybrid)

Installation:
    pip install git+https://github.com/PriteshPatra-BHIV/QCG_task1.git#subdirectory=sdk

Quick start:
    from tantra_platform_sdk import PlatformCapabilitySDK

    sdk = PlatformCapabilitySDK(
        discovery_urls=["https://bhiv-qcg.onrender.com"],
        service_id="MY-SERVICE-001"
    )
    result = sdk.invoke_capability("TANTRA-PSR-USF-001", "discover_solvers", {"problem_type": "QUBO"})
"""

__version__ = "1.0.0"

# -- Core SDK ----------------------------------------------------------------
from ._sdk_core import PlatformCapabilitySDK  # noqa: F401

# -- Data Models --------------------------------------------------------------
from ._models import (  # noqa: F401
    InvocationResult,
    NegotiationResult,
    ValidationResult,
    HealthResult,
    InvocationEvidence,
)

# -- Authentication -----------------------------------------------------------
from ._auth import SDKAuthenticator  # noqa: F401

# -- Trust Providers ----------------------------------------------------------
from ._trust import (  # noqa: F401
    TrustProvider,
    ClassicalTrustProvider,
    KeyPairResult,
)

__all__ = [
    "PlatformCapabilitySDK",
    "InvocationResult",
    "NegotiationResult",
    "ValidationResult",
    "HealthResult",
    "InvocationEvidence",
    "SDKAuthenticator",
    "TrustProvider",
    "ClassicalTrustProvider",
    "KeyPairResult",
]
