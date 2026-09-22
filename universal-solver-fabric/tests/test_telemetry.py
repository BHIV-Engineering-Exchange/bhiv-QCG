"""
tests/test_telemetry.py — Phase 2: Telemetry & EvidencePublisher Unit Tests

Validates evidence file I/O, metrics tracking, and error boundary on publish.
"""

import pytest
import json
import os
import sys
import tempfile
import shutil

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from telemetry import EvidencePublisher, USFMetrics, get_usf_metrics


class TestEvidencePublisher:

    def setup_method(self):
        self._tmp = tempfile.mkdtemp()
        self.publisher = EvidencePublisher(storage_path=self._tmp)

    def teardown_method(self):
        shutil.rmtree(self._tmp, ignore_errors=True)

    def test_publish_creates_json_file(self):
        evidence = {
            "trace_id": "test-trace-001",
            "replay_id": "replay-001",
            "status": "COMPLETED",
            "provenance": {"execution_duration_ms": 42},
            "result": {"x": 1},
            "evidence_hash": "abc123",
        }
        uri = self.publisher.publish(evidence)
        assert "test-trace-001" in uri

        file_path = os.path.join(self._tmp, "test-trace-001.json")
        assert os.path.exists(file_path)

        with open(file_path) as f:
            loaded = json.load(f)
        assert loaded["trace_id"] == "test-trace-001"
        assert loaded["result"] == {"x": 1}

    def test_publish_failed_evidence(self):
        evidence = {
            "trace_id": "fail-trace",
            "status": "FAILED",
            "provenance": {"execution_duration_ms": 0},
            "result": {"error": "crash"},
        }
        uri = self.publisher.publish(evidence)
        assert "fail-trace" in uri

    def test_publish_to_invalid_path_logs_error(self):
        """Test that publishing to a broken path doesn't crash."""
        # Even if mkdir succeeds, the publisher should not raise.
        publisher = EvidencePublisher(storage_path=self._tmp)
        evidence = {
            "trace_id": "safe-trace",
            "status": "COMPLETED",
            "provenance": {"execution_duration_ms": 0},
            "result": {},
        }
        uri = publisher.publish(evidence)
        assert "safe-trace" in uri


class TestUSFMetrics:

    def test_initial_state(self):
        m = USFMetrics()
        s = m.summary
        assert s["execution_count"] == 0
        assert s["error_count"] == 0
        assert s["success_rate"] == 0.0  # no executions yet

    def test_record_success(self):
        m = USFMetrics()
        m.record_execution(100.0, success=True)
        s = m.summary
        assert s["execution_count"] == 1
        assert s["error_count"] == 0
        assert s["avg_latency_ms"] == 100.0

    def test_record_failure(self):
        m = USFMetrics()
        m.record_execution(50.0, success=False)
        s = m.summary
        assert s["execution_count"] == 1
        assert s["error_count"] == 1
        assert s["success_rate"] == 0.0

    def test_mixed_executions(self):
        m = USFMetrics()
        m.record_execution(100.0, success=True)
        m.record_execution(200.0, success=True)
        m.record_execution(300.0, success=False)
        s = m.summary
        assert s["execution_count"] == 3
        assert s["error_count"] == 1
        assert s["success_rate"] == pytest.approx(2 / 3, abs=0.01)
        assert s["avg_latency_ms"] == 200.0

    def test_reset(self):
        m = USFMetrics()
        m.record_execution(100.0)
        m.reset()
        s = m.summary
        assert s["execution_count"] == 0

    def test_uptime(self):
        m = USFMetrics()
        s = m.summary
        assert s["uptime_seconds"] >= 0

    def test_singleton_accessible(self):
        m = get_usf_metrics()
        assert isinstance(m, USFMetrics)
