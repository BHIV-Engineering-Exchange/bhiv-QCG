import json
import logging
import os
import time
from typing import Dict, Any

# Configure structured JSON logging for Observability
class JsonFormatter(logging.Formatter):
    def format(self, record):
        log_record = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "message": record.getMessage(),
            "logger": record.name
        }
        if hasattr(record, "telemetry"):
            log_record["telemetry"] = record.telemetry
        return json.dumps(log_record)

logger = logging.getLogger("PlatformService.Telemetry")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setFormatter(JsonFormatter())
if not logger.handlers:
    logger.addHandler(handler)


class USFMetrics:
    """
    Lightweight in-process metrics tracker for the Universal Solver Fabric.
    Tracks execution counts, errors, and latency.
    """

    def __init__(self):
        self._execution_count = 0
        self._error_count = 0
        self._total_latency_ms = 0.0
        self._start_time = time.time()

    def record_execution(self, duration_ms: float, success: bool = True) -> None:
        self._execution_count += 1
        self._total_latency_ms += duration_ms
        if not success:
            self._error_count += 1

    @property
    def summary(self) -> Dict[str, Any]:
        avg_latency = (self._total_latency_ms / self._execution_count) if self._execution_count > 0 else 0.0
        return {
            "uptime_seconds": round(time.time() - self._start_time, 2),
            "execution_count": self._execution_count,
            "error_count": self._error_count,
            "success_rate": round(
                (self._execution_count - self._error_count) / max(self._execution_count, 1), 4
            ),
            "avg_latency_ms": round(avg_latency, 2),
        }

    def reset(self) -> None:
        self._execution_count = 0
        self._error_count = 0
        self._total_latency_ms = 0.0
        self._start_time = time.time()


# Module-level singleton
_usf_metrics = USFMetrics()


def get_usf_metrics() -> USFMetrics:
    return _usf_metrics


class EvidencePublisher:
    """
    Publishes execution evidence to local storage (simulating Bucket evidence storage).
    Includes error boundary around file I/O to prevent crashes on disk failures.
    """

    def __init__(self, storage_path: str = "evidence_packet/runtime_logs"):
        self.storage_path = storage_path
        os.makedirs(self.storage_path, exist_ok=True)

    def publish(self, evidence: Dict[str, Any]) -> str:
        """
        Publishes evidence and returns the bucket path/URI.
        Error boundary ensures disk failures don't crash the execution pipeline.
        """
        trace_id = evidence.get("trace_id", "unknown_trace")
        file_path = os.path.join(self.storage_path, f"{trace_id}.json")

        try:
            with open(file_path, "w") as f:
                json.dump(evidence, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to write evidence to {file_path}: {type(e).__name__}: {e}")
            return f"bucket://tantra-evidence-store/solver-fabric/ERROR_{trace_id}"

        # Track metrics
        duration_ms = evidence.get("provenance", {}).get("execution_duration_ms", 0)
        success = evidence.get("status") != "FAILED"
        get_usf_metrics().record_execution(duration_ms, success)

        # Log structured telemetry for observability
        logger.info(
            f"Evidence published for execution trace: {trace_id}",
            extra={"telemetry": {
                "trace_id": trace_id,
                "replay_id": evidence.get("replay_id"),
                "status": evidence.get("status"),
                "duration_ms": duration_ms,
                "evidence_hash": evidence.get("evidence_hash", ""),
            }}
        )

        return f"bucket://tantra-evidence-store/solver-fabric/{trace_id}.json"
