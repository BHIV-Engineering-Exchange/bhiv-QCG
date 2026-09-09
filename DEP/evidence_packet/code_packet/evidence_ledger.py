import hashlib
import json
import os
import logging
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any, Optional

from execution_record import ExecutionRecord

logger = logging.getLogger("qcg.evidence_ledger")


@dataclass(frozen=True)
class LedgerSnapshot:
    """
    Represents a snapshot of the Evidence Ledger at a given sequence.
    """
    sequence_length: int
    merkle_root: str
    latest_evidence_hash: str
    timestamp: str


def _hash_pair(left: str, right: str) -> str:
    """Deterministic hash of two strings for the Merkle tree."""
    return hashlib.sha256(f"{left}{right}".encode()).hexdigest()


class EvidenceLedger:
    """
    Phase 4: Deterministic Evidence Ledger
    
    Implements a deterministic evidence chain.
    Every execution must produce:
      Execution -> Evidence Hash -> Previous Hash -> Execution Chain -> Merkle Root -> Ledger Snapshot
    
    This is an execution evidence ledger. It is NOT a blockchain.
    """

    def __init__(self, persistence_path: Optional[str] = None):
        self._records: List[ExecutionRecord] = []
        self._evidence_hashes: List[str] = []
        # The chain head hash
        self._current_head: str = hashlib.sha256(b"GENESIS").hexdigest()
        self._persistence_path = persistence_path

        # Attempt to restore from persistence on init
        if self._persistence_path:
            self._load_from_disk()

    def append(self, record: ExecutionRecord) -> LedgerSnapshot:
        """
        Appends an ExecutionRecord to the ledger.
        Computes the evidence hash and updates the chain.
        """
        # Ensure previous hash matches current head
        if record.previous_execution_hash and record.previous_execution_hash != self._current_head:
            raise ValueError(f"Invalid previous hash. Expected {self._current_head}, got {record.previous_execution_hash}")

        # In a real implementation we would sign or hash the whole record, 
        # but here we use the record's intrinsic execution_hash as the base evidence hash.
        evidence_base_hash = record.execution_hash

        # Chain it
        new_chain_hash = _hash_pair(self._current_head, evidence_base_hash)
        
        self._records.append(record)
        self._evidence_hashes.append(new_chain_hash)
        self._current_head = new_chain_hash

        # Auto-persist on every append
        if self._persistence_path:
            self._save_to_disk()

        return self.get_snapshot()

    def get_merkle_root(self) -> str:
        """
        Computes the Merkle Root of all evidence hashes in the ledger.
        """
        if not self._evidence_hashes:
            return hashlib.sha256(b"EMPTY_LEDGER").hexdigest()

        # Build Merkle tree from current hashes
        current_level = self._evidence_hashes[:]
        
        while len(current_level) > 1:
            next_level = []
            for i in range(0, len(current_level), 2):
                left = current_level[i]
                # Duplicate the last node if odd number of hashes
                right = current_level[i + 1] if i + 1 < len(current_level) else left
                next_level.append(_hash_pair(left, right))
            current_level = next_level

        return current_level[0]

    def get_snapshot(self) -> LedgerSnapshot:
        """
        Returns a snapshot of the current state of the ledger.
        """
        import datetime
        return LedgerSnapshot(
            sequence_length=len(self._records),
            merkle_root=self.get_merkle_root(),
            latest_evidence_hash=self._current_head,
            timestamp=datetime.datetime.now(datetime.timezone.utc).isoformat()
        )

    def verify_chain(self) -> bool:
        """
        Verifies the cryptographic integrity of the entire chain.
        """
        head = hashlib.sha256(b"GENESIS").hexdigest()
        for i, record in enumerate(self._records):
            if record.previous_execution_hash and record.previous_execution_hash != head:
                return False
            expected_hash = _hash_pair(head, record.execution_hash)
            if self._evidence_hashes[i] != expected_hash:
                return False
            head = expected_hash

        return head == self._current_head

    # -- Persistence --------------------------------------------------------

    def _save_to_disk(self) -> None:
        """Persist the ledger state to disk for restart continuity."""
        if not self._persistence_path:
            return
        try:
            os.makedirs(os.path.dirname(self._persistence_path) or ".", exist_ok=True)
            state = {
                "records": [asdict(r) for r in self._records],
                "evidence_hashes": self._evidence_hashes,
                "current_head": self._current_head,
                "saved_at": datetime.now(timezone.utc).isoformat(),
                "chain_length": len(self._records),
            }
            # Write atomically via temp file
            tmp_path = self._persistence_path + ".tmp"
            with open(tmp_path, "w") as f:
                json.dump(state, f, indent=2, default=str)
            os.replace(tmp_path, self._persistence_path)
            logger.debug("Evidence ledger persisted: %d records", len(self._records))
        except Exception as e:
            logger.error("Failed to persist evidence ledger: %s", e)

    def _load_from_disk(self) -> bool:
        """Restore ledger state from disk. Returns True if restored."""
        if not self._persistence_path or not os.path.exists(self._persistence_path):
            return False
        try:
            with open(self._persistence_path, "r") as f:
                state = json.load(f)

            self._records = [
                ExecutionRecord(**r) for r in state.get("records", [])
            ]
            self._evidence_hashes = state.get("evidence_hashes", [])
            self._current_head = state.get(
                "current_head",
                hashlib.sha256(b"GENESIS").hexdigest(),
            )
            logger.info(
                "Evidence ledger restored from disk: %d records, head=%s",
                len(self._records),
                self._current_head[:16],
            )
            return True
        except Exception as e:
            logger.error("Failed to restore evidence ledger: %s", e)
            return False

    def save_to_disk(self) -> None:
        """Public API for explicit persistence."""
        self._save_to_disk()

    def load_from_disk(self) -> bool:
        """Public API for explicit restoration."""
        return self._load_from_disk()
