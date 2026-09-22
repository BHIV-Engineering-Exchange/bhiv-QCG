"""
tests/test_e2e_usf_qcg.py — Phase 2: E2E USF ↔ QCG Integration Tests

End-to-end tests validating the full solver pipeline from registration
through evidence verification, including QCG evidence chain compatibility.
"""

import pytest
import hashlib
import json
import sys
import os
import tempfile
import shutil
from typing import Dict, Any, Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from solver_registry import SolverRegistry, RegistryError
from solver_selection_engine import SolverSelectionEngine
from execution_adapter import ExecutionAdapter
from runtime_validation import ValidatingSolverAdapter
from telemetry import EvidencePublisher, USFMetrics
from solver_interfaces.base import BaseSolverAdapter


SCHEMA_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "solver_contract.schema.json",
)


def _make_solver(solver_id="E2E_CP_01", **overrides):
    base = {
        "solver_id": solver_id,
        "solver_name": f"E2E Solver {solver_id}",
        "solver_type": "CP",
        "version": "1.0.0",
        "supported_problem_types": ["CP", "MILP"],
        "supported_constraints": ["LINEAR", "LOGICAL"],
        "objective_support": ["SINGLE"],
        "optimization_direction": ["MINIMIZE"],
        "deterministic_capability": True,
        "replay_capability": True,
        "explainability_support": True,
        "execution_requirements": {"hardware": "CPU", "distributed": False},
        "resource_requirements": {"memory_mb_min": 512, "cores_min": 1},
        "estimated_cost": "LOW",
        "estimated_runtime": "SECONDS",
        "confidence_model": "EXACT",
        "authority_limits": {"max_variables": 1000, "max_constraints": 1000},
        "attachment_mode": "LOCAL",
        "schema_version": "1.0.0",
    }
    base.update(overrides)
    return base


class TestE2EFullPipeline:

    def test_register_select_execute_verify(self):
        """
        E2E: Register solver → select for problem → execute → evidence package is valid.
        """
        registry = SolverRegistry(SCHEMA_PATH)
        registry.register_solver(_make_solver("PIPELINE_01"))

        engine = SolverSelectionEngine(registry)
        problem = {
            "problem_type": "MILP",
            "required_constraints": ["LINEAR"],
            "require_deterministic": True,
        }

        recommendations = engine.select_solvers(problem)
        assert len(recommendations) >= 1
        selected = recommendations[0]
        assert selected["solver_id"] == "PIPELINE_01"

        solver = ValidatingSolverAdapter(simulate_failure=False)
        adapter = ExecutionAdapter(solver, selected)
        evidence = adapter.execute_with_evidence(problem, timeout_seconds=10)

        # Verify evidence package structure
        assert evidence["status"] == "COMPLETED"
        assert evidence["trace_id"] != ""
        assert evidence["replay_id"] != ""
        assert evidence["provenance"]["fabric_version"] == "1.0.0"
        assert evidence["provenance"]["solver_id"] == "PIPELINE_01"
        assert evidence["deterministic_inputs"]["problem_type"] == "MILP"
        assert len(evidence["evidence_hash"]) == 64

    def test_multiple_solvers_ranked_correctly(self):
        """
        E2E: Multiple solvers registered, selection returns deterministic ranking.
        """
        registry = SolverRegistry(SCHEMA_PATH)
        registry.register_solver(_make_solver("LOW_COST", estimated_cost="LOW"))
        registry.register_solver(_make_solver("HIGH_COST", estimated_cost="HIGH"))
        registry.register_solver(_make_solver("MED_COST", estimated_cost="MEDIUM"))

        engine = SolverSelectionEngine(registry)
        results = engine.select_solvers({"problem_type": "CP"})

        assert len(results) == 3
        assert results[0]["solver_id"] == "LOW_COST"
        assert results[2]["solver_id"] == "HIGH_COST"

    def test_evidence_published_to_disk(self):
        """
        E2E: Evidence published via EvidencePublisher is valid JSON on disk.
        """
        tmp_dir = tempfile.mkdtemp()
        try:
            registry = SolverRegistry(SCHEMA_PATH)
            registry.register_solver(_make_solver("PUBLISH_01"))

            engine = SolverSelectionEngine(registry)
            selected = engine.select_solvers({"problem_type": "MILP"})[0]

            solver = ValidatingSolverAdapter(simulate_failure=False)
            adapter = ExecutionAdapter(solver, selected)
            evidence = adapter.execute_with_evidence({"problem_type": "MILP"})

            publisher = EvidencePublisher(storage_path=tmp_dir)
            uri = publisher.publish(evidence)
            assert "PUBLISH_01" not in uri  # URI uses trace_id, not solver_id

            file_path = os.path.join(tmp_dir, f"{evidence['trace_id']}.json")
            assert os.path.exists(file_path)

            with open(file_path) as f:
                loaded = json.load(f)
            assert loaded["trace_id"] == evidence["trace_id"]
            assert loaded["evidence_hash"] == evidence["evidence_hash"]
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)


class TestE2EFailureRecovery:

    def test_solver_crash_produces_structured_evidence(self):
        """
        E2E: Solver crash produces FAILED evidence without crashing the fabric.
        """
        registry = SolverRegistry(SCHEMA_PATH)
        registry.register_solver(_make_solver("CRASH_01"))

        engine = SolverSelectionEngine(registry)
        selected = engine.select_solvers({"problem_type": "MILP"})[0]

        solver = ValidatingSolverAdapter(simulate_failure=True)
        adapter = ExecutionAdapter(solver, selected)
        evidence = adapter.execute_with_evidence({"problem_type": "MILP"})

        assert evidence["status"] == "FAILED"
        assert "error" in evidence["result"]
        assert evidence["provenance"]["solver_id"] == "CRASH_01"
        assert len(evidence["evidence_hash"]) == 64

    def test_capability_mismatch_returns_empty(self):
        """
        E2E: Unsupported problem type returns empty recommendations.
        """
        registry = SolverRegistry(SCHEMA_PATH)
        registry.register_solver(_make_solver("CP_ONLY", supported_problem_types=["CP"]))

        engine = SolverSelectionEngine(registry)
        results = engine.select_solvers({"problem_type": "NLP"})
        assert results == []


class TestE2EEvidenceIntegrity:

    def test_evidence_hash_tamper_detection(self):
        """
        E2E: Modifying the evidence result invalidates the evidence hash.
        """
        registry = SolverRegistry(SCHEMA_PATH)
        registry.register_solver(_make_solver("TAMPER_01"))

        engine = SolverSelectionEngine(registry)
        selected = engine.select_solvers({"problem_type": "MILP"})[0]

        solver = ValidatingSolverAdapter(simulate_failure=False)
        adapter = ExecutionAdapter(solver, selected)
        evidence = adapter.execute_with_evidence({"problem_type": "MILP"})

        original_hash = evidence["evidence_hash"]

        # Tamper with result
        evidence["result"]["objective_value"] = 999999.0

        # Recompute hash
        canonical = json.dumps(
            {"deterministic_inputs": evidence["deterministic_inputs"], "result": evidence["result"]},
            sort_keys=True, default=str,
        )
        tampered_hash = hashlib.sha256(canonical.encode()).hexdigest()

        assert original_hash != tampered_hash

    def test_qcg_compatible_evidence_fields(self):
        """
        E2E: USF evidence packages contain all fields required for QCG EvidenceLedger compatibility.
        """
        registry = SolverRegistry(SCHEMA_PATH)
        registry.register_solver(_make_solver("QCG_COMPAT"))

        engine = SolverSelectionEngine(registry)
        selected = engine.select_solvers({"problem_type": "MILP"})[0]

        solver = ValidatingSolverAdapter(simulate_failure=False)
        adapter = ExecutionAdapter(solver, selected)
        evidence = adapter.execute_with_evidence({"problem_type": "MILP"})

        # QCG EvidenceLedger requires: trace_id, status, provenance, evidence_hash
        assert "trace_id" in evidence
        assert "status" in evidence
        assert "provenance" in evidence
        assert "evidence_hash" in evidence
        assert "replay_id" in evidence

        # Provenance must have timestamps and version info
        prov = evidence["provenance"]
        assert "timestamp_start_ms" in prov
        assert "timestamp_end_ms" in prov
        assert "execution_duration_ms" in prov
        assert "fabric_version" in prov
        assert "solver_id" in prov
        assert "solver_version" in prov

    def test_metrics_tracked_across_pipeline(self):
        """
        E2E: USFMetrics tracks executions across the full pipeline.
        """
        metrics = USFMetrics()
        metrics.reset()

        registry = SolverRegistry(SCHEMA_PATH)
        registry.register_solver(_make_solver("METRICS_01"))

        engine = SolverSelectionEngine(registry)
        selected = engine.select_solvers({"problem_type": "MILP"})[0]

        # 2 successful, 1 failed
        for i in range(2):
            solver = ValidatingSolverAdapter(simulate_failure=False)
            adapter = ExecutionAdapter(solver, selected)
            evidence = adapter.execute_with_evidence({"problem_type": "MILP"})
            metrics.record_execution(
                evidence["provenance"]["execution_duration_ms"],
                success=(evidence["status"] == "COMPLETED"),
            )

        solver = ValidatingSolverAdapter(simulate_failure=True)
        adapter = ExecutionAdapter(solver, selected)
        evidence = adapter.execute_with_evidence({"problem_type": "MILP"})
        metrics.record_execution(
            evidence["provenance"]["execution_duration_ms"],
            success=(evidence["status"] == "COMPLETED"),
        )

        s = metrics.summary
        assert s["execution_count"] == 3
        assert s["error_count"] == 1
        assert 0.6 < s["success_rate"] < 0.7
