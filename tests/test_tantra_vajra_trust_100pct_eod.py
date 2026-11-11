#!/usr/bin/env python3
"""
tests/test_tantra_vajra_trust_100pct_eod.py — Pytest Integration Test Suite for 100% EOD Checkpoint

Programme: BHQ Sovereign Quantum Computing and Networking / BIQOS
Task ID: BHQ-INFRA-EOD-001
Owner: Pritesh Patra (Trust, Provenance & Integration Lead)
"""

import sys
from pathlib import Path

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

from scripts.run_tantra_vajra_trust_100pct_eod import run_full_100pct_pipeline


def test_100pct_tantra_vajra_e2e_pipeline():
    """Verify that all 5 integration stages and acceptance criteria pass."""
    results = run_full_100pct_pipeline()

    # Overall Status
    assert results["acceptance_criteria"]["Overall_100_Percent_EOD_Status"] == "PASSED"

    # All 5 Criteria
    assert results["acceptance_criteria"]["Criterion_1_Workload_Aer_Simulation"]["passed"] is True
    assert results["acceptance_criteria"]["Criterion_2_TANTRA_Orchestration_Contract"]["passed"] is True
    assert results["acceptance_criteria"]["Criterion_3_VAJRA_Dual_Signing_and_Provenance"]["passed"] is True
    assert results["acceptance_criteria"]["Criterion_4_Evidence_Ledger_and_Merkle_Proof"]["passed"] is True
    assert results["acceptance_criteria"]["Criterion_5_Adversarial_and_Tamper_Rejection"]["passed"] is True

    # Check 10 Adversarial Scenarios
    scenarios = results["adversarial_suite"]
    assert len(scenarios) == 10
    assert all(s["passed"] for s in scenarios)

    # Check Batch Replay Invariance
    batch = results["batch_evidence"]
    assert batch["batch_size"] == 100
    assert batch["verification_rate"] == 100.0
    assert batch["determinism_pass"] is True
    assert batch["chain_continuity_valid"] is True

