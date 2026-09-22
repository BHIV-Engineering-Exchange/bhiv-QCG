"""
tests/test_selection_engine.py — Phase 2: SolverSelectionEngine Unit Tests

Validates compatibility filtering, deterministic ranking, error boundary
on malformed solvers, and edge cases.
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from solver_registry import SolverRegistry
from solver_selection_engine import SolverSelectionEngine

SCHEMA_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "solver_contract.schema.json",
)


def _make_solver(solver_id="TEST_01", **overrides):
    base = {
        "solver_id": solver_id,
        "solver_name": f"Solver {solver_id}",
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


@pytest.fixture
def engine():
    registry = SolverRegistry(SCHEMA_PATH)
    return SolverSelectionEngine(registry), registry


class TestCompatibility:

    def test_matching_problem_type(self, engine):
        eng, reg = engine
        reg.register_solver(_make_solver("S1", supported_problem_types=["MILP"]))
        results = eng.select_solvers({"problem_type": "MILP"})
        assert len(results) == 1

    def test_no_match_problem_type(self, engine):
        eng, reg = engine
        reg.register_solver(_make_solver("S1", supported_problem_types=["CP"]))
        results = eng.select_solvers({"problem_type": "NLP"})
        assert len(results) == 0

    def test_constraint_filter(self, engine):
        eng, reg = engine
        reg.register_solver(_make_solver("S1", supported_constraints=["LINEAR"]))
        results = eng.select_solvers({
            "problem_type": "CP",
            "required_constraints": ["LINEAR"],
        })
        assert len(results) == 1
        results = eng.select_solvers({
            "problem_type": "CP",
            "required_constraints": ["NONLINEAR"],
        })
        assert len(results) == 0

    def test_deterministic_filter(self, engine):
        eng, reg = engine
        reg.register_solver(_make_solver("S1", deterministic_capability=False))
        results = eng.select_solvers({
            "problem_type": "CP",
            "require_deterministic": True,
        })
        assert len(results) == 0

    def test_resource_filter(self, engine):
        eng, reg = engine
        reg.register_solver(_make_solver("S1", resource_requirements={"memory_mb_min": 4096, "cores_min": 1}))
        results = eng.select_solvers({
            "problem_type": "CP",
            "available_memory_mb": 1024,
        })
        assert len(results) == 0
        results = eng.select_solvers({
            "problem_type": "CP",
            "available_memory_mb": 8192,
        })
        assert len(results) == 1

    def test_authority_limits_filter(self, engine):
        eng, reg = engine
        reg.register_solver(_make_solver("S1", authority_limits={"max_variables": 100, "max_constraints": 100}))
        results = eng.select_solvers({
            "problem_type": "CP",
            "max_variables": 200,
        })
        assert len(results) == 0


class TestDeterministicRanking:

    def test_cost_ranking(self, engine):
        eng, reg = engine
        reg.register_solver(_make_solver("CHEAP", estimated_cost="LOW"))
        reg.register_solver(_make_solver("EXPENSIVE", estimated_cost="HIGH"))
        results = eng.select_solvers({"problem_type": "CP"})
        assert results[0]["solver_id"] == "CHEAP"
        assert results[1]["solver_id"] == "EXPENSIVE"

    def test_runtime_tiebreak(self, engine):
        eng, reg = engine
        reg.register_solver(_make_solver("SLOW", estimated_cost="LOW", estimated_runtime="HOURS"))
        reg.register_solver(_make_solver("FAST", estimated_cost="LOW", estimated_runtime="SECONDS"))
        results = eng.select_solvers({"problem_type": "CP"})
        assert results[0]["solver_id"] == "FAST"

    def test_solver_id_alphabetical_tiebreak(self, engine):
        eng, reg = engine
        reg.register_solver(_make_solver("ZZZ", estimated_cost="LOW", estimated_runtime="SECONDS"))
        reg.register_solver(_make_solver("AAA", estimated_cost="LOW", estimated_runtime="SECONDS"))
        results = eng.select_solvers({"problem_type": "CP"})
        assert results[0]["solver_id"] == "AAA"
        assert results[1]["solver_id"] == "ZZZ"

    def test_full_ranking_order(self, engine):
        eng, reg = engine
        reg.register_solver(_make_solver("CP_01", estimated_cost="LOW"))
        reg.register_solver(_make_solver("CP_02", estimated_cost="MEDIUM"))
        reg.register_solver(_make_solver("CP_03", estimated_cost="LOW"))
        results = eng.select_solvers({"problem_type": "CP"})
        assert len(results) == 3
        assert results[0]["solver_id"] == "CP_01"
        assert results[1]["solver_id"] == "CP_03"
        assert results[2]["solver_id"] == "CP_02"


class TestEdgeCases:

    def test_empty_registry(self, engine):
        eng, reg = engine
        results = eng.select_solvers({"problem_type": "CP"})
        assert results == []

    def test_disabled_solver_excluded(self, engine):
        eng, reg = engine
        reg.register_solver(_make_solver("S1"))
        reg.disable_solver("S1")
        results = eng.select_solvers({"problem_type": "CP"})
        assert len(results) == 0

    def test_empty_problem(self, engine):
        eng, reg = engine
        reg.register_solver(_make_solver("S1"))
        results = eng.select_solvers({})
        assert len(results) == 0
