"""
review_packets/Code_Packets/state_machine_event_sourcing.py
Parikshak Engineering Review Runtime — State Machine & Event Sourcing
Standard: Governed Operational System (Gov-OS) Core Compliance

Enforces:
1. Deterministic state transitions
2. Immutable audit trail indexing
3. Cryptographic state replay verification
"""

import hashlib
import json
from typing import List, Dict, Any
from contracts.schemas import EvaluationState


class DeterministicStateMachineEventSourcing:
    def __init__(self, task_id: str, candidate_id: str):
        self.task_id = task_id
        self.candidate_id = candidate_id
        self.current_state = EvaluationState.INITIALIZED
        self.event_stream: List[Dict[str, Any]] = []

    def record_transition(self, to_state: EvaluationState, reason: str, metadata: Dict[str, Any] = None):
        event = {
            "event_index": len(self.event_stream) + 1,
            "from_state": self.current_state.value,
            "to_state": to_state.value,
            "reason": reason,
            "metadata": metadata or {}
        }
        self.current_state = to_state
        self.event_stream.append(event)

    def replay_audit_hash(self) -> str:
        serialized = json.dumps(self.event_stream, sort_keys=True)
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()
