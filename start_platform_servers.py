"""
start_platform_servers.py — Script to keep platform servers running for manual testing.

Updated to launch a 3-node federated discovery fabric with heartbeat management,
mutual authentication, and version negotiation.
"""

import time
import threading
import sys
import os
import json

from capability_registry import CapabilityRegistryClient
from platform_service_registry import PlatformServiceRegistry, PlatformServiceRecord, CapabilityManifest, RegistrationEvidenceRecorder, OperationContract
from platform_lifecycle_manager import LifecycleManager
from platform_service_discovery import PlatformDiscoveryServer
from federated_registry import FederatedRegistryNode
import config

def _load_manifest_json():
    manifest_path = os.path.join(os.path.dirname(__file__), "platform_capability_manifest.json")
    with open(manifest_path) as f:
        return json.load(f)

def _build_manifest_from_data(service_data):
    """Build a CapabilityManifest from manifest JSON data."""
    m = service_data["manifest"]
    ops = [OperationContract(
        operation_name=op["operation_name"],
        description=op["description"],
        input_contract=op["input_contract"],
        output_contract=op["output_contract"],
        execution_modes=op["execution_modes"],
        idempotent=op.get("idempotent", False),
    ) for op in m["supported_operations"]]
    return CapabilityManifest(
        manifest_id=m["manifest_id"],
        service_name=service_data["service_name"],
        version=service_data["version"],
        supported_operations=ops,
        execution_modes=m["execution_modes"],
        determinism_guarantees=m["determinism_guarantees"],
        replay_guarantees=m["replay_guarantees"],
        trust_requirements=m["trust_requirements"],
        evidence_guarantees=m["evidence_guarantees"],
        runtime_dependencies=m["runtime_dependencies"],
        version_compatibility=m["version_compatibility"],
        security_requirements=m["security_requirements"],
        resource_requirements=m["resource_requirements"],
    )

def main():
    num_nodes = int(os.environ.get("FEDERATION_NODES", "3"))
    base_port = config.DISCOVERY_PORT_BASE

    # --- Legacy Capability Registry ---
    print("Legacy Capability Registry (Port 9000) should be started separately via uvicorn.")

    # --- Federated Discovery Nodes ---
    print(f"\nStarting {num_nodes} Federated Discovery Nodes...")
    nodes = []
    servers = []
    for i in range(num_nodes):
        node_id = f"FEDERATION-NODE-{i+1}"
        port = base_port + i
        registry = PlatformServiceRegistry(evidence_recorder=RegistrationEvidenceRecorder())
        node = FederatedRegistryNode(node_id=node_id, registry=registry, port=port)
        nodes.append(node)

    # Wire peers
    for i, node in enumerate(nodes):
        for j, peer in enumerate(nodes):
            if i != j:
                node.add_peer(peer)

    # Start HTTP servers
    for i, node in enumerate(nodes):
        port = base_port + i
        server = PlatformDiscoveryServer(
            host="127.0.0.1",
            port=port,
            registry=node.registry,
            lifecycle=LifecycleManager(),
            federation_node=node,
        )
        server.start()
        servers.append(server)
        time.sleep(0.3)

    # --- Register services on Node 1 ---
    print("\nRegistering capabilities on Node 1...")
    manifest_data = _load_manifest_json()
    node1 = nodes[0]

    for svc_data in manifest_data.get("services", []):
        record = PlatformServiceRecord(
            platform_service_id=svc_data["platform_service_id"],
            capability_id=svc_data["capability_id"],
            service_name=svc_data["service_name"],
            version=svc_data["version"],
            provider=svc_data["provider"],
            owner=svc_data["owner"],
            runtime_type=svc_data["runtime_type"],
            service_classification=svc_data["service_classification"],
            capability_category=svc_data["capability_category"],
            status=svc_data["status"],
            endpoints=svc_data.get("endpoints", {}),
        )
        manifest = _build_manifest_from_data(svc_data)
        node1.register_service_authenticated(record, manifest)

        compat = svc_data.get("manifest", {}).get("version_compatibility", {})
        for node in nodes:
            node.registry.negotiator.register_compatibility(
                svc_data["platform_service_id"],
                compatible=compat.get("compatible", [svc_data["version"]]),
                deprecated=compat.get("deprecated", []),
                unsupported=compat.get("unsupported", []),
            )
        print(f"  Registered: {svc_data['platform_service_id']}")

    # Federation sync
    print("\nFederation sync...")
    for node in nodes:
        node.anti_entropy_sync()
    time.sleep(0.5)

    for node in nodes:
        count = len(node.registry.list_services())
        print(f"  {node.node_id}: {count} services")

    # Print endpoints
    print("\n" + "=" * 60)
    print("  FEDERATED DISCOVERY FABRIC RUNNING")
    print("=" * 60)
    for i in range(num_nodes):
        port = base_port + i
        print(f"\n  Node {i+1} (port {port}):")
        print(f"    Services:    http://127.0.0.1:{port}/platform/v1/services")
        print(f"    Health:      http://127.0.0.1:{port}/platform/v1/health")
        print(f"    Federation:  http://127.0.0.1:{port}/platform/v1/federation/status")
        print(f"    Audit:       http://127.0.0.1:{port}/platform/v1/federation/audit")
        print(f"    Certs:       http://127.0.0.1:{port}/platform/v1/certificates")
        print(f"    Evidence:    http://127.0.0.1:{port}/platform/v1/evidence")
    print(f"\n  Legacy Registry: http://127.0.0.1:9000/capabilities")
    print("=" * 60)
    print("Press Ctrl+C to exit.\n")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping servers...")
        for server in servers:
            server.stop()
        cap_server.stop()
        print("Done.")

if __name__ == "__main__":
    main()

