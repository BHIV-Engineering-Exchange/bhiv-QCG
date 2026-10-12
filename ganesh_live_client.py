"""
ganesh_live_client.py — Live Ganesh Quantum Application Layer Client & QCG Bridge

Provides a production-grade HTTP client and contract bridge for Ganesh's
BHIV Quantum Application Layer (deployed on Render).

API: https://bhiv-quantum-application-layer.onrender.com
Key Endpoints:
  GET  /health                                 — Service health check
  GET  /api/v1/capabilities                    — Supported models, backends, limits
  POST /api/v1/workloads                       — Register domain workload (VANA, MARINE, etc.)
  GET  /api/v1/workloads                       — List registered workloads
  GET  /api/v1/workloads/{workload_id}         — Get workload details
  POST /api/v1/workloads/{workload_id}/execute — Execute on aer_simulator or hardware
  GET  /api/v1/executions                      — List all executions
  GET  /api/v1/executions/{execution_id}       — Get execution result & measurements

QCG Platform Bridging:
  - Bridges quantum execution results into ComputationExecutionContract
  - Signs payload via NodeSigner (ECDSA P-256)
  - Tracks sequence & generates replay lineage via CanonicalReplayAuthority
  - Appends execution to EvidenceLedger to mint cryptographic Merkle inclusion snapshot
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import time
import urllib.request
import urllib.error
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import config
from execution_contract import ComputationExecutionContract, validate_contract
from execution_classification import ExecutionClassification
from execution_record import ExecutionRecord
from node_identity import NodeSigner, NodeProof
from canonical_replay_authority import CanonicalReplayAuthority, ReplayVerdict
from evidence_ledger import EvidenceLedger, LedgerSnapshot

logger = logging.getLogger("qcg.ganesh")


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

GANESH_API_URL: str = getattr(config, "GANESH_API_URL", "https://bhiv-quantum-application-layer.onrender.com")
GANESH_TIMEOUT: int = getattr(config, "GANESH_TIMEOUT", 60)


# ---------------------------------------------------------------------------
# Data Models
# ---------------------------------------------------------------------------

@dataclass
class GaneshHealthResponse:
    """Parsed response from /health endpoint."""
    status: str
    service: str
    version: str = "0.1.0"
    raw_response: dict = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict) -> "GaneshHealthResponse":
        return cls(
            status=data.get("status", "UNKNOWN"),
            service=data.get("service", "quantum-application-layer"),
            version=data.get("version", "0.1.0"),
            raw_response=data,
        )


@dataclass
class GaneshCapabilitiesResponse:
    """Parsed response from /api/v1/capabilities endpoint."""
    status: str
    service: str
    version: str
    domains: Any = field(default_factory=list)
    backends: Any = field(default_factory=list)
    raw_response: dict = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict) -> "GaneshCapabilitiesResponse":
        return cls(
            status=data.get("status", "UNKNOWN"),
            service=data.get("service", "quantum-application-layer"),
            version=data.get("version", "0.1.0"),
            domains=data.get("domains", data.get("supported_domains", [])),
            backends=data.get("backends", data.get("supported_backends", [])),
            raw_response=data,
        )


@dataclass
class GaneshWorkloadRequest:
    """Payload to register a new domain workload."""
    domain: str                     # VANA | MARINE | UCCIS | AIAIC
    problem_id: str
    algorithm: str                  # QAOA | VQE | QML_CLASSIFIER | Q_ROUTING
    qubits_required: int
    shots: int = 1024
    execution_mode: str = "SIMULATOR"
    formulation: Dict[str, Any] = field(default_factory=dict)
    parameters: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class GaneshWorkloadResponse:
    """Parsed response from workload registration."""
    workload_id: str
    domain: str
    problem_id: str
    algorithm: str
    qubits_required: int
    shots: int
    status: str
    created_at: str = ""
    raw_response: dict = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict) -> "GaneshWorkloadResponse":
        return cls(
            workload_id=data.get("workload_id", ""),
            domain=data.get("domain", ""),
            problem_id=data.get("problem_id", ""),
            algorithm=data.get("algorithm", ""),
            qubits_required=data.get("qubits_required", 0),
            shots=data.get("shots", 1024),
            status=data.get("status", "UNKNOWN"),
            created_at=data.get("created_at", ""),
            raw_response=data,
        )


@dataclass
class GaneshExecuteRequest:
    """Payload to execute an existing workload."""
    backend_target: str = "aer_simulator"
    shots: int = 1024
    evaluate_governance: bool = True

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class GaneshExecuteResponse:
    """Parsed response from workload execution."""
    execution_id: str
    workload_id: str
    backend_target: str
    shots: int
    status: str
    counts: Dict[str, int] = field(default_factory=dict)
    probabilities: Dict[str, float] = field(default_factory=dict)
    best_candidate: Optional[str] = None
    execution_time_ms: float = 0.0
    error_message: Optional[str] = None
    raw_response: dict = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict) -> "GaneshExecuteResponse":
        # Supports both direct response or nested result dictionary
        result_inner = data.get("result", {}) if isinstance(data.get("result"), dict) else data
        return cls(
            execution_id=data.get("execution_id", ""),
            workload_id=data.get("workload_id", ""),
            backend_target=data.get("backend_target", "aer_simulator"),
            shots=data.get("shots", 1024),
            status=data.get("status", "UNKNOWN"),
            counts=result_inner.get("counts", {}),
            probabilities=result_inner.get("probabilities", {}),
            best_candidate=result_inner.get("best_candidate"),
            execution_time_ms=data.get("execution_time_ms", 0.0),
            error_message=data.get("error_message") or data.get("error"),
            raw_response=data,
        )


@dataclass
class GaneshQCGBridgeResult:
    """Outcome of bridging Ganesh quantum execution into QCG canonical contract."""
    contract: ComputationExecutionContract
    node_proof: NodeProof
    replay_verdict: ReplayVerdict
    ledger_snapshot: LedgerSnapshot
    evidence_payload: Dict[str, Any]

    def to_dict(self) -> dict:
        return {
            "contract": self.contract.to_dict(),
            "node_proof": self.node_proof.to_dict(),
            "replay_verdict": self.replay_verdict.to_dict(),
            "ledger_snapshot": {
                "sequence_length": self.ledger_snapshot.sequence_length,
                "merkle_root": self.ledger_snapshot.merkle_root,
                "latest_evidence_hash": self.ledger_snapshot.latest_evidence_hash,
                "timestamp": self.ledger_snapshot.timestamp,
            },
            "evidence_payload": self.evidence_payload,
        }


# ---------------------------------------------------------------------------
# Integration Log — captures every request/response for audit & review packet
# ---------------------------------------------------------------------------

class IntegrationLog:
    """In-memory audit log of all HTTP calls to Ganesh's service."""

    def __init__(self):
        self._entries: list[dict] = []

    def record(
        self,
        method: str,
        endpoint: str,
        request_body: Any,
        status_code: int,
        response_body: Any,
        latency_ms: float,
        error: Optional[str] = None,
    ) -> dict:
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "method": method,
            "endpoint": endpoint,
            "status_code": status_code,
            "latency_ms": round(latency_ms, 2),
            "request_hash": hashlib.sha256(
                json.dumps(request_body, sort_keys=True, default=str).encode()
            ).hexdigest() if request_body is not None else None,
            "response_hash": hashlib.sha256(
                json.dumps(response_body, sort_keys=True, default=str).encode()
            ).hexdigest() if response_body is not None else None,
            "error": error,
        }
        self._entries.append(entry)
        return entry

    @property
    def entries(self) -> list[dict]:
        return list(self._entries)

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self._entries, indent=indent, default=str)


# ---------------------------------------------------------------------------
# GaneshClient
# ---------------------------------------------------------------------------

class GaneshClient:
    """
    Production-grade HTTP client and QCG bridge for the Ganesh Quantum Application Layer.
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        timeout: Optional[int] = None,
        signer: Optional[NodeSigner] = None,
        replay_authority: Optional[CanonicalReplayAuthority] = None,
        ledger: Optional[EvidenceLedger] = None,
    ):
        self.base_url = (base_url or GANESH_API_URL).rstrip("/")
        self.timeout = timeout or GANESH_TIMEOUT
        self.log = IntegrationLog()
        self._available: Optional[bool] = None

        # QCG Sovereign Core Components
        self.signer = signer or NodeSigner(
            node_id="NODE-GANESH-QAPP-BRIDGE",
            node_role="QUANTUM_FEDERATED_GATEWAY",
            version="1.0.0",
        )
        self.replay_authority = replay_authority or CanonicalReplayAuthority()
        self.ledger = ledger or EvidenceLedger()

    # -- Internal HTTP Helper -------------------------------------------------

    def _request(
        self,
        method: str,
        endpoint: str,
        body: Optional[dict] = None,
    ) -> Tuple[int, Any]:
        """Execute an HTTP request with error trapping and logging."""
        url = f"{self.base_url}{endpoint}"
        start = time.monotonic()

        try:
            if method == "POST" and body is not None:
                data = json.dumps(body).encode("utf-8")
                req = urllib.request.Request(
                    url,
                    data=data,
                    headers={"Content-Type": "application/json", "Accept": "application/json"},
                    method="POST",
                )
            else:
                req = urllib.request.Request(
                    url,
                    headers={"Accept": "application/json"},
                    method=method,
                )

            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                latency = (time.monotonic() - start) * 1000
                response_body = json.loads(resp.read().decode("utf-8"))
                self.log.record(method, endpoint, body, resp.status, response_body, latency)
                return resp.status, response_body

        except urllib.error.HTTPError as e:
            latency = (time.monotonic() - start) * 1000
            try:
                error_body = json.loads(e.read().decode("utf-8"))
            except Exception:
                error_body = {"raw_error": str(e)}
            self.log.record(method, endpoint, body, e.code, error_body, latency, error=str(e))
            return e.code, error_body

        except Exception as e:
            latency = (time.monotonic() - start) * 1000
            self.log.record(method, endpoint, body, 0, None, latency, error=str(e))
            return 0, {"error": str(e)}

    # -- Public Service Endpoints ---------------------------------------------

    def health(self) -> GaneshHealthResponse:
        """Query GET /health (fallback GET /api/v1/health)."""
        status, body = self._request("GET", "/health")
        if status != 200:
            status, body = self._request("GET", "/api/v1/health")

        if status == 200 and isinstance(body, dict):
            self._available = True
            return GaneshHealthResponse.from_dict(body)

        self._available = False
        return GaneshHealthResponse(
            status="UNREACHABLE",
            service="quantum-application-layer",
            raw_response=body if isinstance(body, dict) else {"error": str(body)},
        )

    def is_available(self) -> bool:
        """Check if Ganesh service is reachable."""
        if self._available is None:
            self.health()
        return self._available is True

    def get_capabilities(self) -> GaneshCapabilitiesResponse:
        """Query GET /api/v1/capabilities."""
        status, body = self._request("GET", "/api/v1/capabilities")
        if status == 200 and isinstance(body, dict):
            return GaneshCapabilitiesResponse.from_dict(body)
        return GaneshCapabilitiesResponse(
            status="ERROR",
            service="quantum-application-layer",
            version="0.1.0",
            raw_response=body if isinstance(body, dict) else {"error": str(body)},
        )

    def create_workload(self, request: GaneshWorkloadRequest) -> GaneshWorkloadResponse:
        """Register a new domain algorithm workload. POST /api/v1/workloads."""
        status, body = self._request("POST", "/api/v1/workloads", request.to_dict())
        if status in (200, 201) and isinstance(body, dict):
            return GaneshWorkloadResponse.from_dict(body)
        return GaneshWorkloadResponse(
            workload_id="",
            domain=request.domain,
            problem_id=request.problem_id,
            algorithm=request.algorithm,
            qubits_required=request.qubits_required,
            shots=request.shots,
            status="REGISTRATION_FAILED",
            raw_response=body if isinstance(body, dict) else {"error": str(body)},
        )

    def list_workloads(self) -> List[Dict[str, Any]]:
        """List registered workloads. GET /api/v1/workloads."""
        status, body = self._request("GET", "/api/v1/workloads")
        if status == 200 and isinstance(body, list):
            return body
        if status == 200 and isinstance(body, dict) and "workloads" in body:
            return body["workloads"]
        return []

    def get_workload(self, workload_id: str) -> Dict[str, Any]:
        """Fetch workload details. GET /api/v1/workloads/{workload_id}."""
        status, body = self._request("GET", f"/api/v1/workloads/{workload_id}")
        return body if status == 200 and isinstance(body, dict) else {"error": str(body)}

    def execute_workload(
        self,
        workload_id: str,
        request: Optional[GaneshExecuteRequest] = None,
    ) -> GaneshExecuteResponse:
        """
        Execute a workload on the quantum backend.
        POST /api/v1/workloads/{workload_id}/execute
        """
        req_payload = (request or GaneshExecuteRequest()).to_dict()
        status, body = self._request("POST", f"/api/v1/workloads/{workload_id}/execute", req_payload)
        if status in (200, 201) and isinstance(body, dict):
            return GaneshExecuteResponse.from_dict(body)

        # Polling fallback: check if Render finished processing asynchronously
        for _ in range(3):
            time.sleep(2)
            for ex in reversed(self.list_executions()):
                if ex.get("workload_id") == workload_id:
                    return GaneshExecuteResponse.from_dict(ex)

        return GaneshExecuteResponse(
            execution_id="",
            workload_id=workload_id,
            backend_target=req_payload.get("backend_target", "aer_simulator"),
            shots=req_payload.get("shots", 1024),
            status="EXECUTION_FAILED",
            error_message=str(body),
            raw_response=body if isinstance(body, dict) else {"error": str(body)},
        )

    def list_executions(self) -> List[Dict[str, Any]]:
        """List all executions. GET /api/v1/executions."""
        status, body = self._request("GET", "/api/v1/executions")
        if status == 200 and isinstance(body, list):
            return body
        if status == 200 and isinstance(body, dict) and "executions" in body:
            return body["executions"]
        return []

    def get_execution(self, execution_id: str) -> Dict[str, Any]:
        """Retrieve execution results. GET /api/v1/executions/{execution_id}."""
        status, body = self._request("GET", f"/api/v1/executions/{execution_id}")
        return body if status == 200 and isinstance(body, dict) else {"error": str(body)}

    # -- QCG Sovereign Core Bridging ------------------------------------------

    def bridge_to_qcg_contract(
        self,
        workload_resp: GaneshWorkloadResponse,
        exec_resp: GaneshExecuteResponse,
        trace_id: Optional[str] = None,
        confidence: Optional[float] = None,
    ) -> GaneshQCGBridgeResult:
        """
        Transform Ganesh's quantum execution output into a formal QCG contract:
          1. Construct ComputationExecutionContract (producer_type="QUANTUM")
          2. Compute confidence from candidate distribution or default heuristic
          3. Validate contract against QCG constraints
          4. Sign contract using NodeSigner (ECDSA P-256)
          5. Submit to CanonicalReplayAuthority for sequence assignment & lineage record
          6. Commit to EvidenceLedger and obtain Merkle root inclusion snapshot
        """
        effective_trace_id = trace_id or str(uuid.uuid5(uuid.NAMESPACE_DNS, f"ganesh-exec-{exec_resp.execution_id or workload_resp.workload_id}"))

        # Heuristic confidence calculation from measurement probabilities
        if confidence is not None:
            eff_confidence = max(0.0, min(1.0, confidence))
        elif exec_resp.probabilities and exec_resp.best_candidate:
            eff_confidence = float(exec_resp.probabilities.get(exec_resp.best_candidate, 0.85))
        elif exec_resp.status in ("COMPLETED", "SUCCESS"):
            eff_confidence = 0.95
        else:
            eff_confidence = 0.50

        # Construct payload with quantum results
        payload = {
            "source_service": "BHIV_QUANTUM_APPLICATION_LAYER",
            "provider": "Ganesh Bhiv",
            "workload_id": workload_resp.workload_id,
            "execution_id": exec_resp.execution_id,
            "domain": workload_resp.domain,
            "problem_id": workload_resp.problem_id,
            "algorithm": workload_resp.algorithm,
            "qubits_required": workload_resp.qubits_required,
            "backend_target": exec_resp.backend_target,
            "shots": exec_resp.shots,
            "execution_status": exec_resp.status,
            "best_candidate": exec_resp.best_candidate,
            "measurement_counts": exec_resp.counts,
            "measurement_probabilities": exec_resp.probabilities,
            "execution_time_ms": exec_resp.execution_time_ms,
        }

        # Determine execution path and classification
        is_sim = "simulator" in exec_resp.backend_target.lower()
        classification = ExecutionClassification.QUANTUM_SIMULATED.value if is_sim else ExecutionClassification.QUANTUM_LIVE.value
        path = "SIMULATED" if is_sim else "LIVE"

        # Construct ComputationExecutionContract
        contract = ComputationExecutionContract(
            producer_type="QUANTUM",
            payload=payload,
            confidence=round(eff_confidence, 4),
            trace_id=effective_trace_id,
            contract_version="2.0.0",
            execution_constraints={
                "backend": exec_resp.backend_target,
                "shots": exec_resp.shots,
                "domain": workload_resp.domain,
            },
            execution_classification=classification,
            execution_path=path,
        )

        # Validate contract schema & integrity
        validate_contract(contract)

        # Sign contract with NodeSigner (ECDSA P-256)
        node_proof = self.signer.sign_payload(contract.to_dict())

        # Submit to CanonicalReplayAuthority
        replay_verdict = self.replay_authority.submit(
            message_id=contract.payload_hash,
            issued_at=time.time(),
            trace_reference=effective_trace_id,
        )

        # Commit to EvidenceLedger
        exec_hash = hashlib.sha256(
            f"{contract.payload_hash}:{replay_verdict.sequence_number}:{node_proof.signature}".encode()
        ).hexdigest()

        record = ExecutionRecord(
            execution_id=exec_resp.execution_id or f"exec-{uuid.uuid4().hex[:12]}",
            trace_id=effective_trace_id,
            replay_reference=str(replay_verdict.sequence_number),
            execution_sequence=replay_verdict.sequence_number,
            producer_identity=self.signer.identity.node_id,
            runtime_identity="TANTRA-SOVEREIGN-RUNTIME",
            governance_identity="TANTRA-GOVERNANCE-AUTH-001",
            execution_status=exec_resp.status,
            runtime_hash=hashlib.sha256(contract.contract_version.encode()).hexdigest(),
            execution_hash=exec_hash,
            previous_execution_hash=self.ledger._current_head,
            execution_root_hash="",
            schema_version="2.0.0",
        )

        ledger_snapshot = self.ledger.append(record)

        evidence_payload = {
            "evidence_id": f"EVID-QAPP-{uuid.uuid4().hex[:8]}",
            "service_id": "TANTRA-PSR-QAPP-001",
            "service_name": "BHIV_QUANTUM_APPLICATION_LAYER",
            "endpoint": f"{self.base_url}/api/v1/workloads/{workload_resp.workload_id}/execute",
            "trace_id": effective_trace_id,
            "contract_hash": contract.payload_hash,
            "signer_node_id": self.signer.identity.node_id,
            "node_signature": node_proof.signature,
            "replay_sequence": replay_verdict.sequence_number,
            "replay_status": replay_verdict.status,
            "merkle_root": ledger_snapshot.merkle_root,
            "ledger_chain_length": ledger_snapshot.sequence_length,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        return GaneshQCGBridgeResult(
            contract=contract,
            node_proof=node_proof,
            replay_verdict=replay_verdict,
            ledger_snapshot=ledger_snapshot,
            evidence_payload=evidence_payload,
        )

    def get_evidence_log(self) -> str:
        """Return all API interactions as JSON."""
        return self.log.to_json()

    def export_evidence(self, output_path: str) -> None:
        """Write integration log and state to disk."""
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(self.get_evidence_log())


# ---------------------------------------------------------------------------
# Module Singleton
# ---------------------------------------------------------------------------

_default_client: Optional[GaneshClient] = None


def get_client() -> GaneshClient:
    """Get or create singleton client."""
    global _default_client
    if _default_client is None:
        _default_client = GaneshClient()
    return _default_client


# ---------------------------------------------------------------------------
# CLI Execution / Quick Self-test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
    client = get_client()

    print("=" * 60)
    print("Ganesh Quantum Application Layer Live Probe & Bridge")
    print(f"Target: {client.base_url}")
    print("=" * 60)

    # 1. Health
    h = client.health()
    print(f"[1] Health Check: {h.status} (Service: {h.service}, Version: {h.version})")

    # 2. Capabilities
    caps = client.get_capabilities()
    domains_summary = list(caps.domains.keys()) if isinstance(caps.domains, dict) else [d.get("name", d) if isinstance(d, dict) else str(d) for d in caps.domains]
    backends_summary = list(caps.backends.keys()) if isinstance(caps.backends, dict) else [b.get("name", b) if isinstance(b, dict) else str(b) for b in caps.backends]
    print(f"[2] Capabilities: {len(domains_summary)} domains ({domains_summary})")
    print(f"    Available Backends: {len(backends_summary)} ({backends_summary})")

    # 3. Create Workload for VANA (6 qubits)
    w_req = GaneshWorkloadRequest(
        domain="VANA",
        problem_id="PROB-VANA-REFOREST-001",
        algorithm="QAOA",
        qubits_required=6,
        shots=512,
        formulation={"num_zones": 6, "cost_matrix": [[0, 1], [1, 0]]},
    )
    w_resp = client.create_workload(w_req)
    print(f"[3] Workload Created: ID={w_resp.workload_id}, Domain={w_resp.domain}, Status={w_resp.status}")

    if w_resp.workload_id:
        # 4. Execute on aer_simulator
        e_req = GaneshExecuteRequest(backend_target="aer_simulator", shots=512)
        e_resp = client.execute_workload(w_resp.workload_id, e_req)
        print(f"[4] Execution: ID={e_resp.execution_id}, Status={e_resp.status}, Target={e_resp.backend_target}")
        print(f"    Best Candidate: {e_resp.best_candidate}")
        print(f"    Sample Counts: {list(e_resp.counts.items())[:3]}")

        # 5. Bridge to QCG Contract
        bridge = client.bridge_to_qcg_contract(w_resp, e_resp)
        print(f"[5] QCG Bridge Verified:")
        print(f"    Contract Payload Hash: {bridge.contract.payload_hash}")
        print(f"    Node Proof Signature:  {bridge.node_proof.signature[:32]}...")
        print(f"    Replay Sequence:       {bridge.replay_verdict.sequence_number} ({bridge.replay_verdict.status})")
        print(f"    Merkle Root:           {bridge.ledger_snapshot.merkle_root}")
