"""
tests/test_config_security.py — Phase 2: Config & Security Tests

Tests for new Phase 2 security configurations, middleware behavior,
and metrics collector functionality.
"""

import pytest
import threading
import time

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from metrics import MetricsCollector, LatencyRecorder


# ═══════════════════════════════════════════════════════════════════════════
# Config Validation
# ═══════════════════════════════════════════════════════════════════════════

class TestConfigValidation:

    def test_config_validates_with_defaults(self):
        import config
        config.validate()  # should not raise

    def test_security_config_keys_exist(self):
        import config
        assert hasattr(config, "MAX_REQUEST_BODY_SIZE")
        assert hasattr(config, "RATE_LIMIT_ENABLED")
        assert hasattr(config, "INPUT_TRACE_ID_MAX_LENGTH")
        assert hasattr(config, "INPUT_PAYLOAD_MAX_KEYS")

    def test_security_config_defaults_are_sane(self):
        import config
        assert config.MAX_REQUEST_BODY_SIZE == 1048576  # 1 MB
        assert config.INPUT_TRACE_ID_MAX_LENGTH == 256
        assert config.INPUT_PAYLOAD_MAX_KEYS == 100


# ═══════════════════════════════════════════════════════════════════════════
# Latency Recorder
# ═══════════════════════════════════════════════════════════════════════════

class TestLatencyRecorder:

    def test_record_and_percentile(self):
        lr = LatencyRecorder()
        for v in [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]:
            lr.record(v)
        # P50 should be near the median
        p50 = lr.percentile(50)
        assert 40 <= p50 <= 60

    def test_empty_percentile_returns_zero(self):
        lr = LatencyRecorder()
        assert lr.percentile(50) == 0.0
        assert lr.percentile(99) == 0.0

    def test_count(self):
        lr = LatencyRecorder()
        lr.record(1.0)
        lr.record(2.0)
        assert lr.count == 2

    def test_reset(self):
        lr = LatencyRecorder()
        lr.record(1.0)
        lr.reset()
        assert lr.count == 0

    def test_bounded_memory(self):
        """Should not exceed max_samples."""
        lr = LatencyRecorder()
        lr._max_samples = 100
        for i in range(200):
            lr.record(float(i))
        assert lr.count <= 100 + 10  # some slack from eviction batch


# ═══════════════════════════════════════════════════════════════════════════
# Metrics Collector
# ═══════════════════════════════════════════════════════════════════════════

class TestMetricsCollector:

    def test_record_request(self):
        mc = MetricsCollector()
        mc.record_request("/health", "GET")
        mc.record_request("/verify", "POST")
        assert mc.total_requests == 2

    def test_record_error(self):
        mc = MetricsCollector()
        mc.record_error("500")
        mc.record_error("422")
        assert mc.total_errors == 2

    def test_record_halt(self):
        mc = MetricsCollector()
        mc.record_halt("REPLAY_DUPLICATE")
        mc.record_halt("TRUST_REJECTED")
        summary = mc.get_summary()
        assert summary["halts"]["total"] == 2

    def test_record_latency(self):
        mc = MetricsCollector()
        mc.record_latency("/health", 5.0)
        mc.record_latency("/health", 10.0)
        summary = mc.get_summary()
        assert summary["latency_ms"]["sample_count"] == 2

    def test_component_health(self):
        mc = MetricsCollector()
        mc.set_component_health("ledger", "UP")
        mc.set_component_health("consensus", "DEGRADED")
        summary = mc.get_summary()
        assert summary["component_health"]["ledger"] == "UP"
        assert summary["component_health"]["consensus"] == "DEGRADED"

    def test_uptime(self):
        mc = MetricsCollector()
        time.sleep(0.05)
        assert mc.uptime_seconds >= 0.04

    def test_get_summary_structure(self):
        mc = MetricsCollector()
        mc.record_request("/test", "GET")
        summary = mc.get_summary()
        assert "uptime_seconds" in summary
        assert "requests" in summary
        assert "errors" in summary
        assert "halts" in summary
        assert "latency_ms" in summary
        assert "component_health" in summary

    def test_prometheus_export(self):
        mc = MetricsCollector()
        mc.record_request("/health", "GET")
        mc.record_error("500")
        mc.record_latency("/health", 5.0)
        mc.set_component_health("ledger", "UP")
        output = mc.to_prometheus()
        assert "qcg_uptime_seconds" in output
        assert "qcg_requests_total" in output
        assert "qcg_errors_total" in output
        assert "qcg_component_health" in output
        assert "qcg_request_duration_ms" in output

    def test_reset(self):
        mc = MetricsCollector()
        mc.record_request("/test", "GET")
        mc.record_error("500")
        mc.reset()
        assert mc.total_requests == 0
        assert mc.total_errors == 0

    def test_thread_safety(self):
        """Concurrent writes should not crash or lose data."""
        mc = MetricsCollector()
        errors = []

        def worker(n):
            try:
                for i in range(100):
                    mc.record_request(f"/endpoint-{n}", "GET")
                    mc.record_latency(f"/endpoint-{n}", float(i))
                    mc.record_error("test_error")
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        assert mc.total_requests == 500
        assert mc.total_errors == 500


# ═══════════════════════════════════════════════════════════════════════════
# Global Metrics Singleton
# ═══════════════════════════════════════════════════════════════════════════

class TestGlobalMetrics:

    def test_singleton_returns_same_instance(self):
        from metrics import get_metrics
        m1 = get_metrics()
        m2 = get_metrics()
        assert m1 is m2
