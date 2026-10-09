"""
tests/test_quantum_network_distribution.py — Phase 4: Distributed Quantum Networking Tests

Validates:
1. EntanglementPair decoherence modeling and lifecycle (generation, decay, consumption, expiry)
2. EntanglementPoolManager multi-node pair pooling and purge
3. DistributedMeasurementAggregator multi-node measurement aggregation & entropy
4. Multi-node distributed quantum workload coordination across participating nodes
5. Network failure scenarios (node offline, route blocked, latency exceeded, entanglement exhaustion)
6. PlatformCapabilitySDK integration with tamper-evident SDKEvidenceChain
"""

import time
import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from quantum_network_contract import (
    QuantumNetworkContract,
    QuantumNetworkNode,
    NetworkNodeStatus,
    NetworkProtocol,
    EntanglementPair,
    EntanglementPoolManager,
    DistributedQuantumWorkload,
    DistributedMeasurementAggregator,
)
from platform_capability_sdk import PlatformCapabilitySDK


class TestEntanglementLifecycle:

    def test_entanglement_pair_initialization(self):
        pair = EntanglementPair(
            pair_id="epr-test-1",
            node_a="node-alpha",
            node_b="node-beta",
            initial_fidelity=0.98,
            coherence_time_ms=100.0,
        )
        assert pair.pair_id == "epr-test-1"
        assert pair.initial_fidelity == 0.98
        assert pair.get_current_fidelity() >= 0.95
        assert not pair.is_consumed
        assert not pair.is_expired(min_fidelity=0.70)

    def test_entanglement_pair_decoherence_decay(self):
        created_time = time.time() - 0.2  # 200 ms ago
        pair = EntanglementPair(
            pair_id="epr-decay-1",
            node_a="node-a",
            node_b="node-b",
            initial_fidelity=0.98,
            created_at_timestamp=created_time,
            coherence_time_ms=50.0,  # 4 half-lives passed
        )
        current_fid = pair.get_current_fidelity()
        assert current_fid < 0.70
        assert pair.is_expired(min_fidelity=0.70)

    def test_entanglement_pair_consumption(self):
        pair = EntanglementPair(
            pair_id="epr-consume-1",
            node_a="node-a",
            node_b="node-b",
        )
        assert not pair.is_consumed
        assert pair.consume() is True
        assert pair.is_consumed is True
        assert pair.consume() is False
        assert pair.get_current_fidelity() == 0.0
        assert pair.is_expired() is True


class TestEntanglementPoolManager:

    def test_pool_generation_and_reservation(self):
        pool = EntanglementPoolManager()
        pairs = pool.generate_pairs("node-1", "node-2", count=3, initial_fidelity=0.99)
        assert len(pairs) == 3

        status = pool.get_status()
        assert status["total_pairs_tracked"] == 3
        assert status["available_pairs"] == 3

        reserved = pool.reserve_pair("node-1", "node-2", min_fidelity=0.80)
        assert reserved is not None
        assert reserved.is_consumed is True

        status_after = pool.get_status()
        assert status_after["available_pairs"] == 2
        assert status_after["consumed_pairs"] == 1

    def test_pool_purge_expired_pairs(self):
        pool = EntanglementPoolManager()
        past = time.time() - 1.0
        pair_old = EntanglementPair(
            pair_id="old-epr",
            node_a="node-1",
            node_b="node-2",
            created_at_timestamp=past,
            coherence_time_ms=10.0,
        )
        pool._pairs[pair_old.pair_id] = pair_old

        purged_count = pool.purge_expired(min_fidelity=0.70)
        assert purged_count == 1
        assert "old-epr" not in pool._pairs


class TestDistributedMeasurementAggregator:

    def test_empty_measurements(self):
        result = DistributedMeasurementAggregator.aggregate({})
        assert result["total_shots"] == 0
        assert result["shannon_entropy"] == 0.0

    def test_two_node_joint_distribution(self):
        measurements = {
            "node_alpha": {"0": 500, "1": 500},
            "node_beta": {"0": 500, "1": 500},
        }
        res = DistributedMeasurementAggregator.aggregate(measurements)
        probs = res["joint_probabilities"]
        assert "00" in probs
        assert "01" in probs
        assert "10" in probs
        assert "11" in probs
        for p in probs.values():
            assert pytest.approx(p, abs=0.01) == 0.25
        assert res["shannon_entropy"] > 1.9
        assert res["total_shots"] == 1000


class TestDistributedWorkloadCoordination:

    def setup_method(self):
        self.net = QuantumNetworkContract()
        self.node1 = QuantumNetworkNode(
            node_id="qnode-router-1",
            node_name="Delhi Core Router",
            capabilities=["QKD", "ENTANGLEMENT"],
            supported_protocols=[
                NetworkProtocol.BB84.value,
                NetworkProtocol.E91.value,
                NetworkProtocol.ENTANGLEMENT_SWAPPING.value,
                NetworkProtocol.CLASSICAL_CONTROL.value,
            ],
            network_status=NetworkNodeStatus.ACTIVE.value,
            qubit_coherence_time_us=5000.0,
        )
        self.node2 = QuantumNetworkNode(
            node_id="qnode-router-2",
            node_name="Mumbai Hub Router",
            capabilities=["QKD", "ENTANGLEMENT"],
            supported_protocols=[
                NetworkProtocol.BB84.value,
                NetworkProtocol.E91.value,
                NetworkProtocol.ENTANGLEMENT_SWAPPING.value,
                NetworkProtocol.CLASSICAL_CONTROL.value,
            ],
            network_status=NetworkNodeStatus.ACTIVE.value,
            qubit_coherence_time_us=5000.0,
        )
        self.node3 = QuantumNetworkNode(
            node_id="qnode-router-3",
            node_name="Bengaluru Edge Router",
            capabilities=["QKD", "ENTANGLEMENT"],
            supported_protocols=[
                NetworkProtocol.BB84.value,
                NetworkProtocol.E91.value,
                NetworkProtocol.ENTANGLEMENT_SWAPPING.value,
                NetworkProtocol.CLASSICAL_CONTROL.value,
            ],
            network_status=NetworkNodeStatus.ACTIVE.value,
            qubit_coherence_time_us=5000.0,
        )
        self.net.declare_node(self.node1)
        self.net.declare_node(self.node2)
        self.net.declare_node(self.node3)

    def test_multi_node_coordination_success(self):
        self.net.allocate_entanglement("qnode-router-1", "qnode-router-2", count=2)
        self.net.allocate_entanglement("qnode-router-2", "qnode-router-3", count=2)

        workload = DistributedQuantumWorkload(
            workload_id="bharat-mala-qnet-001",
            participating_nodes=["qnode-router-1", "qnode-router-2", "qnode-router-3"],
            protocol=NetworkProtocol.ENTANGLEMENT_SWAPPING.value,
            min_fidelity=0.75,
            max_latency_ms=80.0,
        )

        res = self.net.coordinate_distributed_workload(workload)
        assert res["status"] == "COMPLETED"
        assert res["protocol"] == NetworkProtocol.ENTANGLEMENT_SWAPPING.value
        assert len(res["participating_nodes"]) == 3
        assert len(res["routes"]) == 2
        assert len(res["entanglement_pairs_used"]) == 2
        assert "aggregated_results" in res
        assert "coordination_hash" in res

    def test_multi_node_single_node_rejected(self):
        workload = DistributedQuantumWorkload(
            workload_id="single-node-err",
            participating_nodes=["qnode-router-1"],
        )
        res = self.net.coordinate_distributed_workload(workload)
        assert res["status"] == "BLOCKED"
        assert "requires at least 2" in res["reason"]

    def test_multi_node_offline_node_rejected(self):
        self.node2.network_status = NetworkNodeStatus.OFFLINE.value
        self.net.declare_node(self.node2)

        workload = DistributedQuantumWorkload(
            workload_id="offline-node-err",
            participating_nodes=["qnode-router-1", "qnode-router-2"],
        )
        res = self.net.coordinate_distributed_workload(workload)
        assert res["status"] == "BLOCKED"
        assert "OFFLINE" in res["reason"]

    def test_multi_node_entanglement_fallback(self):
        workload = DistributedQuantumWorkload(
            workload_id="fallback-workload-001",
            participating_nodes=["qnode-router-1", "qnode-router-2"],
            protocol=NetworkProtocol.ENTANGLEMENT_SWAPPING.value,
            classical_fallback_acceptable=True,
        )
        res = self.net.coordinate_distributed_workload(workload)
        assert res["status"] == "COMPLETED"
        assert len(res["entanglement_pairs_used"]) == 0

    def test_multi_node_latency_limit_exceeded_without_fallback(self):
        workload = DistributedQuantumWorkload(
            workload_id="latency-exceeded-001",
            participating_nodes=["qnode-router-1", "qnode-router-2"],
            max_latency_ms=1.0,
            classical_fallback_acceptable=False,
        )
        res = self.net.coordinate_distributed_workload(workload)
        assert res["status"] == "BLOCKED"
        assert "latency" in res["reason"].lower()


class TestPlatformCapabilitySDKNetworking:

    def setup_method(self):
        self.sdk = PlatformCapabilitySDK()
        self.net = QuantumNetworkContract()
        node_a = QuantumNetworkNode(
            node_id="node-a",
            node_name="Node Alpha",
            capabilities=["QKD"],
            supported_protocols=[NetworkProtocol.BB84.value, NetworkProtocol.CLASSICAL_CONTROL.value],
            network_status=NetworkNodeStatus.ACTIVE.value,
        )
        node_b = QuantumNetworkNode(
            node_id="node-b",
            node_name="Node Beta",
            capabilities=["QKD"],
            supported_protocols=[NetworkProtocol.BB84.value, NetworkProtocol.CLASSICAL_CONTROL.value],
            network_status=NetworkNodeStatus.ACTIVE.value,
        )
        self.net.declare_node(node_a)
        self.net.declare_node(node_b)
        self.sdk.set_network_contract(self.net)

    def test_sdk_request_quantum_network_route(self):
        resp = self.sdk.request_quantum_network_route(
            source_node_id="node-a",
            destination_node_id="node-b",
            preferred_protocol="BB84",
        )
        assert resp["status"] in ("LOCAL", "SIMULATED", "LIVE")
        assert "route" in resp

        evidence_records = self.sdk.evidence.get_all()
        assert len(evidence_records) > 0
        last = evidence_records[-1]
        assert last["service_id"] == "QUANTUM_NETWORK_COORDINATION"
        assert last["operation"] == "request_route"

    def test_sdk_coordinate_distributed_workload(self):
        res = self.sdk.coordinate_distributed_quantum_workload(
            workload_id="sdk-vana-forest-001",
            participating_nodes=["node-a", "node-b"],
            protocol=NetworkProtocol.CLASSICAL_CONTROL.value,
        )
        assert res["status"] == "COMPLETED"
        assert res["workload_id"] == "sdk-vana-forest-001"

        assert self.sdk.evidence.verify_chain() is True
        evidence_records = self.sdk.evidence.get_all()
        assert any(e["operation"] == "coordinate_distributed_workload" for e in evidence_records)

    def test_sdk_get_quantum_network_status(self):
        status = self.sdk.get_quantum_network_status()
        assert "control_plane" in status
        assert "nodes" in status
        assert "entanglement_pool" in status
        assert status["control_plane"]["status"] == "ACTIVE"
