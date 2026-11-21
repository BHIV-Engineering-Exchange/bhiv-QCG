"""
tests/test_evaluation_determinism.py — 50-Run Deterministic State Hash Verification
Task ID: T-GOV-002
Standard: Governed Operational System (Gov-OS) Core Compliance

Validates:
Acceptance Criterion: "Deterministic execution: 50 consecutive runs must produce identical SHA-256 state hashes"
"""

import pytest
import os
import json
from contracts.schemas import (
    ReviewSubmissionPayload,
    CriterionInput,
    CriterionCategory,
    TestSummary,
    VerdictEnum,
)
from evaluation_engine.rule_engine import EvaluationEngine


class TestEvaluationDeterminism:

    def test_fifty_consecutive_runs_produce_identical_sha256_state_hash(self):
        """
        Executes EvaluationEngine.evaluate_submission 50 consecutive times on identical input.
        Asserts that every single run produces the exact same SHA-256 state hash.
        """
        fixed_timestamp = "2026-11-21T12:00:00Z"

        payload = ReviewSubmissionPayload(
            task_id="T-GOV-002",
            candidate_id="user-kanishk-singh",
            candidate_name="Kanishk Singh",
            target_product="Parikshak Engineering Review Runtime",
            submission_timestamp=fixed_timestamp,
            review_packet_path="review_packets/REVIEW_PACKET.md",
            criteria=[
                CriterionInput(
                    name="Architectural Modularity",
                    category=CriterionCategory.ARCHITECTURAL_MODULARITY,
                    weight=25.0,
                    score=100.0,
                    pass_threshold=70.0,
                    details="Deterministic scoring rules and strict schemas."
                ),
                CriterionInput(
                    name="Gov-OS Core Compliance",
                    category=CriterionCategory.GOV_OS_COMPLIANCE,
                    weight=25.0,
                    score=100.0,
                    pass_threshold=80.0,
                    details="Zero forbidden patterns, SHA-256 state hash replay verification."
                ),
                CriterionInput(
                    name="Test & Verification Matrix",
                    category=CriterionCategory.TEST_VERIFICATION_MATRIX,
                    weight=25.0,
                    score=100.0,
                    pass_threshold=80.0,
                    details="5-Tier automated testing with 100% pass rate."
                ),
                CriterionInput(
                    name="Runtime Evidence Grounding",
                    category=CriterionCategory.RUNTIME_EVIDENCE_GROUNDING,
                    weight=25.0,
                    score=100.0,
                    pass_threshold=70.0,
                    details="Verified audit logs and canonical next-task assignment."
                ),
            ],
            test_summary=TestSummary(
                total_tests=50,
                passed_tests=50,
                failed_tests=0,
                skipped_tests=0,
                pass_rate=100.0
            ),
            code_packets=[
                {"name": "rule_engine.py", "hash": "deterministic_source_hash"}
            ],
            metadata={"run_env": "production_govos_replay"}
        )

        hashes = []
        scores = []
        verdicts = []

        for i in range(50):
            # Create a fresh engine instance per run to test stateless determinism
            engine = EvaluationEngine()
            verdict = engine.evaluate_submission(payload)

            hashes.append(verdict.deterministic_state_hash)
            scores.append(verdict.total_score)
            verdicts.append(verdict.verdict)

        # Verification 1: Exactly 50 runs executed
        assert len(hashes) == 50, "Expected 50 evaluation executions."

        # Verification 2: All 50 hashes must be strictly identical (set length == 1)
        distinct_hashes = set(hashes)
        assert len(distinct_hashes) == 1, (
            f"Non-deterministic execution detected! Found {len(distinct_hashes)} distinct hashes: {distinct_hashes}"
        )

        canonical_hash = hashes[0]
        assert len(canonical_hash) == 64, f"Hash length must be 64 characters (SHA-256), got {len(canonical_hash)}"

        # Verification 3: All scores and verdicts are identical
        assert set(scores) == {100.0}
        assert set(verdicts) == {VerdictEnum.PASS}

        # Write proof artifact
        evidence_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "evidence")
        os.makedirs(evidence_dir, exist_ok=True)
        proof_log_path = os.path.join(evidence_dir, "determinism_50_run_proof.log")

        with open(proof_log_path, "w", encoding="utf-8") as f:
            f.write("# 50-Run Deterministic State Hash Verification Log\n")
            f.write(f"Task ID: T-GOV-002 | Candidate: Kanishk Singh\n")
            f.write(f"Timestamp: {fixed_timestamp}\n")
            f.write(f"Canonical State Hash (SHA-256): {canonical_hash}\n")
            f.write(f"Total Runs: 50 | Unique Hashes: 1 | Parity: 100.0%\n\n")
            for idx, h in enumerate(hashes, start=1):
                f.write(f"Run {idx:02d}: {h} | Verdict: PASS | Score: 100.0 | Parity: MATCH\n")
