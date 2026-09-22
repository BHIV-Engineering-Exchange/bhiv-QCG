"""
tests/test_execution_adapter.py — Phase 2: ExecutionAdapter Unit Tests

Validates evidence package generation, failure handling, timeout enforcement,
and evidence hash integrity.
"""

import pytest
import hashlib
import json
import sys
import os
import time
from typing import Dict, Any, Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from execution_adapter import ExecutionAdapter
from solver_interfaces.base import BaseSolverAdapter


class MockSolver(BaseSolverAdapter):
    def __init__(self, result=None, raise_on_execute=False, sleep_time=0):
        self._result = result or {"objective_value": 42.0}
        self._raise = raise_on_execute
        self._sleep = sleep_time
        self.bound_problem = None

    def bind_problem(self, problem: Dict[str, Any]) -> None:
        self.bound_problem = problem

    def execute(self, timeout_seconds: Optional[int] = None) -> Dict[str, Any]:
        if self._sleep > 0:
            time.sleep(self._sleep)
        if self._raise:
            raise RuntimeError("Simulated solver crash")
        return self._result

    def get_health(self) -> str:
        return "HEALTHY"


class FailingBindSolver(BaseSolverAdapter):
    def bind_problem(self, problem: Dict[str, Any]) -> None:
        raise ValueError("Bad problem format")

    def execute(self, timeout_seconds: Optional[int] = None) -> Dict[str, Any]:
        return {}

    def get_health(self) -> str:
        return "HEALTHY"


MOCK_META = {"solver_id": "MOCK_01", "version": "1.0.0", "attachment_mode": "LOCAL"}


class TestSuccessfulExecution:

    def test_produces_valid_evidence(self):
        adapter = ExecutionAdapter(MockSolver(), MOCK_META)
        evidence = adapter.execute_with_evidence({"problem_type": "MILP", "required_constraints": ["LINEAR"]})
        assert evidence["status"] == "COMPLETED"
        assert "trace_id" in evidence
        assert "replay_id" in evidence
        assert "provenance" in evidence
        assert "deterministic_inputs" in evidence
        assert "result" in evidence
        assert "evidence_hash" in evidence

    def test_provenance_metadata(self):
        adapter = ExecutionAdapter(MockSolver(), MOCK_META)
        evidence = adapter.execute_with_evidence({"problem_type": "MILP"})
        prov = evidence["provenance"]
        assert prov["fabric_version"] == "1.0.0"
        assert prov["solver_id"] == "MOCK_01"
        assert prov["solver_version"] == "1.0.0"
        assert prov["execution_duration_ms"] >= 0

    def test_deterministic_inputs_captured(self):
        adapter = ExecutionAdapter(MockSolver(), MOCK_META)
        evidence = adapter.execute_with_evidence({
            "problem_type": "CP",
            "required_constraints": ["LINEAR", "LOGICAL"],
        })
        di = evidence["deterministic_inputs"]
        assert di["problem_type"] == "CP"
        assert di["constraints_applied"] == ["LINEAR", "LOGICAL"]

    def test_result_passthrough(self):
        adapter = ExecutionAdapter(
            MockSolver(result={"x": 1, "y": 2}), MOCK_META
        )
        evidence = adapter.execute_with_evidence({"problem_type": "MILP"})
        assert evidence["result"] == {"x": 1, "y": 2}


class TestEvidenceHash:

    def test_hash_present(self):
        adapter = ExecutionAdapter(MockSolver(), MOCK_META)
        evidence = adapter.execute_with_evidence({"problem_type": "MILP"})
        assert len(evidence["evidence_hash"]) == 64  # SHA-256 hex

    def test_hash_matches_recomputation(self):
        adapter = ExecutionAdapter(MockSolver(), MOCK_META)
        evidence = adapter.execute_with_evidence({"problem_type": "MILP"})
        canonical = json.dumps(
            {"deterministic_inputs": evidence["deterministic_inputs"], "result": evidence["result"]},
            sort_keys=True,
            default=str,
        )
        expected_hash = hashlib.sha256(canonical.encode()).hexdigest()
        assert evidence["evidence_hash"] == expected_hash

    def test_different_inputs_produce_different_hashes(self):
        adapter = ExecutionAdapter(MockSolver(), MOCK_META)
        ev1 = adapter.execute_with_evidence({"problem_type": "MILP"})
        ev2 = adapter.execute_with_evidence({"problem_type": "CP"})
        assert ev1["evidence_hash"] != ev2["evidence_hash"]


class TestFailureHandling:

    def test_solver_crash_produces_failed_evidence(self):
        adapter = ExecutionAdapter(MockSolver(raise_on_execute=True), MOCK_META)
        evidence = adapter.execute_with_evidence({"problem_type": "MILP"})
        assert evidence["status"] == "FAILED"
        assert "error" in evidence["result"]
        assert "Simulated solver crash" in evidence["result"]["error"]

    def test_bind_failure_produces_failed_evidence(self):
        adapter = ExecutionAdapter(FailingBindSolver(), MOCK_META)
        evidence = adapter.execute_with_evidence({"problem_type": "MILP"})
        assert evidence["status"] == "FAILED"
        assert "Bind failure" in evidence["result"]["error"]

    def test_failed_evidence_still_has_hash(self):
        adapter = ExecutionAdapter(MockSolver(raise_on_execute=True), MOCK_META)
        evidence = adapter.execute_with_evidence({"problem_type": "MILP"})
        assert evidence["status"] == "FAILED"
        assert len(evidence["evidence_hash"]) == 64


class TestTimeout:

    def test_timeout_produces_failed_evidence(self):
        adapter = ExecutionAdapter(MockSolver(sleep_time=5), MOCK_META)
        evidence = adapter.execute_with_evidence({"problem_type": "MILP"}, timeout_seconds=1)
        assert evidence["status"] == "FAILED"
        assert "timed out" in evidence["result"]["error"]

    def test_no_timeout_succeeds(self):
        adapter = ExecutionAdapter(MockSolver(sleep_time=0.1), MOCK_META)
        evidence = adapter.execute_with_evidence({"problem_type": "MILP"}, timeout_seconds=5)
        assert evidence["status"] == "COMPLETED"
