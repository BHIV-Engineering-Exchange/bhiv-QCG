"""
test_distributed_runtime.py - Integration and unit tests for QCG Distributed Runtime.
"""

import os
import time
import unittest
import tempfile
from pathlib import Path

import config
from transport import (
    create_transport_sender,
    create_transport_receiver,
    TCPTransportSender,
    HTTPTransportSender,
    UDSTransportSender
)
from observability import TraceStore, TraceEntry

class TestDistributedTransport(unittest.TestCase):
    def test_tcp_transport_loopback(self):
        port = 12345
        receiver = create_transport_receiver("tcp", ("127.0.0.1", port))
        sender = create_transport_sender("tcp", ("127.0.0.1", port))

        sender.connect()
        test_payload = {"hello": "world", "type": "TEST"}
        sender.put(test_payload)
        
        received = receiver.get(timeout=2.0)
        self.assertEqual(received["hello"], "world")
        
        sender.close()
        receiver.close()

    def test_http_transport_loopback(self):
        port = 12346
        receiver = create_transport_receiver("http", ("127.0.0.1", port))
        sender = create_transport_sender("http", ("127.0.0.1", port))

        test_payload = {"greeting": "hello http", "type": "TEST"}
        sender.put(test_payload)
        
        received = receiver.get(timeout=3.0)
        self.assertEqual(received["greeting"], "hello http")
        
        receiver.close()

    def test_uds_transport_fallback_or_native(self):
        uds_path = "./logs/test_uds.sock"
        receiver = create_transport_receiver("uds", uds_path)
        sender = create_transport_sender("uds", uds_path)

        sender.connect()
        test_payload = {"uds_msg": "testing UDS", "type": "TEST"}
        sender.put(test_payload)
        
        received = receiver.get(timeout=2.0)
        self.assertEqual(received["uds_msg"], "testing UDS")
        
        sender.close()
        receiver.close()

class TestOpenTelemetryObservability(unittest.TestCase):
    def test_otel_span_export(self):
        store = TraceStore()
        trace_id = "test-otel-trace-123"
        store.record_execution_trace(
            trace_id=trace_id,
            contract_hash="abc",
            ack="ACK:OK",
            runtime_hash="xyz",
            confidence=0.95
        )
        
        spans = store.export_opentelemetry(trace_id)
        self.assertEqual(len(spans), 1)
        span = spans[0]
        self.assertEqual(span["name"], "qcg:execution")
        self.assertEqual(span["attributes"]["qcg.data.ack"], "ACK:OK")
        self.assertEqual(span["status"]["code"], "STATUS_CODE_OK")
        self.assertTrue("traceId" in span)
        self.assertTrue("spanId" in span)

if __name__ == "__main__":
    unittest.main()
