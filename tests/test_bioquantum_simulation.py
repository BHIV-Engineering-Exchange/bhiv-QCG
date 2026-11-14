"""
tests/test_bioquantum_simulation.py
===================================
Automated Unit and Acceptance Tests for Workstream B (Biological Networks & BioQuantum)
and Candidate Test Task under BHQ-INFRA-001.

Verifies:
1. Repeatable parameter loading from SIMULATION/config.json.
2. Classical Minimum Spanning Tree baseline calculation and properties (N-1 edges).
3. Adaptive mycelium transport network convergence and metric computation.
4. Fault tolerance advantage of nature-inspired loops over tree topology.
5. FitzHugh-Nagumo bio-electrical action potential triggering and Rule 3 adherence.
"""

import json
from pathlib import Path
import pytest
from SIMULATION.mycelium_network_model import MyceliumNetworkSimulator


@pytest.fixture
def simulator():
    config_path = Path(__file__).parent.parent / "SIMULATION" / "config.json"
    return MyceliumNetworkSimulator(str(config_path))


class TestMyceliumSimulationSuite:
    """Verifies Workstream B / Candidate Test Task requirements."""

    def test_spatial_node_generation(self, simulator):
        assert len(simulator.nodes) == simulator.node_count
        assert len(simulator.nodes) == 12
        for node in simulator.nodes:
            assert 0.0 <= node.x <= 100.0
            assert 0.0 <= node.y <= 100.0

    def test_classical_mst_baseline(self, simulator):
        mst = simulator.compute_classical_mst_baseline()
        assert mst["baseline_type"] == "CLASSICAL_MINIMUM_SPANNING_TREE (Kruskal)"
        assert mst["edge_count"] == simulator.node_count - 1
        assert mst["redundancy_cycles"] == 0
        assert mst["total_network_length_mm"] > 0.0
        assert mst["average_shortest_path_mm"] > 0.0

    def test_mycelium_transport_adaptation(self, simulator):
        result = simulator.run_transport_adaptation()
        assert result["initial_edges"] > result["surviving_edges"]
        assert result["total_network_length_mm"] > 0.0
        assert result["average_shortest_path_mm"] > 0.0
        assert len(result["surviving_edge_keys"]) == result["surviving_edges"]

    def test_comparative_fault_tolerance(self, simulator):
        full_res = simulator.run_full_simulation()
        mst_resilience = full_res["comparative_benchmark"]["classical_mst"][2]
        mycelium_resilience = full_res["comparative_benchmark"]["mycelial_adaptive_network"][2]

        # Mycelium network with loops must be strictly more resilient to cuts than single MST tree
        assert mycelium_resilience > mst_resilience
        assert full_res["comparative_benchmark"]["engineering_tradeoff"]["fault_tolerance_gain_pct"] > 0.0

    def test_bioelectrical_action_potential_signaling(self, simulator):
        signaling = simulator.simulate_bioelectrical_action_potential()
        assert signaling["action_potential_triggered"] is True
        assert signaling["simulated_peak_potential_mv"] > 0.0
        assert signaling["quantum_state_present"] is False
        assert signaling["scientific_classification"] == "CLASSICAL_BIOELECTRICAL_ION_EXCHANGE"
        assert "Rule_3" in signaling["rule_3_affirmation"] or "ionic" in signaling["rule_3_affirmation"]

    def test_full_simulation_schema_and_rules(self, simulator):
        res = simulator.run_full_simulation()
        assert res["task_id"] == "BHQ-INFRA-001"
        assert res["simulation_status"] == "SIMULATED AND TESTED"
        assert res["candidate_test_task_evaluation"].startswith("PASSED")
        audit = res["scientific_and_engineering_rules_audit"]
        assert "Rule_1_Simulation_Not_Validation" in audit
        assert "Rule_3_Biological_Signaling_Not_Computation" in audit
