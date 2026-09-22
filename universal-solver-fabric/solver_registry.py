import json
import os
import logging
import threading
import jsonschema
from jsonschema import validate
from typing import Dict, List, Optional, Any

logger = logging.getLogger("usf.solver_registry")


class RegistryError(Exception):
    pass


class SolverRegistry:
    """
    Thread-safe in-memory registry for solver capabilities.

    Validates solver metadata against a JSON schema on registration.
    Supports enable/disable lifecycle, capability search, and compatibility lookup.
    """

    def __init__(self, schema_path: str):
        self._solvers: Dict[str, Dict[str, Any]] = {}
        self._disabled_solvers: set = set()
        self._lock = threading.Lock()

        try:
            with open(schema_path, 'r') as f:
                self.schema = json.load(f)
        except Exception as e:
            raise RegistryError(f"Failed to load schema from {schema_path}: {e}")

    def register_solver(self, solver_metadata: Dict[str, Any]) -> str:
        """Registers a new solver capability, validating against the JSON schema."""
        if not solver_metadata or not isinstance(solver_metadata, dict):
            raise RegistryError("Solver metadata must be a non-empty dictionary.")

        try:
            validate(instance=solver_metadata, schema=self.schema)
        except jsonschema.exceptions.ValidationError as e:
            raise RegistryError(f"Solver metadata is invalid: {e.message}")

        solver_id = solver_metadata.get("solver_id")
        with self._lock:
            if solver_id in self._solvers:
                # Check version conflicts
                if self._solvers[solver_id]["version"] == solver_metadata["version"]:
                    raise RegistryError(f"Solver {solver_id} version {solver_metadata['version']} is already registered.")

            self._solvers[solver_id] = solver_metadata
            self._disabled_solvers.discard(solver_id)

        logger.info(f"Solver registered: {solver_id} v{solver_metadata.get('version')}")
        return solver_id

    def remove_solver(self, solver_id: str) -> None:
        """Removes a solver from the registry."""
        with self._lock:
            if solver_id in self._solvers:
                del self._solvers[solver_id]
                self._disabled_solvers.discard(solver_id)
                logger.info(f"Solver removed: {solver_id}")
            else:
                raise RegistryError(f"Solver {solver_id} not found.")

    def enable_solver(self, solver_id: str) -> None:
        """Enables a solver."""
        with self._lock:
            if solver_id not in self._solvers:
                raise RegistryError(f"Solver {solver_id} not found.")
            self._disabled_solvers.discard(solver_id)
            logger.info(f"Solver enabled: {solver_id}")

    def disable_solver(self, solver_id: str) -> None:
        """Disables a solver so it won't be returned in lookups."""
        with self._lock:
            if solver_id not in self._solvers:
                raise RegistryError(f"Solver {solver_id} not found.")
            self._disabled_solvers.add(solver_id)
            logger.info(f"Solver disabled: {solver_id}")

    def get_health_status(self, solver_id: str) -> str:
        """Returns the health status of a solver (ENABLED, DISABLED, or UNKNOWN)."""
        with self._lock:
            if solver_id not in self._solvers:
                return "UNKNOWN"
            return "DISABLED" if solver_id in self._disabled_solvers else "ENABLED"

    def get_solver_metadata(self, solver_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves full metadata for a specific solver."""
        with self._lock:
            return self._solvers.get(solver_id)

    def search_capabilities(self, **kwargs) -> List[Dict[str, Any]]:
        """
        Search for solvers matching specific criteria.
        Example: registry.search_capabilities(solver_type="CP", deterministic_capability=True)
        """
        results = []
        with self._lock:
            for solver_id, meta in self._solvers.items():
                if solver_id in self._disabled_solvers:
                    continue

                match = True
                for k, v in kwargs.items():
                    if k not in meta or meta[k] != v:
                        match = False
                        break
                if match:
                    results.append(meta)

        return results

    def compatibility_lookup(self, required_problem_type: str, required_constraint: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Lookup solvers compatible with a specific problem type and optional constraint.
        """
        results = []
        with self._lock:
            for solver_id, meta in self._solvers.items():
                if solver_id in self._disabled_solvers:
                    continue

                # Check problem type support
                if required_problem_type not in meta.get("supported_problem_types", []):
                    continue

                # Check constraint support if provided
                if required_constraint and required_constraint not in meta.get("supported_constraints", []):
                    continue

                results.append(meta)

        return results

    @property
    def solver_count(self) -> int:
        """Returns the number of registered solvers."""
        with self._lock:
            return len(self._solvers)

    @property
    def active_solver_count(self) -> int:
        """Returns the number of enabled (active) solvers."""
        with self._lock:
            return len(self._solvers) - len(self._disabled_solvers)
