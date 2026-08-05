import uuid
import time
from typing import Dict, Any, Optional
from solver_interfaces.base import BaseSolverAdapter

class ExecutionAdapter:
    """
    The ExecutionAdapter wraps any BaseSolverAdapter to enforce BCAB compliance.
    It acts as the strict boundary that guarantees every execution produces 
    replay-safe evidence and provenance metadata.
    """
    def __init__(self, solver: BaseSolverAdapter, solver_metadata: Dict[str, Any]):
        self.solver = solver
        self.solver_metadata = solver_metadata
        self.fabric_version = "1.0.0"

    def execute_with_evidence(self, problem: Dict[str, Any], timeout_seconds: Optional[int] = None) -> Dict[str, Any]:
        """
        Executes the problem and wraps the result in an Evidence Package.
        """
        # 1. Generate execution identities
        trace_id = str(uuid.uuid4())
        replay_id = str(uuid.uuid4())
        execution_start_ms = int(time.time() * 1000)

        # 2. Bind problem to the underlying solver
        self.solver.bind_problem(problem)

        # 3. Execute
        try:
            raw_result = self.solver.execute(timeout_seconds=timeout_seconds)
            status = "COMPLETED"
        except Exception as e:
            raw_result = {"error": str(e)}
            status = "FAILED"

        execution_end_ms = int(time.time() * 1000)

        # 4. Construct Replay-safe Evidence Package
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
                "attachment_mode": self.solver_metadata.get("attachment_mode", "LOCAL")
            },
            "deterministic_inputs": {
                "problem_type": problem.get("problem_type", "UNKNOWN"),
                "constraints_applied": problem.get("required_constraints", [])
            },
            "result": raw_result
        }

        # 5. Publish to Live Bucket (Canonical Truth Layer)
        import os
        import sys
        # Add parent directory to path so we can import bucket_client
        parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        if parent_dir not in sys.path:
            sys.path.insert(0, parent_dir)
        import bucket_client
        from datetime import datetime, timezone

        client = bucket_client.get_client()
        bucket_payload = {
            "artifact_id": str(uuid.uuid4()),
            "trace_id": trace_id,
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "schema_version": "1.0.0",
            "source_module_id": f"usf_{self.solver_metadata.get('solver_id', 'UNKNOWN').lower()}",
            "artifact_type": "solver_evidence",
            "parent_hash": "", # Let bucket_client dynamic trace continuity handle this if empty
            "payload": evidence_package
        }
        
        success, response = client.publish_artifact(bucket_payload)
        
        if success:
            evidence_package["bucket_hash"] = response.get("hash")
            evidence_package["bucket_parent_hash"] = response.get("parent_hash")
            evidence_package["bucket_artifact_id"] = response.get("artifact_id")

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
