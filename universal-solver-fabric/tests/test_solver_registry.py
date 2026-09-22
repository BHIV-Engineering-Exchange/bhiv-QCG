"""
tests/test_solver_registry.py — Phase 2: SolverRegistry Unit Tests

Validates registration, duplicate detection, removal, enable/disable lifecycle,
input validation, capability search, and compatibility lookup.
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from solver_registry import SolverRegistry, RegistryError

SCHEMA_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "solver_contract.schema.json",
)


def _make_solver(solver_id="TEST_CP_01", version="1.0.0", problem_types=None, **overrides):
    base = {
        "solver_id": solver_id,
        "solver_name": f"Test Solver {solver_id}",
        "solver_type": "CP",
        "version": version,
        "supported_problem_types": problem_types or ["CP", "MILP"],
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
def registry():
    return SolverRegistry(SCHEMA_PATH)


class TestRegistration:

    def test_successful_registration(self, registry):
        sid = registry.register_solver(_make_solver())
        assert sid == "TEST_CP_01"
        assert registry.get_health_status(sid) == "ENABLED"

    def test_duplicate_version_rejected(self, registry):
        registry.register_solver(_make_solver())
        with pytest.raises(RegistryError, match="already registered"):
            registry.register_solver(_make_solver())

    def test_different_version_accepted(self, registry):
        registry.register_solver(_make_solver(version="1.0.0"))
        sid = registry.register_solver(_make_solver(version="2.0.0"))
        assert sid == "TEST_CP_01"

    def test_invalid_schema_rejected(self, registry):
        invalid = _make_solver()
        del invalid["solver_type"]
        with pytest.raises(RegistryError, match="invalid"):
            registry.register_solver(invalid)

    def test_none_metadata_rejected(self, registry):
        with pytest.raises(RegistryError, match="non-empty"):
            registry.register_solver(None)

    def test_empty_dict_rejected(self, registry):
        with pytest.raises(RegistryError):
            registry.register_solver({})

    def test_non_dict_rejected(self, registry):
        with pytest.raises(RegistryError, match="non-empty"):
            registry.register_solver("not a dict")


class TestRemoval:

    def test_remove_existing(self, registry):
        registry.register_solver(_make_solver())
        registry.remove_solver("TEST_CP_01")
        assert registry.get_health_status("TEST_CP_01") == "UNKNOWN"

    def test_remove_nonexistent_raises(self, registry):
        with pytest.raises(RegistryError, match="not found"):
            registry.remove_solver("DOES_NOT_EXIST")


class TestEnableDisable:

    def test_disable_solver(self, registry):
        registry.register_solver(_make_solver())
        registry.disable_solver("TEST_CP_01")
        assert registry.get_health_status("TEST_CP_01") == "DISABLED"

    def test_enable_solver(self, registry):
        registry.register_solver(_make_solver())
        registry.disable_solver("TEST_CP_01")
        registry.enable_solver("TEST_CP_01")
        assert registry.get_health_status("TEST_CP_01") == "ENABLED"

    def test_disabled_excluded_from_search(self, registry):
        registry.register_solver(_make_solver())
        registry.disable_solver("TEST_CP_01")
        results = registry.search_capabilities()
        assert len(results) == 0

    def test_disabled_excluded_from_lookup(self, registry):
        registry.register_solver(_make_solver())
        registry.disable_solver("TEST_CP_01")
        results = registry.compatibility_lookup("CP")
        assert len(results) == 0

    def test_enable_nonexistent_raises(self, registry):
        with pytest.raises(RegistryError, match="not found"):
            registry.enable_solver("FAKE")

    def test_disable_nonexistent_raises(self, registry):
        with pytest.raises(RegistryError, match="not found"):
            registry.disable_solver("FAKE")


class TestSearch:

    def test_search_all_capabilities(self, registry):
        registry.register_solver(_make_solver("S1"))
        registry.register_solver(_make_solver("S2"))
        results = registry.search_capabilities()
        assert len(results) == 2

    def test_search_by_type(self, registry):
        registry.register_solver(_make_solver("S1", solver_type="CP"))
        registry.register_solver(_make_solver("S2", solver_type="MIP"))
        results = registry.search_capabilities(solver_type="MIP")
        assert len(results) == 1
        assert results[0]["solver_id"] == "S2"

    def test_compatibility_lookup(self, registry):
        registry.register_solver(_make_solver("S1", problem_types=["CP"]))
        registry.register_solver(_make_solver("S2", problem_types=["QUBO"]))
        results = registry.compatibility_lookup("QUBO")
        assert len(results) == 1
        assert results[0]["solver_id"] == "S2"

    def test_compatibility_with_constraint(self, registry):
        registry.register_solver(_make_solver("S1"))
        results = registry.compatibility_lookup("CP", required_constraint="LINEAR")
        assert len(results) == 1
        results = registry.compatibility_lookup("CP", required_constraint="NONLINEAR")
        assert len(results) == 0


class TestProperties:

    def test_solver_count(self, registry):
        assert registry.solver_count == 0
        registry.register_solver(_make_solver("S1"))
        assert registry.solver_count == 1

    def test_active_solver_count(self, registry):
        registry.register_solver(_make_solver("S1"))
        registry.register_solver(_make_solver("S2"))
        assert registry.active_solver_count == 2
        registry.disable_solver("S1")
        assert registry.active_solver_count == 1

    def test_get_solver_metadata(self, registry):
        registry.register_solver(_make_solver())
        meta = registry.get_solver_metadata("TEST_CP_01")
        assert meta is not None
        assert meta["solver_id"] == "TEST_CP_01"

    def test_get_unknown_solver_metadata(self, registry):
        assert registry.get_solver_metadata("FAKE") is None

    def test_unknown_health_status(self, registry):
        assert registry.get_health_status("FAKE") == "UNKNOWN"
