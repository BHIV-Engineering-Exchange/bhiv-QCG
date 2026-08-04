"""
federated_discovery_packet.py — Standalone Code Packet

Demonstrates the full Secure Federated Capability Fabric flow:
  Service Registration → Federation Sync → SDK Invocation → Evidence Collection

Usage:
    python code_packets/federated_discovery_packet.py
"""

import sys
import os
import time
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from platform_service_registry import (
    PlatformServiceRegistry,
    PlatformServiceRecord,
    CapabilityManifest,
    OperationContract,
    RegistrationEvidenceRecorder,
)
from platform_lifecycle_manager import LifecycleManager
from platform_service_discovery import PlatformDiscoveryServer
from federated_registry import FederatedRegistryNode
from platform_capability_sdk import PlatformCapabilitySDK
from quantum_trust_provider import create_trust_provider

import config


def main():
    print("=" * 60)
    print("  FEDERATED DISCOVERY CODE PACKET")
    print("=" * 60)

    # 1. Create 2 federated nodes
    print("\n[1] Creating 2 federated registry nodes...")
    nodes = []
    servers = []
    for i in range(2):
        node_id = f"PACKET-NODE-{i+1}"
        port = config.DISCOVERY_PORT_BASE + 100 + i  # avoid port conflicts
        registry = PlatformServiceRegistry(evidence_recorder=RegistrationEvidenceRecorder())
        node = FederatedRegistryNode(node_id=node_id, registry=registry, port=port)
        nodes.append(node)

    nodes[0].add_peer(nodes[1])
    nodes[1].add_peer(nodes[0])

    for i, node in enumerate(nodes):
        port = config.DISCOVERY_PORT_BASE + 100 + i
        server = PlatformDiscoveryServer(
            host="127.0.0.1", port=port,
            registry=node.registry,
            lifecycle=LifecycleManager(),
            federation_node=node,
        )
        server.start()
        servers.append(server)
        time.sleep(0.2)
    print(f"  Nodes started on ports {config.DISCOVERY_PORT_BASE+100}, {config.DISCOVERY_PORT_BASE+101}")

    # 2. Register a service on Node 1
    print("\n[2] Registering service on Node 1...")
    record = PlatformServiceRecord(
        platform_service_id="PACKET-SVC-001",
        capability_id="packet-cap-001",
        service_name="PACKET_DEMO_SERVICE",
        version="1.0.0",
        provider="Code Packet Demo",
        owner={"team": "Demo"},
        runtime_type="PROCESS",
        service_classification="PLATFORM_SERVICE",
        capability_category="VERIFICATION",
        status="ACTIVE",
        endpoints={"execution": f"http://127.0.0.1:{config.DISCOVERY_PORT_BASE+100}/platform/v1/services/PACKET-SVC-001"},
    )
    manifest = CapabilityManifest(
        manifest_id="PACKET-MANIFEST-001",
        service_name="PACKET_DEMO_SERVICE",
        version="1.0.0",
        supported_operations=[
            OperationContract(
                operation_name="demo_op",
                description="Demo operation",
                input_contract={"type": "object", "required": []},
                output_contract={"type": "object"},
                execution_modes=["SYNCHRONOUS"],
                idempotent=True,
            ),
        ],
        execution_modes=["SYNCHRONOUS"],
        determinism_guarantees={"deterministic_execution": True},
        replay_guarantees={"replay_safe": True},
        trust_requirements={},
        evidence_guarantees={"evidence_per_execution": True},
        runtime_dependencies=[],
        version_compatibility={"compatible": ["1.0.0"]},
        security_requirements={},
        resource_requirements={},
    )
    result = nodes[0].register_service_authenticated(record, manifest)
    print(f"  Registration: {result.get('status')}")

    # Register version compatibility
    nodes[0].registry.negotiator.register_compatibility(
        "PACKET-SVC-001", compatible=["1.0.0"], deprecated=[], unsupported=[]
    )
    nodes[1].registry.negotiator.register_compatibility(
        "PACKET-SVC-001", compatible=["1.0.0"], deprecated=[], unsupported=[]
    )

    # 3. Federation sync
    print("\n[3] Federation sync...")
    nodes[1].sync_with_peer("PACKET-NODE-1")
    n1_count = len(nodes[0].registry.list_services())
    n2_count = len(nodes[1].registry.list_services())
    print(f"  Node 1: {n1_count} services, Node 2: {n2_count} services")

    # 4. SDK invocation
    print("\n[4] SDK invocation via federated discovery...")
    sdk = PlatformCapabilitySDK(
        discovery_urls=[
            f"http://127.0.0.1:{config.DISCOVERY_PORT_BASE+100}",
            f"http://127.0.0.1:{config.DISCOVERY_PORT_BASE+101}",
        ],
        trust_provider=create_trust_provider("CLASSICAL"),
        service_id="PACKET-CLIENT",
    )

    services = sdk.discover_services()
    print(f"  Discovered: {[s['platform_service_id'] for s in services]}")

    inv_result = sdk.invoke_capability("PACKET-SVC-001", "demo_op", {"key": "value"})
    print(f"  Invocation: status={inv_result.status}, duration={inv_result.duration_ms:.1f}ms")

    # 5. Evidence collection
    print("\n[5] Evidence collection...")
    evidence = sdk.evidence.get_all()
    chain_valid = sdk.evidence.verify_chain()
    print(f"  Evidence records: {len(evidence)}, chain valid: {chain_valid}")
    print(f"  Head hash: {sdk.evidence.head_hash[:32]}...")

    # Cleanup
    print("\n[6] Cleanup...")
    for s in servers:
        s.stop()
    print("  Done!")


if __name__ == "__main__":
    main()
