#!/usr/bin/env python3
"""
tests/test_qcg_provenance.py — Unit test wrapper for CI/CD integration

Workstream D: Mechatronics, Instrumentation & Retained Cryptographic Provenance
Accountable Owner: Pritesh Patra
Remediates: BLK-QCG-003
"""

import sys
from pathlib import Path

# Add workspace root to sys.path
WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

from evidence.test_qcg_provenance import (
    test_ecdsa_keypair_generation,
    test_100_record_signing_and_merkle_provenance,
    test_single_bit_tamper_detection,
    run_provenance_verification_suite,
)


def test_full_provenance_acceptance_suite():
    """Verify Criterion D3 for BHQ-INFRA-001 Workstream D."""
    results = run_provenance_verification_suite(record_count=100, tamper_index=42)
    assert results["acceptance_criteria"]["Criterion_D3_Cryptographic_Provenance"]["passed"] is True

