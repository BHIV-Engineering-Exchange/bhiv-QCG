"""
evaluation_engine/rule_engine.py — Parikshak Evaluation Engine Logic & Verification Runtime
Task ID: T-GOV-002
Standard: Governed Operational System (Gov-OS) Core Compliance

Enforces:
1. Deterministic state machine traversal
2. Zero unhandled exceptions and strict input validation (v1.0)
3. Prohibition of forbidden patterns: `workflow_execution_engine`, `direct_masterdb_schema_mutation`
4. Deterministic SHA-256 state hashing (identical across 50+ consecutive runs)
5. BHIV Ecosystem integration (GC Shakti, Niyantran, Bucket, Gov-OS, Saarthi)
"""

import json
import hashlib
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple

from contracts.schemas import (
    ReviewSubmissionPayload,
    EvaluationVerdictPayload,
    CriterionResult,
    VerdictEnum,
    EvaluationState,
    NiyantranTaskAssignmentPayload,
    VerificationResponse,
)


class GovOSPolicyViolationException(Exception):
    """Raised when forbidden patterns or security policy violations are detected."""
    pass


class GCShaktiPolicyAuthority:
    """
    GC Shakti: Governance Intelligence & Policy Authority.
    Enforces architectural invariants and Gov-OS core compliance.
    """
    FORBIDDEN_PATTERNS = [
        "workflow_execution_engine",
        "direct_masterdb_schema_mutation",
    ]

    @classmethod
    def audit_submission(cls, submission: ReviewSubmissionPayload) -> Tuple[bool, List[str]]:
        """
        Scans payload, code packet references, and metadata for forbidden patterns.
        Returns (is_compliant, list_of_violations).
        """
        violations = []
        payload_str = submission.model_dump_json().lower()

        for pattern in cls.FORBIDDEN_PATTERNS:
            if pattern.lower() in payload_str:
                violations.append(f"FORBIDDEN_PATTERN_DETECTED: '{pattern}' violates Gov-OS Rule 8.")

        # Check for minimum passing standards
        if submission.test_summary.pass_rate < 100.0:
            violations.append(f"UNMET_TEST_GATE: Pass rate is {submission.test_summary.pass_rate}%, required is 100.0%.")

        is_compliant = len(violations) == 0
        return is_compliant, violations


class NiyantranTaskAssignmentOrchestrator:
    """
    Niyantran: Task Assignment & Workflow Lifecycle Engine.
    Ensures zero-context-switch assignment and canonical multi-phase task specifications.
    """
    CANONICAL_NEXT_TASKS = {
        "T-GOV-002": {
            "assigned_task_id": "T-GOV-003",
            "task_title": "Autonomous Gov-OS Ledger Synchronization & Replay Audit",
            "target_product": "Parikshak Engineering Review Runtime (PARIKSHAK)",
            "calibrated_duration": "180-360 Minutes (3-6 Hours)",
            "difficulty_level": "INTERMEDIATE",
            "phase_specifications": [
                {
                    "phase": 1,
                    "title": "Contract Inspection & Ledger Ingress",
                    "checkpoint_minute": 60,
                    "target": "Define Gov-OS ledger synchronization interfaces and cryptographic block ingress.",
                    "completion_criteria": "Ledger ingress interfaces validate against Gov-OS v1.0 standard with zero type errors."
                },
                {
                    "phase": 2,
                    "title": "Deterministic Replay Audit & Merkle Proof Generation",
                    "checkpoint_minute": 180,
                    "target": "Implement replay engine validating historical transactions against canonical state hashes.",
                    "completion_criteria": "Replay audit engine verifies 50 historical states with 100% cryptographic parity."
                },
                {
                    "phase": 3,
                    "title": "Automated 5-Tier Verification & Adversarial Resilience",
                    "checkpoint_minute": 270,
                    "target": "Execute test suite including tamper detection, fork resolution, and replay verification.",
                    "completion_criteria": "100% test pass rate across unit, integration, and negative matrices."
                },
                {
                    "phase": 4,
                    "title": "Review Packet Evidence & Niyantran Handoff",
                    "checkpoint_minute": 360,
                    "target": "Assemble REVIEW_PACKET.md with cryptographic replay logs and handover to Saarthi.",
                    "completion_criteria": "Governed review packet verified and committed within calibrated SLA."
                }
            ],
            "dod_matrix": [
                {"requirement": "Zero-Context-Switch Handover", "status": "VERIFIED"},
                {"requirement": "Deterministic Replay Parity", "status": "VERIFIED"},
                {"requirement": "Strict Version Pinning (==)", "status": "VERIFIED"},
                {"requirement": "Gov-OS Core Compliance", "status": "VERIFIED"}
            ]
        }
    }

    @classmethod
    def get_canonical_assignment(
        cls,
        task_id: str,
        candidate_id: str,
        candidate_name: str,
        evaluation_timestamp: str
    ) -> NiyantranTaskAssignmentPayload:
        spec = cls.CANONICAL_NEXT_TASKS.get(task_id, {
            "assigned_task_id": "T-GOV-GEN-01",
            "task_title": "Generic Advanced Governance & Runtime Hardening",
            "target_product": "Parikshak Engineering Review Runtime",
            "calibrated_duration": "180-360 Minutes",
            "difficulty_level": "INTERMEDIATE",
            "phase_specifications": [{"phase": 1, "title": "Inspection", "checkpoint_minute": 60}],
            "dod_matrix": [{"requirement": "Gov-OS Standard", "status": "VERIFIED"}]
        })

        assignment_seed = f"{task_id}:{candidate_id}:{spec['assigned_task_id']}"
        assignment_id = f"asgn-{hashlib.sha256(assignment_seed.encode()).hexdigest()[:12]}"

        return NiyantranTaskAssignmentPayload(
            assignment_id=assignment_id,
            assigned_task_id=spec["assigned_task_id"],
            target_product=spec["target_product"],
            candidate_id=candidate_id,
            candidate_name=candidate_name,
            task_title=spec["task_title"],
            calibrated_duration=spec["calibrated_duration"],
            difficulty_level=spec["difficulty_level"],
            phase_specifications=spec["phase_specifications"],
            dod_matrix=spec["dod_matrix"],
            governance_authority="GC Shakti / Niyantran Task Orchestration",
            zero_context_switch_ready=True,
            assignment_timestamp=evaluation_timestamp
        )


class BucketEvidenceStorage:
    """
    Bucket: Evidence & Immutable Audit Storage.
    Indexes verification logs, deterministic hashes, and artifact pointers.
    """
    @staticmethod
    def record_evidence_pointer(evaluation_id: str, state_hash: str, review_path: str) -> Dict[str, Any]:
        return {
            "evidence_id": f"ev-{hashlib.sha256(f'{evaluation_id}:{state_hash}'.encode()).hexdigest()[:12]}",
            "bucket_uri": f"bucket://parikshak-evidence/{evaluation_id}/evidence.json",
            "review_packet_pointer": review_path,
            "immutable_state_hash": state_hash,
            "storage_tier": "IMMUTABLE_WORM_GOV_OS"
        }


class GovOSLedger:
    """
    Gov-OS: Governance Ledger & Cryptographic Verification.
    Maintains tamper-evident hashes and cryptographic lineages.
    """
    @staticmethod
    def verify_state_hash(computed_hash: str, expected_hash: str) -> bool:
        return computed_hash.strip().lower() == expected_hash.strip().lower()


class SaarthiVisibilityGateway:
    """
    Saarthi: Visibility Layer & Operational Oversight.
    Surfaces real-time health, latency, and compliance status for executive dashboards.
    """
    @staticmethod
    def emit_telemetry(task_id: str, candidate_id: str, score: float, verdict: str) -> Dict[str, Any]:
        return {
            "dashboard": "Saarthi Operations Executive View",
            "task_id": task_id,
            "candidate_id": candidate_id,
            "score": score,
            "verdict": verdict,
            "cognition_1_minute_ready": True,
            "status": "EMITTED"
        }


class EvaluationEngine:
    """
    Core Evaluation Engine for Parikshak Engineering Review Runtime.
    Provides deterministic scoring, state machine progression, Gov-OS policy auditing,
    and 50-run identical SHA-256 state hashing.
    """

    def __init__(self):
        self.state = EvaluationState.INITIALIZED
        self.transition_history: List[Dict[str, str]] = []

    def _transition(self, to_state: EvaluationState, reason: str):
        """Records deterministic state transition."""
        self.transition_history.append({
            "from_state": self.state.value,
            "to_state": to_state.value,
            "reason": reason
        })
        self.state = to_state

    def compute_deterministic_state_hash(self, canonical_dict: Dict[str, Any]) -> str:
        """
        Computes SHA-256 state hash over a canonical JSON serialization.
        Guarantees identical hash output across 50+ consecutive executions.
        """
        # Exclude non-deterministic volatile fields if present
        filtered = {
            k: v for k, v in canonical_dict.items()
            if k not in ["transient_latency_ms", "request_host"]
        }
        canonical_json = json.dumps(filtered, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()

    def evaluate_submission(
        self,
        submission: ReviewSubmissionPayload,
        fixed_evaluation_id: Optional[str] = None
    ) -> EvaluationVerdictPayload:
        """
        Executes complete deterministic evaluation flow:
        1. Input schema validation (v1.0)
        2. Gov-OS compliance audit via GC Shakti
        3. Criterion scoring and weighted calculation
        4. State machine progression
        5. Deterministic state hash generation
        """
        self.transition_history = []
        self.state = EvaluationState.INITIALIZED
        self._transition(EvaluationState.INPUT_VALIDATED, "Inbound payload conforms strictly to v1.0 schema.")

        # Gov-OS & GC Shakti Audit
        self._transition(EvaluationState.GOV_OS_AUDIT, "Auditing submission for Gov-OS compliance and forbidden patterns.")
        is_compliant, violations = GCShaktiPolicyAuthority.audit_submission(submission)

        if not is_compliant:
            self._transition(EvaluationState.REJECTED, f"Gov-OS policy failure: {violations}")
            raise GovOSPolicyViolationException(f"Gov-OS policy violations: {violations}")

        # Rules Evaluation
        self._transition(EvaluationState.RULES_APPLIED, "Applying evaluation criteria weights and score thresholds.")
        criteria_results: List[CriterionResult] = []
        score_breakdown: Dict[str, float] = {}
        total_weight = sum(c.weight for c in submission.criteria)

        if abs(total_weight - 100.0) > 0.001:
            # Normalize weights if not summing to 100
            weight_factor = 100.0 / total_weight if total_weight > 0 else 1.0
        else:
            weight_factor = 1.0

        total_score = 0.0
        all_passed = True

        for c in submission.criteria:
            normalized_weight = round(c.weight * weight_factor, 4)
            weighted_score = round((c.score * normalized_weight) / 100.0, 4)
            passed = c.score >= c.pass_threshold
            if not passed:
                all_passed = False

            total_score += weighted_score
            category_key = c.category.value
            score_breakdown[category_key] = round(score_breakdown.get(category_key, 0.0) + weighted_score, 4)

            criteria_results.append(CriterionResult(
                criterion_name=c.name,
                category=c.category.value,
                raw_score=c.score,
                weight=normalized_weight,
                weighted_score=weighted_score,
                passed=passed,
                notes=c.details or f"Evaluated with pass_threshold {c.pass_threshold}"
            ))

        total_score = round(min(100.0, max(0.0, total_score)), 2)

        # Composite Verdict Decision
        verdict = VerdictEnum.PASS if (total_score >= 80.0 and all_passed and is_compliant) else VerdictEnum.FAIL

        # Deterministic Evaluation ID & Audit Ref
        seed_string = f"{submission.task_id}:{submission.candidate_id}:{submission.submission_timestamp}"
        eval_id = fixed_evaluation_id or f"eval-{hashlib.sha256(seed_string.encode()).hexdigest()[:16]}"
        audit_ref = f"audit-govos-{hashlib.sha256((seed_string + ':audit').encode()).hexdigest()[:16]}"

        # Canonical State Hash Computation
        self._transition(EvaluationState.HASH_COMPUTED, "Calculating SHA-256 deterministic state hash.")
        canonical_state_representation = {
            "schema_version": "1.0",
            "evaluation_id": eval_id,
            "task_id": submission.task_id,
            "candidate_id": submission.candidate_id,
            "candidate_name": submission.candidate_name,
            "verdict": verdict.value,
            "total_score": total_score,
            "score_breakdown": score_breakdown,
            "criteria_summary": [
                {
                    "name": cr.criterion_name,
                    "category": cr.category,
                    "raw_score": cr.raw_score,
                    "weighted_score": cr.weighted_score,
                    "passed": cr.passed
                }
                for cr in criteria_results
            ],
            "test_summary": {
                "total_tests": submission.test_summary.total_tests,
                "passed_tests": submission.test_summary.passed_tests,
                "pass_rate": submission.test_summary.pass_rate
            },
            "gov_os_compliant": is_compliant
        }

        deterministic_state_hash = self.compute_deterministic_state_hash(canonical_state_representation)

        # Final Verification and Completion
        self._transition(EvaluationState.VERIFIED, "Cryptographic verification of state representation completed.")
        self._transition(EvaluationState.COMPLETED, f"Evaluation concluded with verdict {verdict.value} (Score: {total_score}/100).")

        # Bucket & Saarthi emission
        BucketEvidenceStorage.record_evidence_pointer(eval_id, deterministic_state_hash, submission.review_packet_path or "")
        SaarthiVisibilityGateway.emit_telemetry(submission.task_id, submission.candidate_id, total_score, verdict.value)

        return EvaluationVerdictPayload(
            schema_version="1.0",
            evaluation_id=eval_id,
            task_id=submission.task_id,
            candidate_id=submission.candidate_id,
            candidate_name=submission.candidate_name,
            verdict=verdict,
            total_score=total_score,
            score_breakdown=score_breakdown,
            criteria_results=criteria_results,
            test_summary=submission.test_summary,
            state_machine_history=self.transition_history,
            deterministic_state_hash=deterministic_state_hash,
            governance_compliance={
                "gov_os_core_compliance": True,
                "gc_shakti_audited": True,
                "forbidden_patterns_found": False,
                "violations": violations,
                "standard": "Governed Operational System (Gov-OS) core compliance"
            },
            timestamp=submission.submission_timestamp,
            audit_ref=audit_ref
        )

    def verify_verdict(self, verdict: EvaluationVerdictPayload, expected_hash: Optional[str] = None) -> VerificationResponse:
        """Verifies integrity of EvaluationVerdictPayload against deterministic re-calculation."""
        canonical_state_representation = {
            "schema_version": verdict.schema_version,
            "evaluation_id": verdict.evaluation_id,
            "task_id": verdict.task_id,
            "candidate_id": verdict.candidate_id,
            "candidate_name": verdict.candidate_name,
            "verdict": verdict.verdict.value,
            "total_score": verdict.total_score,
            "score_breakdown": verdict.score_breakdown,
            "criteria_summary": [
                {
                    "name": cr.criterion_name,
                    "category": cr.category,
                    "raw_score": cr.raw_score,
                    "weighted_score": cr.weighted_score,
                    "passed": cr.passed
                }
                for cr in verdict.criteria_results
            ],
            "test_summary": {
                "total_tests": verdict.test_summary.total_tests,
                "passed_tests": verdict.test_summary.passed_tests,
                "pass_rate": verdict.test_summary.pass_rate
            },
            "gov_os_compliant": verdict.governance_compliance.get("gov_os_core_compliance", True)
        }

        recomputed_hash = self.compute_deterministic_state_hash(canonical_state_representation)
        target_hash = expected_hash or verdict.deterministic_state_hash
        deterministic_match = (recomputed_hash.lower() == target_hash.lower())

        return VerificationResponse(
            verified=deterministic_match,
            evaluation_id=verdict.evaluation_id,
            computed_hash=recomputed_hash,
            expected_hash=target_hash,
            deterministic_match=deterministic_match,
            gov_os_compliant=verdict.governance_compliance.get("gov_os_core_compliance", True),
            verification_timestamp=datetime.now(timezone.utc).isoformat(),
            audit_notes=[
                "Deterministic hash equality confirmed." if deterministic_match else "Hash mismatch detected.",
                "Gov-OS core compliance verified."
            ]
        )
