"""
integration_harness.py — Phase 3: Runtime Participation Harness

Executes one continuous flow representing a TANTRA ecosystem integration:
- Incoming BHIV contract
- Replay validation
- KESHAV live analysis (root-cause + severity)
- Trust verification
- Runtime execution
- Consensus proof
- Structured output with trace continuity
"""

import tempfile
import time
import logging
import re
from pathlib import Path
from typing import Dict, Any, Tuple

from execution_contract import ComputationExecutionContract
from canonical_replay_authority import CanonicalReplayAuthority
from replay_registry import ReplayRegistry
from producer_verification import ProducerRegistry, ProducerVerificationLayer
from runtime_core import RuntimeCore
from consensus_simulation import ConsensusEngine, DistributedConsensusNode
from node_identity import NodeIdentity

from integration_interfaces import (
    ReplayVerifierInterface,
    TrustVerifierInterface,
    ExecutionValidatorInterface,
    ConsensusVerifierInterface,
    HealthStatusInterface
)

import config

logger = logging.getLogger("qcg.harness")

class TANTRAIntegrationHarness:
    """
    Continuous execution pipeline connecting all standard BHIV interfaces,
    including live KESHAV ecosystem integration.
    """
    def __init__(self):
        # 1. Initialize persistent stores
        import os
        base_dir = os.path.dirname(os.path.abspath(__file__))
        replay_path = Path(os.path.join(base_dir, "replay_registry_persistent.json"))
        trust_path = Path(os.path.join(base_dir, "trust_registry_persistent.json"))
        
        self.replay_registry = ReplayRegistry(path=replay_path)
        self.trust_registry = ProducerRegistry(path=trust_path)
        from evidence_ledger import EvidenceLedger
        self.ledger = EvidenceLedger()
        
        # 2. Initialize Core Engines
        self.replay_auth = CanonicalReplayAuthority(self.replay_registry)
        self.verifier_layer = ProducerVerificationLayer(self.trust_registry)
        self.runtime_core = RuntimeCore()
        
        nodes = [
            DistributedConsensusNode("TANTRA_NODE_1"),
            DistributedConsensusNode("TANTRA_NODE_2"),
            DistributedConsensusNode("TANTRA_NODE_3"),
        ]
        self.consensus_engine = ConsensusEngine(nodes)
        
        # 3. Initialize Standard Interfaces
        self.replay_iface = ReplayVerifierInterface(self.replay_auth)
        self.trust_iface = TrustVerifierInterface(self.verifier_layer)
        self.execution_iface = ExecutionValidatorInterface(self.runtime_core)
        self.consensus_iface = ConsensusVerifierInterface(self.consensus_engine)
        self.health_iface = HealthStatusInterface(self.replay_registry)

        # 4. Initialize Live Ecosystem Clients
        self.keshav_client = None
        if config.KESHAV_ENABLED:
            try:
                from keshav_live_client import KeshavClient
                self.keshav_client = KeshavClient()
                logger.info("KESHAV live client initialized: %s", config.KESHAV_API_URL)
            except Exception as e:
                logger.warning("KESHAV client initialization failed: %s", e)

    def _run_keshav_analysis(self, trace_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Call KESHAV live /analyze endpoint for root-cause analysis.
        Returns analysis result dict or fallback if unavailable.
        """
        if self.keshav_client is None:
            return {
                "status": "SKIPPED",
                "reason": "KESHAV client not enabled",
                "live": False,
            }

        try:
            execution_id = payload.get("execution_id", f"exec-{trace_id}")
            resp = self.keshav_client.analyze_from_contract(
                trace_id=trace_id,
                execution_id=execution_id,
                payload=payload,
            )
            return {
                "status": "COMPLETED",
                "live": True,
                "trace_id": resp.trace_id,
                "root_cause": resp.root_cause,
                "resolution_signal": resp.resolution_signal,
                "impact_score": resp.impact_score,
                "severity": resp.severity,
                "timestamp": resp.timestamp,
            }
        except Exception as e:
            logger.warning("KESHAV analysis failed for trace %s: %s", trace_id, e)
            return {
                "status": "FALLBACK",
                "reason": str(e),
                "live": False,
            }

    def _sanitize_trace_id(self, trace_id: str) -> str:
        """Validate and sanitize trace_id input."""
        if not trace_id or not isinstance(trace_id, str):
            return "unknown"
        # Truncate to max length
        trace_id = trace_id[:config.INPUT_TRACE_ID_MAX_LENGTH]
        # Remove any control characters
        trace_id = re.sub(r'[\x00-\x1f\x7f]', '', trace_id)
        return trace_id.strip() or "unknown"

    def _validate_payload_bounds(self, payload: Dict[str, Any]) -> bool:
        """Check payload doesn't exceed configured key count limits."""
        if not isinstance(payload, dict):
            return False
        if len(payload) > config.INPUT_PAYLOAD_MAX_KEYS:
            return False
        return True

    def process_incoming_contract(self, payload: Dict[str, Any], pub_key: str, auth_token: str = None) -> Tuple[bool, Dict[str, Any]]:
        """
        Main continuous flow for incoming TANTRA contracts.
        
        Each pipeline stage is wrapped in its own error boundary to ensure
        partial failures are isolated and reported with full context.
        """
        from metrics import get_metrics
        metrics = get_metrics()
        
        trace_id = self._sanitize_trace_id(payload.get("trace_id", "unknown"))
        parent_trace = payload.get("parent_trace_id", None)
        issued_at = payload.get("issued_at", time.time())
        
        # Input validation: payload bounds
        if not self._validate_payload_bounds(payload):
            metrics.record_halt("INPUT_VALIDATION_FAILED")
            return False, {
                "trace_id": trace_id,
                "flow_status": "HALTED",
                "halt_reason": "INPUT_VALIDATION: Payload exceeds maximum key count",
                "stages": {}
            }
        
        response = {
            "trace_id": trace_id,
            "parent_trace_id": parent_trace,
            "flow_status": "STARTED",
            "stages": {},
            "stage_timings_ms": {}
        }
        
        try:
            # 1. Replay Validation
            stage_start = time.time()
            try:
                replay_res = self.replay_iface.verify_replay(trace_id, issued_at)
            except Exception as e:
                logger.error("Stage REPLAY failed for trace %s: %s", trace_id, e)
                metrics.record_halt("REPLAY_STAGE_ERROR")
                response["flow_status"] = "HALTED"
                response["halt_reason"] = f"REPLAY_STAGE_ERROR: {type(e).__name__}"
                response["stages"]["replay"] = {"is_valid": False, "error": str(e)}
                self.health_iface.record_process(False)
                return False, response
            response["stage_timings_ms"]["replay"] = round((time.time() - stage_start) * 1000, 2)
            response["stages"]["replay"] = replay_res
            if not replay_res["is_valid"]:
                response["flow_status"] = "HALTED"
                response["halt_reason"] = f"REPLAY_{replay_res['status']}"
                metrics.record_halt(f"REPLAY_{replay_res['status']}")
                self.health_iface.record_process(False)
                return False, response

            # 2. KESHAV Live Analysis (new ecosystem integration step)
            stage_start = time.time()
            try:
                keshav_res = self._run_keshav_analysis(trace_id, payload)
            except Exception as e:
                logger.warning("Stage KESHAV failed for trace %s: %s", trace_id, e)
                keshav_res = {"status": "ERROR", "reason": str(e), "live": False}
            response["stage_timings_ms"]["keshav_analysis"] = round((time.time() - stage_start) * 1000, 2)
            response["stages"]["keshav_analysis"] = keshav_res
                
            # Parse Contract (Governance Boundary)
            try:
                contract = ComputationExecutionContract(**payload)
            except Exception as e:
                response["flow_status"] = "HALTED"
                response["halt_reason"] = f"INVALID_CONTRACT: {e}"
                metrics.record_halt("INVALID_CONTRACT")
                self.health_iface.record_process(False)
                return False, response

            # Auto-register producer if not already known.
            # TRUST BOUNDARY: Registration requires a valid ECDSA public key.
            # The pseudo-token path ("Bearer VALID_GC_TOKEN") has been removed
            # from the production flow. Identity is now verified cryptographically.
            if not self.trust_registry.is_registered(contract.producer_id):
                if not pub_key or len(pub_key) < 16:
                    response["flow_status"] = "HALTED"
                    response["halt_reason"] = "TRUST_REJECTED: Producer not registered and no valid public key provided"
                    metrics.record_halt("TRUST_REJECTED")
                    self.health_iface.record_process(False)
                    return False, response

                identity = NodeIdentity(
                    node_id=contract.producer_id,
                    public_key=pub_key,
                    node_role="PRODUCER",
                    version="1.0.0"
                )
                self.trust_registry.register(identity, allowed_types={contract.producer_type})
                
            # 3. Trust Verification
            stage_start = time.time()
            try:
                trust_res = self.trust_iface.verify_trust(contract)
            except Exception as e:
                logger.error("Stage TRUST failed for trace %s: %s", trace_id, e)
                metrics.record_halt("TRUST_STAGE_ERROR")
                response["flow_status"] = "HALTED"
                response["halt_reason"] = f"TRUST_STAGE_ERROR: {type(e).__name__}"
                response["stages"]["trust"] = {"passed": False, "error": str(e)}
                self.health_iface.record_process(False)
                return False, response
            response["stage_timings_ms"]["trust"] = round((time.time() - stage_start) * 1000, 2)
            response["stages"]["trust"] = trust_res
            if not trust_res["passed"]:
                response["flow_status"] = "HALTED"
                response["halt_reason"] = trust_res["halt_signal"]
                metrics.record_halt("TRUST_REJECTED")
                self.health_iface.record_process(False)
                return False, response
                
            # 4. Runtime Execution
            stage_start = time.time()
            try:
                exec_res = self.execution_iface.validate_execution(contract)
            except Exception as e:
                logger.error("Stage EXECUTION failed for trace %s: %s", trace_id, e)
                metrics.record_halt("EXECUTION_STAGE_ERROR")
                response["flow_status"] = "HALTED"
                response["halt_reason"] = f"EXECUTION_STAGE_ERROR: {type(e).__name__}"
                response["stages"]["execution"] = {"ack": f"HALT:EXECUTION_ERROR", "error": str(e)}
                self.health_iface.record_process(False)
                return False, response
            response["stage_timings_ms"]["execution"] = round((time.time() - stage_start) * 1000, 2)
            response["stages"]["execution"] = exec_res
            if "HALT" in exec_res["ack"]:
                response["flow_status"] = "HALTED"
                response["halt_reason"] = exec_res["ack"]
                metrics.record_halt(exec_res["ack"])
                self.health_iface.record_process(False)
                return False, response
                
            # 5. Consensus Proof
            stage_start = time.time()
            try:
                cons_res = self.consensus_iface.verify_consensus(contract, pub_key)
            except Exception as e:
                logger.error("Stage CONSENSUS failed for trace %s: %s", trace_id, e)
                # Consensus failure is non-fatal — log and continue with empty proof
                cons_res = {"consensus_reached": False, "error": str(e)}
            response["stage_timings_ms"]["consensus"] = round((time.time() - stage_start) * 1000, 2)
            response["stages"]["consensus"] = cons_res
            
            # Trace Continuity propagation
            response["trace_continuity"] = {
                "sequence_number": replay_res["sequence_number"],
                "runtime_hash": exec_res["runtime_hash"],
                "final_hash": cons_res.get("final_hash"),
                "keshav_severity": keshav_res.get("severity"),
            }
            
            # Record Evidence
            from execution_record import ExecutionRecord
            import uuid
            import hashlib
            record = ExecutionRecord(
                execution_id=str(uuid.uuid4()),
                trace_id=trace_id,
                replay_reference=replay_res["sequence_number"],
                execution_sequence=len(self.ledger._records) + 1,
                producer_identity=contract.producer_id,
                runtime_identity="EXTERNAL_RUNTIME_v1",
                governance_identity="TANTRA_GOVERNANCE",
                execution_status=response["flow_status"],
                runtime_hash=exec_res["runtime_hash"],
                previous_execution_hash=self.ledger._current_head,
                execution_hash=hashlib.sha256(f"{trace_id}:{exec_res['runtime_hash']}".encode()).hexdigest(),
                execution_root_hash=self.ledger.get_merkle_root(),
                schema_version="1.0.0"
            )
            self.ledger.append(record)
            
            response["flow_status"] = "COMPLETED"
            self.health_iface.record_process(True)
            return True, response
            
        except Exception as e:
            logger.error("Pipeline-level exception for trace %s: %s", trace_id, e, exc_info=True)
            response["flow_status"] = "ERROR"
            response["error"] = str(e)
            metrics.record_error("pipeline_exception")
            self.health_iface.record_process(False)
            return False, response

    def get_keshav_evidence(self) -> str:
        """Return KESHAV integration evidence log as JSON."""
        if self.keshav_client:
            return self.keshav_client.get_evidence_log()
        return "[]"

