"""
tests/test_quantum_network_contract.py — Phase 2: Quantum Network Contract Tests

Validates the data models and boundaries for quantum node coordination.
"""

import pytest
import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from quantum_network_contract import (
    QuantumNetworkNode, 
    NetworkNodeStatus,
    RouteRequest,
    NetworkProtocol
)


class TestQuantumNetworkNode:

    def test_node_creation(self):
        node = QuantumNetworkNode(
            node_id="q-node-001",
            node_name="Primary Quantum Router",
            capabilities=["QKD", "TELEPORTATION"],
            supported_protocols=[NetworkProtocol.BB84.value],
            classical_control_endpoint="https://qnode1.example.com/api"
        )
        assert node.node_id == "q-node-001"
        assert node.network_status == NetworkNodeStatus.UNKNOWN.value
        assert "QKD" in node.capabilities

    def test_node_to_dict_serialization(self):
        node = QuantumNetworkNode(node_id="test", node_name="Test Node")
        data = node.to_dict()
        assert data["node_id"] == "test"
        assert "registered_at" in data

    def test_node_from_dict_deserialization(self):
        data = {
            "node_id": "test-2",
            "node_name": "Test Node 2",
            "network_status": "ACTIVE"
        }
        node = QuantumNetworkNode(**data)
        assert node.node_id == "test-2"
        assert node.network_status == "ACTIVE"


class TestRouteRequest:

    def test_route_request_creation(self):
        req = RouteRequest(
            request_id="req-123",
            source_node_id="node-a",
            destination_node_id="node-b",
            preferred_protocol=NetworkProtocol.E91.value,
            min_fidelity=0.99
        )
        assert req.request_id == "req-123"
        assert req.source_node_id == "node-a"
        assert req.destination_node_id == "node-b"
        assert req.min_fidelity == 0.99

    def test_route_request_serialization(self):
        req = RouteRequest(
            request_id="req-124",
            source_node_id="node-a",
            destination_node_id="node-b",
            preferred_protocol=NetworkProtocol.ENTANGLEMENT_SWAPPING.value
        )
        data = req.to_dict()
        assert data["preferred_protocol"] == NetworkProtocol.ENTANGLEMENT_SWAPPING.value

    def test_route_request_from_dict(self):
        data = {
            "request_id": "req-123",
            "source_node_id": "src",
            "destination_node_id": "dst",
            "preferred_protocol": "BB84",
            "min_fidelity": 0.95
        }
        req = RouteRequest(**data)
        assert req.request_id == "req-123"
        assert req.min_fidelity == 0.95
