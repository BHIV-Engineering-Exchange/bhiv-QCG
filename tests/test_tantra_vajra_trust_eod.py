#!/usr/bin/env python3
"""
tests/test_tantra_vajra_trust_eod.py — Pytest Integration for TANTRA-VAJRA Trust Suite

Programme: BHQ Sovereign Quantum Computing and Networking / BIQOS
Task ID: BHQ-INFRA-EOD-001
Owner: Pritesh Patra (Trust, Provenance & Integration Architect)
"""

import sys
from pathlib import Path

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

from scripts.run_tantra_vajra_trust_eod import run_tantra_vajra_trust_suite


def test_tantra_vajra_trust_eod_checkpoint():
    """Verify that all 5 criteria pass for Pritesh's 50% EOD Checkpoint."""
    results = run_tantra_vajra_trust_suite()
    assert results["acceptance_criteria"]["Overall_50_Percent_Checkpoint_Status"] == "PASSED"
    assert results["acceptance_criteria"]["Criterion_1_Identity_and_Signing"]["passed"] is True
    assert results["acceptance_criteria"]["Criterion_2_TANTRA_Contract_Boundary"]["passed"] is True
    assert results["acceptance_criteria"]["Criterion_3_VAJRA_Provenance_Verification"]["passed"] is True
    assert results["acceptance_criteria"]["Criterion_4_Tamper_and_Adversarial_Rejection"]["passed"] is True
    assert results["acceptance_criteria"]["Criterion_5_Evidence_Ledger_and_Merkle_Integrity"]["passed"] is True

