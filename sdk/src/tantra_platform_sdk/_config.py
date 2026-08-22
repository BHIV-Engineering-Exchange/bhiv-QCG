"""
_config.py — SDK-only configuration defaults.

Standalone configuration for the SDK package so external participants
don't need the full QCG config.py. All values can be overridden via
environment variables.
"""

import os


def _float(key: str, default: float) -> float:
    return float(os.environ.get(key, default))


def _int(key: str, default: int) -> int:
    return int(os.environ.get(key, default))


# -- Federated Discovery Platform -------------------------------------------
DISCOVERY_PORT_BASE: int            = _int("QCG_DISCOVERY_PORT_BASE", 9010)

# -- SDK Configuration -------------------------------------------------------
SDK_MAX_RETRIES: int                = _int("QCG_SDK_MAX_RETRIES", 3)
SDK_RETRY_BASE_DELAY: float         = _float("QCG_SDK_RETRY_BASE_DELAY", 0.5)
SDK_RETRY_MAX_DELAY: float          = _float("QCG_SDK_RETRY_MAX_DELAY", 30.0)
SDK_CIRCUIT_BREAKER_THRESHOLD: int  = _int("QCG_SDK_CB_THRESHOLD", 5)
SDK_CIRCUIT_BREAKER_TIMEOUT: float  = _float("QCG_SDK_CB_TIMEOUT", 60.0)
SDK_REQUEST_TIMEOUT: int            = _int("QCG_SDK_REQUEST_TIMEOUT", 10)
