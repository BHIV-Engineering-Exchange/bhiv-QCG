#!/usr/bin/env python3
"""
tests/test_vajra_qcg_endpoint_validation.py — Pytest Wrapper for VAJRA Trust/Provenance Endpoints

Programme: BHQ Sovereign Quantum Computing and Networking / BIQOS
Task ID: BHQ-INFRA-EOD-001
Owner: Pritesh Patra (Trust, Provenance & Integration Lead)
"""

import sys
from pathlib import Path

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

from scripts.run_vajra_qcg_endpoint_validation import run_vajra_endpoint_validation


def test_vajra_trust_boundary_endpoints_e2e():
    """Verify all positive and negative test criteria pass for VAJRA endpoints."""
    results = run_vajra_endpoint_validation()

    # Overall Status
    assert results["acceptance_criteria"]["Overall_VAJRA_Trust_Boundary_Status"] == "PASSED"

    # Positive Tests
    pos = results["positive_tests"]
    assert len(pos) == 4
    assert all(t["passed"] for t in pos)

    # Negative Tests
    neg = results["negative_tests"]
    assert len(neg) == 6
    assert all(t["passed"] for t in neg)

    # Check Specific Critical Assertions
    assert any(t["test_id"] == "POS-01" and t["passed"] for t in pos)
    assert any(t["test_id"] == "POS-02" and t["passed"] for t in pos)
    assert any(t["test_id"] == "NEG-01" and "REPLAY" in t["halt_reason"] for t in neg)
    assert any(t["test_id"] == "NEG-02" and t["passed"] for t in neg)
    assert any(t["test_id"] == "NEG-03" and t["passed"] for t in neg)

