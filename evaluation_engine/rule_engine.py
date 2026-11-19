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
