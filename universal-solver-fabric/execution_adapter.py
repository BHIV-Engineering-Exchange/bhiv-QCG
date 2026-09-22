import hashlib
import json
import logging
import uuid
import time
import threading
from typing import Dict, Any, Optional
from solver_interfaces.base import BaseSolverAdapter

logger = logging.getLogger("usf.execution_adapter")


class ExecutionAdapter:
    """
    The ExecutionAdapter wraps any BaseSolverAdapter to enforce BCAB compliance.
    It acts as the strict boundary that guarantees every execution produces
    replay-safe evidence and provenance metadata.

    Phase 2 additions:
    - Timeout enforcement via threading
    - Evidence hash generation (SHA-256) for tamper detection
    - Error boundary around solver.execute()
    """

    def __init__(self, solver: BaseSolverAdapter, solver_metadata: Dict[str, Any]):
        self.solver = solver
        self.solver_metadata = solver_metadata
        self.fabric_version = "1.0.0"

    def _compute_evidence_hash(self, deterministic_inputs: dict, result: dict) -> str:
        """Compute a SHA-256 hash of the deterministic inputs + result for tamper detection."""
        canonical = json.dumps(
            {"deterministic_inputs": deterministic_inputs, "result": result},
            sort_keys=True,
            default=str,
        )
        return hashlib.sha256(canonical.encode()).hexdigest()

    def execute_with_evidence(self, problem: Dict[str, Any], timeout_seconds: Optional[int] = None) -> Dict[str, Any]:
        """
        Executes the problem and wraps the result in an Evidence Package.
        Enforces timeout and produces tamper-evident evidence hashes.
        """
        # 1. Generate execution identities
        trace_id = str(uuid.uuid4())
        replay_id = str(uuid.uuid4())
        execution_start_ms = int(time.time() * 1000)

        # 2. Bind problem to the underlying solver
        try:
            self.solver.bind_problem(problem)
        except Exception as e:
            logger.error(f"Failed to bind problem to solver: {type(e).__name__}: {e}")
            return self._build_evidence(
                trace_id, replay_id, execution_start_ms,
                {"error": f"Bind failure: {e}"}, "FAILED", problem,
            )

        # 3. Execute with timeout enforcement
        raw_result = {}
        status = "COMPLETED"

        if timeout_seconds and timeout_seconds > 0:
            result_container = {"result": None, "error": None}

            def _run():
                try:
                    result_container["result"] = self.solver.execute(timeout_seconds=timeout_seconds)
                except Exception as e:
                    result_container["error"] = e

            thread = threading.Thread(target=_run, daemon=True)
            thread.start()
            thread.join(timeout=timeout_seconds)

            if thread.is_alive():
                logger.warning(f"Solver execution timed out after {timeout_seconds}s for trace {trace_id}")
                raw_result = {"error": f"Execution timed out after {timeout_seconds}s"}
                status = "FAILED"
            elif result_container["error"]:
                raw_result = {"error": str(result_container["error"])}
                status = "FAILED"
            else:
                raw_result = result_container["result"]
        else:
            try:
                raw_result = self.solver.execute(timeout_seconds=timeout_seconds)
            except Exception as e:
                raw_result = {"error": str(e)}
                status = "FAILED"

        return self._build_evidence(trace_id, replay_id, execution_start_ms, raw_result, status, problem)

    def _build_evidence(
        self,
        trace_id: str,
        replay_id: str,
        execution_start_ms: int,
        raw_result: dict,
        status: str,
        problem: dict,
    ) -> Dict[str, Any]:
        """Construct a replay-safe evidence package with tamper-detection hash."""
        execution_end_ms = int(time.time() * 1000)

        deterministic_inputs = {
            "problem_type": problem.get("problem_type", "UNKNOWN"),
            "constraints_applied": problem.get("required_constraints", []),
        }

        evidence_hash = self._compute_evidence_hash(deterministic_inputs, raw_result)

        evidence_package = {
            "trace_id": trace_id,
            "replay_id": replay_id,
            "status": status,
            "provenance": {
                "timestamp_start_ms": execution_start_ms,
                "timestamp_end_ms": execution_end_ms,
                "execution_duration_ms": execution_end_ms - execution_start_ms,
                "fabric_version": self.fabric_version,
                "solver_id": self.solver_metadata.get("solver_id", "UNKNOWN"),
                "solver_version": self.solver_metadata.get("version", "UNKNOWN"),
                "attachment_mode": self.solver_metadata.get("attachment_mode", "LOCAL"),
            },
            "deterministic_inputs": deterministic_inputs,
            "result": raw_result,
            "evidence_hash": evidence_hash,
        }

        if status == "FAILED":
            logger.warning(f"Execution FAILED for trace {trace_id}: {raw_result.get('error', 'unknown')}")
        else:
            logger.info(f"Execution COMPLETED for trace {trace_id} (hash={evidence_hash[:16]}...)")

        return evidence_package


if __name__ == "__main__":
    # Verification test
    class MockSolver(BaseSolverAdapter):
        def bind_problem(self, problem: Dict[str, Any]) -> None:
            pass
        def execute(self, timeout_seconds: Optional[int] = None) -> Dict[str, Any]:
            return {"objective_value": 42.0, "decision_variables": {"x1": 1}}
        def get_health(self) -> str:
            return "HEALTHY"

    print("Running Evidence Package Verification...")
    mock_metadata = {
        "solver_id": "MOCK_SOLVER_01",
        "version": "1.0.0",
        "attachment_mode": "LOCAL"
    }
    adapter = ExecutionAdapter(MockSolver(), mock_metadata)

    test_problem = {
        "problem_type": "MILP",
        "required_constraints": ["LINEAR"]
    }

    evidence = adapter.execute_with_evidence(test_problem)

    import json
    print(json.dumps(evidence, indent=2))
