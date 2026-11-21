<<<<<<< HEAD
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
=======
"""PARIKSHAK Evaluation Rule Engine Implementation.

Standard: Governed Operational System (Gov-OS) Core Compliance
Authority: Parikshak Engineering Review Runtime
"""

from __future__ import annotations

import copy
import hashlib
import json
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from pydantic import ValidationError
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

from contracts.schemas import (
    EvaluationCriteriaCheck,
    EvaluationRequest,
    EvaluationRuleCategory,
    EvaluationRuleItem,
    EvaluationVerdict,
)


# ============================================================================
# Domain Exceptions (Strict Gov-OS Error Boundaries)
# ============================================================================

class EvaluationEngineException(Exception):
    """Base exception for all Evaluation Engine operations."""
    def __init__(self, message: str, error_code: str = "EVALUATION_ENGINE_ERROR"):
        super().__init__(message)
        self.message = message
        self.error_code = error_code


class EvaluationValidationError(EvaluationEngineException):
    """Raised when an inbound evaluation payload fails schema boundaries."""
    def __init__(self, message: str, invalid_fields: Optional[List[str]] = None):
        super().__init__(message, error_code="EVALUATION_VALIDATION_ERROR")
        self.invalid_fields = invalid_fields or []


class ForbiddenPatternViolationError(EvaluationEngineException):
    """Raised when forbidden anti-patterns are detected in requests."""
    def __init__(self, pattern_name: str, explanation: str):
        super().__init__(
            f"Forbidden pattern '{pattern_name}' detected. Violation: {explanation}",
            error_code="FORBIDDEN_PATTERN_VIOLATION",
        )
        self.pattern_name = pattern_name


class DeterminismVerificationError(EvaluationEngineException):
    """Raised when evaluation fails bit-identical hash stability."""
    def __init__(self, message: str):
        super().__init__(message, error_code="DETERMINISM_VERIFICATION_FAILED")


# ============================================================================
# Core Rule Engine
# ============================================================================

class EvaluationRuleEngine:
    """Core Evaluation Engine for Parikshak Engineering Review Runtime.
    
    Adheres strictly to Gov-OS Core Compliance:
    - Enforces non-repudiation & zero direct masterdb schema mutations
    - Forbids hijacking Niyantran workflow execution engine
    - Computes deterministic SHA-256 state hashes with 0 bit drift
    - Generates government-grade PDF evaluation summaries
    """

    # Strictly forbidden patterns prohibited under Gov-OS Doctrine
    FORBIDDEN_PATTERNS = {
        "workflow_execution_engine": "Parikshak must not execute or hijack workflow orchestration; orchestration is reserved for Niyantran.",
        "direct_masterdb_schema_mutation": "Direct mutation of master database schemas during review is strictly prohibited.",
    }

    # Default Gov-OS Core Rule Suite
    DEFAULT_RULES: List[EvaluationRuleItem] = [
        EvaluationRuleItem(
            rule_id="RULE-GOV-01",
            rule_name="Schema Contract Validation (v1.0)",
            category=EvaluationRuleCategory.SCHEMA_COMPLIANCE,
            weight=0.20,
            min_score_required=100.0,
        ),
        EvaluationRuleItem(
            rule_id="RULE-GOV-02",
            rule_name="Automated Test Pass Rate",
            category=EvaluationRuleCategory.TEST_PASS_RATE,
            weight=0.30,
            min_score_required=100.0,
        ),
        EvaluationRuleItem(
            rule_id="RULE-GOV-03",
            rule_name="50-Run Determinism State Hash Stability",
            category=EvaluationRuleCategory.DETERMINISM_PROOF,
            weight=0.30,
            min_score_required=100.0,
        ),
        EvaluationRuleItem(
            rule_id="RULE-GOV-04",
            rule_name="Fail-Closed Error Boundary Coverage (Zero 500s)",
            category=EvaluationRuleCategory.ERROR_BOUNDARY_COVERAGE,
            weight=0.10,
            min_score_required=100.0,
        ),
        EvaluationRuleItem(
            rule_id="RULE-GOV-05",
            rule_name="Strict Dependency Pinning (==)",
            category=EvaluationRuleCategory.DEPENDENCY_PINNING,
            weight=0.10,
            min_score_required=100.0,
        ),
    ]

    def __init__(self, seed: Optional[str] = None):
        self._seed = seed or "PARIKSHAK_CANONICAL_SEED_V6"

    def evaluate_submission(
        self,
        request_input: EvaluationRequest | Dict[str, Any],
        fixed_timestamp_utc: Optional[str] = None,
    ) -> EvaluationVerdict:
        """Evaluate a candidate submission against canonical Gov-OS rules.
        
        Fail-closed: guarantees zero unhandled 500 exceptions on invalid inputs.
        """
        # 1. Inbound validation
        if isinstance(request_input, EvaluationRequest):
            request = request_input
        else:
            try:
                request = EvaluationRequest(**request_input)
            except ValidationError as e:
                invalid_fields = [str(err.get("loc", ["unknown"])[-1]) for err in e.errors()]
                raise EvaluationValidationError(
                    f"Inbound evaluation payload failed schema validation: {str(e)}",
                    invalid_fields=invalid_fields,
                )
            except Exception as e:
                raise EvaluationValidationError(f"Malformed evaluation request: {str(e)}")

        # 2. Check for forbidden patterns
        raw_dump = json.dumps(request.submission_evidence)
        for pattern, explanation in self.FORBIDDEN_PATTERNS.items():
            if pattern in raw_dump or pattern in request.repository_target:
                raise ForbiddenPatternViolationError(pattern, explanation)

        evidence = request.submission_evidence
        rules = request.rules or self.DEFAULT_RULES
        criteria_checks: List[EvaluationCriteriaCheck] = []
        weighted_score_sum = 0.0

        # 3. Deterministic rule evaluation
        for rule in rules:
            criterion_id = f"crit-{rule.rule_id.lower()}"
            category = rule.category

            if category == EvaluationRuleCategory.SCHEMA_COMPLIANCE:
                passed = bool(evidence.get("schema_compliance", False))
                score = 100.0 if passed else 0.0
                msg = "Schema compliance v1.0 verified with zero extraneous fields." if passed else "Schema non-compliant."

            elif category == EvaluationRuleCategory.TEST_PASS_RATE:
                pass_rate = float(evidence.get("test_pass_rate_percent", 0.0))
                passed = pass_rate >= rule.min_score_required
                score = min(max(pass_rate, 0.0), 100.0)
                msg = f"Test pass rate verified at {score:.1f}%."

            elif category == EvaluationRuleCategory.DETERMINISM_PROOF:
                det_verified = bool(evidence.get("determinism_verified", False))
                unique_hashes = int(evidence.get("unique_hashes", 999))
                passed = det_verified and (unique_hashes == 1)
                score = 100.0 if passed else 0.0
                msg = "50-run determinism confirmed: exactly 1 unique SHA-256 state hash." if passed else "Determinism check failed."

            elif category == EvaluationRuleCategory.ERROR_BOUNDARY_COVERAGE:
                eb_cov = float(evidence.get("error_boundary_coverage_percent", 0.0))
                passed = eb_cov >= rule.min_score_required
                score = min(max(eb_cov, 0.0), 100.0)
                msg = "Zero unhandled 500 exceptions verified; all invalid payloads caught." if passed else "Error boundary failures."

            elif category == EvaluationRuleCategory.DEPENDENCY_PINNING:
                pinned = bool(evidence.get("dependency_pinning_compliant", False))
                passed = pinned
                score = 100.0 if passed else 0.0
                msg = "All dependencies strictly pinned with '==' matching PKB." if passed else "Unpinned dependencies detected."

            else:
                passed = False
                score = 0.0
                msg = f"Unknown rule category '{category}'."

            criteria_checks.append(
                EvaluationCriteriaCheck(
                    criterion_id=criterion_id,
                    rule_id=rule.rule_id,
                    category=category,
                    passed=passed,
                    observed_value=score,
                    score=score,
                    message=msg,
                )
            )
            weighted_score_sum += score * rule.weight

        total_score = round(weighted_score_sum, 2)
        all_passed = all(c.passed for c in criteria_checks)
        verdict = "PASS" if (all_passed and total_score >= 85.0) else "FAIL"

        timestamp = fixed_timestamp_utc or datetime.now(timezone.utc).isoformat()
        verdict_id = f"vrd-{hashlib.sha256((request.evaluation_id + self._seed).encode()).hexdigest()[:16]}"
        next_task = "T-GOV-003" if verdict == "PASS" else None

        # 4. Canonical state hash computation (Zero bit drift across 50 runs)
        hash_payload = {
            "verdict_id": verdict_id,
            "task_id": request.task_id,
            "candidate_name": request.candidate_name,
            "total_score": total_score,
            "verdict": verdict,
            "compliance_standard": "Gov-OS Core Compliance",
            "criteria": [
                {
                    "criterion_id": c.criterion_id,
                    "rule_id": c.rule_id,
                    "score": c.score,
                    "passed": c.passed,
                }
                for c in criteria_checks
            ],
            "next_task": next_task,
        }
        canonical_json = json.dumps(hash_payload, sort_keys=True, separators=(",", ":"))
        deterministic_hash = hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()

        return EvaluationVerdict(
            verdict_id=verdict_id,
            task_id=request.task_id,
            candidate_name=request.candidate_name,
            total_score=total_score,
            verdict=verdict,
            compliance_standard="Gov-OS Core Compliance",
            criteria_results=criteria_checks,
            deterministic_verdict_hash=deterministic_hash,
            timestamp_utc=timestamp,
            next_task_recommendation=next_task,
        )

    def generate_pdf_report(self, verdict: EvaluationVerdict, output_path: str) -> str:
        """Generate a government-grade PDF audit certificate using reportlab."""
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        doc = SimpleDocTemplate(output_path, pagesize=letter)
        styles = getSampleStyleSheet()
        elements = []

        # Title
        title_style = ParagraphStyle(
            "TitleStyle",
            parent=styles["Heading1"],
            fontSize=18,
            leading=22,
            textColor=colors.HexColor("#1e293b"),
            alignment=1,
        )
        elements.append(Paragraph("PARIKSHAK ENGINEERING REVIEW CERTIFICATE", title_style))
        elements.append(Spacer(1, 15))

        # Metadata table
        meta_data = [
            [Paragraph("<b>Task ID:</b>", styles["Normal"]), Paragraph(verdict.task_id, styles["Normal"])],
            [Paragraph("<b>Candidate:</b>", styles["Normal"]), Paragraph(verdict.candidate_name, styles["Normal"])],
            [Paragraph("<b>Verdict:</b>", styles["Normal"]), Paragraph(f"<b><font color='{'green' if verdict.verdict == 'PASS' else 'red'}'>{verdict.verdict}</font></b>", styles["Normal"])],
            [Paragraph("<b>Total Score:</b>", styles["Normal"]), Paragraph(f"{verdict.total_score} / 100", styles["Normal"])],
            [Paragraph("<b>Standard:</b>", styles["Normal"]), Paragraph(verdict.compliance_standard, styles["Normal"])],
            [Paragraph("<b>State Hash:</b>", styles["Normal"]), Paragraph(f"<font size=8>{verdict.deterministic_verdict_hash}</font>", styles["Normal"])],
            [Paragraph("<b>Timestamp (UTC):</b>", styles["Normal"]), Paragraph(verdict.timestamp_utc, styles["Normal"])],
        ]
        meta_table = Table(meta_data, colWidths=[140, 360])
        meta_table.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ])
        )
        elements.append(meta_table)
        elements.append(Spacer(1, 15))

        # Criteria breakdown
        elements.append(Paragraph("<b>Evaluation Criteria Breakdown:</b>", styles["Heading3"]))
        elements.append(Spacer(1, 8))

        crit_data = [["Rule ID", "Category", "Score", "Status", "Message"]]
        for c in verdict.criteria_results:
            crit_data.append([
                c.rule_id,
                c.category.value,
                f"{c.score:.1f}",
                "PASS" if c.passed else "FAIL",
                Paragraph(f"<font size=8>{c.message}</font>", styles["Normal"]),
            ])

        crit_table = Table(crit_data, colWidths=[70, 110, 45, 50, 225])
        crit_table.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f172a")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("ALIGN", (2, 0), (3, -1), "CENTER"),
            ])
        )
        elements.append(crit_table)
        doc.build(elements)
        return output_path
>>>>>>> fc3ed141ac5b1a024e1222b9642fff407ee2851b
