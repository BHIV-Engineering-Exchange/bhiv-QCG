"""
metrics.py — Phase 2: Production Metrics Collector

Thread-safe in-process metrics collector for the QCG runtime.
Tracks request counts, error rates, latency percentiles, and component health.
Exports in Prometheus text format.

RESPONSIBILITY BOUNDARY
-----------------------
MetricsCollector OWNS:
    - Request/error/halt counters
    - Latency recording and percentile calculation
    - Component health aggregation
    - Prometheus text export

MetricsCollector does NOT OWN:
    - OpenTelemetry trace export     → observability.py
    - Structured logging             → logger.py
    - Health check responses         → integration_interfaces.py
"""

from __future__ import annotations

import bisect
import threading
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class LatencyRecorder:
    """Records latencies and computes percentiles on demand."""
    _values: List[float] = field(default_factory=list)
    _lock: threading.Lock = field(default_factory=threading.Lock)
    _max_samples: int = 10_000

    def record(self, duration_ms: float) -> None:
        with self._lock:
            if len(self._values) >= self._max_samples:
                # Evict oldest 10%
                self._values = self._values[self._max_samples // 10:]
            bisect.insort(self._values, duration_ms)

    def percentile(self, p: float) -> float:
        """Return the p-th percentile (0-100). Returns 0.0 if no data."""
        with self._lock:
            if not self._values:
                return 0.0
            idx = int(len(self._values) * p / 100.0)
            idx = min(idx, len(self._values) - 1)
            return self._values[idx]

    @property
    def count(self) -> int:
        with self._lock:
            return len(self._values)

    def reset(self) -> None:
        with self._lock:
            self._values.clear()


class MetricsCollector:
    """
    Thread-safe production metrics collector.

    Tracks:
    - Total requests by endpoint
    - Error counts by type (4xx, 5xx, HALT)
    - Latency percentiles (P50, P95, P99)
    - Component health signals
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._request_counts: Dict[str, int] = defaultdict(int)
        self._error_counts: Dict[str, int] = defaultdict(int)
        self._halt_counts: Dict[str, int] = defaultdict(int)
        self._latency = LatencyRecorder()
        self._endpoint_latencies: Dict[str, LatencyRecorder] = {}
        self._component_health: Dict[str, str] = {}
        self._start_time = time.time()

    # -- Recording -----------------------------------------------------------

    def record_request(self, endpoint: str, method: str = "GET") -> None:
        """Increment request counter for an endpoint."""
        with self._lock:
            self._request_counts[f"{method} {endpoint}"] += 1

    def record_error(self, error_type: str) -> None:
        """Increment error counter by type (e.g., '422', '500', 'HALT')."""
        with self._lock:
            self._error_counts[error_type] += 1

    def record_halt(self, halt_reason: str) -> None:
        """Increment halt counter by reason."""
        with self._lock:
            self._halt_counts[halt_reason] += 1

    def record_latency(self, endpoint: str, duration_ms: float) -> None:
        """Record request latency for an endpoint."""
        self._latency.record(duration_ms)
        with self._lock:
            if endpoint not in self._endpoint_latencies:
                self._endpoint_latencies[endpoint] = LatencyRecorder()
        self._endpoint_latencies[endpoint].record(duration_ms)

    def set_component_health(self, component: str, status: str) -> None:
        """Set health status for a component (UP, DOWN, DEGRADED)."""
        with self._lock:
            self._component_health[component] = status

    # -- Querying ------------------------------------------------------------

    @property
    def total_requests(self) -> int:
        with self._lock:
            return sum(self._request_counts.values())

    @property
    def total_errors(self) -> int:
        with self._lock:
            return sum(self._error_counts.values())

    @property
    def uptime_seconds(self) -> float:
        return time.time() - self._start_time

    def get_summary(self) -> Dict:
        """Return a structured summary of all metrics."""
        with self._lock:
            request_counts = dict(self._request_counts)
            error_counts = dict(self._error_counts)
            halt_counts = dict(self._halt_counts)
            component_health = dict(self._component_health)

        return {
            "uptime_seconds": round(self.uptime_seconds, 2),
            "requests": {
                "total": self.total_requests,
                "by_endpoint": request_counts,
            },
            "errors": {
                "total": self.total_errors,
                "by_type": error_counts,
            },
            "halts": {
                "total": sum(halt_counts.values()),
                "by_reason": halt_counts,
            },
            "latency_ms": {
                "p50": round(self._latency.percentile(50), 2),
                "p95": round(self._latency.percentile(95), 2),
                "p99": round(self._latency.percentile(99), 2),
                "sample_count": self._latency.count,
            },
            "component_health": component_health,
        }

    # -- Prometheus Export ----------------------------------------------------

    def to_prometheus(self) -> str:
        """Export metrics in Prometheus text exposition format."""
        lines: List[str] = []

        # Uptime
        lines.append("# HELP qcg_uptime_seconds Time since server start.")
        lines.append("# TYPE qcg_uptime_seconds gauge")
        lines.append(f"qcg_uptime_seconds {self.uptime_seconds:.2f}")
        lines.append("")

        # Request counts
        lines.append("# HELP qcg_requests_total Total HTTP requests.")
        lines.append("# TYPE qcg_requests_total counter")
        with self._lock:
            for endpoint, count in self._request_counts.items():
                safe_ep = endpoint.replace('"', '\\"')
                lines.append(f'qcg_requests_total{{endpoint="{safe_ep}"}} {count}')
        lines.append("")

        # Error counts
        lines.append("# HELP qcg_errors_total Total errors by type.")
        lines.append("# TYPE qcg_errors_total counter")
        with self._lock:
            for etype, count in self._error_counts.items():
                lines.append(f'qcg_errors_total{{type="{etype}"}} {count}')
        lines.append("")

        # Halt counts
        lines.append("# HELP qcg_halts_total Total halts by reason.")
        lines.append("# TYPE qcg_halts_total counter")
        with self._lock:
            for reason, count in self._halt_counts.items():
                safe_r = reason.replace('"', '\\"')
                lines.append(f'qcg_halts_total{{reason="{safe_r}"}} {count}')
        lines.append("")

        # Latency
        lines.append("# HELP qcg_request_duration_ms Request latency in milliseconds.")
        lines.append("# TYPE qcg_request_duration_ms summary")
        lines.append(f'qcg_request_duration_ms{{quantile="0.5"}} {self._latency.percentile(50):.2f}')
        lines.append(f'qcg_request_duration_ms{{quantile="0.95"}} {self._latency.percentile(95):.2f}')
        lines.append(f'qcg_request_duration_ms{{quantile="0.99"}} {self._latency.percentile(99):.2f}')
        lines.append(f"qcg_request_duration_ms_count {self._latency.count}")
        lines.append("")

        # Component health
        lines.append("# HELP qcg_component_health Component health status (1=UP, 0=DOWN, 0.5=DEGRADED).")
        lines.append("# TYPE qcg_component_health gauge")
        health_map = {"UP": 1.0, "DOWN": 0.0, "DEGRADED": 0.5}
        with self._lock:
            for comp, status in self._component_health.items():
                val = health_map.get(status, 0.0)
                lines.append(f'qcg_component_health{{component="{comp}"}} {val}')
        lines.append("")

        return "\n".join(lines)

    def reset(self) -> None:
        """Reset all metrics (primarily for testing)."""
        with self._lock:
            self._request_counts.clear()
            self._error_counts.clear()
            self._halt_counts.clear()
            self._component_health.clear()
        self._latency.reset()
        for lr in self._endpoint_latencies.values():
            lr.reset()
        self._start_time = time.time()


# Module-level singleton for global access
_global_metrics: Optional[MetricsCollector] = None
_metrics_lock = threading.Lock()


def get_metrics() -> MetricsCollector:
    """Return the global MetricsCollector singleton."""
    global _global_metrics
    if _global_metrics is None:
        with _metrics_lock:
            if _global_metrics is None:
                _global_metrics = MetricsCollector()
    return _global_metrics
