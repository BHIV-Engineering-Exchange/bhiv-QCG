"""
tests/test_evidence_ledger.py — Phase 2: Evidence Ledger Unit Tests

Focused unit tests for the EvidenceLedger covering:
- Append and chain integrity
- Merkle root computation
- Chain verification
- Persistence round-trip (save/load)
- Genesis state
- Invalid previous hash rejection
- Snapshot correctness
"""

import pytest
import hashlib
import json
import os
import tempfile

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from evidence_ledger import EvidenceLedger, LedgerSnapshot, _hash_pair
from execution_record import ExecutionRecord


# ═══════════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════════

def _make_record(
    execution_id: str = "exec-001",
    trace_id: str = "trace-001",
    previous_hash: str = None,
    runtime_hash: str = "abc123",
) -> ExecutionRecord:
    """Create a valid ExecutionRecord for testing."""
    exec_hash = hashlib.sha256(f"{trace_id}:{runtime_hash}".encode()).hexdigest()
    return ExecutionRecord(
        execution_id=execution_id,
        trace_id=trace_id,
        replay_reference=1,
        execution_sequence=1,
        producer_identity="TEST_PRODUCER",
        runtime_identity="TEST_RUNTIME",
        governance_identity="TEST_GOVERNANCE",
        execution_status="COMPLETED",
        runtime_hash=runtime_hash,
        previous_execution_hash=previous_hash or "",
        execution_hash=exec_hash,
        execution_root_hash="",
        schema_version="1.0.0",
    )


# ═══════════════════════════════════════════════════════════════════════════
# Genesis State
# ═══════════════════════════════════════════════════════════════════════════

class TestGenesisState:

    def test_new_ledger_is_empty(self):
        ledger = EvidenceLedger()
        assert len(ledger._records) == 0

    def test_new_ledger_has_genesis_head(self):
        ledger = EvidenceLedger()
        expected = hashlib.sha256(b"GENESIS").hexdigest()
        assert ledger._current_head == expected

    def test_empty_ledger_merkle_root(self):
        ledger = EvidenceLedger()
        root = ledger.get_merkle_root()
        expected = hashlib.sha256(b"EMPTY_LEDGER").hexdigest()
        assert root == expected

    def test_empty_ledger_snapshot(self):
        ledger = EvidenceLedger()
        snapshot = ledger.get_snapshot()
        assert isinstance(snapshot, LedgerSnapshot)
        assert snapshot.sequence_length == 0


# ═══════════════════════════════════════════════════════════════════════════
# Append & Chain Integrity
# ═══════════════════════════════════════════════════════════════════════════

class TestAppendAndChain:

    def test_append_single_record(self):
        ledger = EvidenceLedger()
        record = _make_record(previous_hash=ledger._current_head)
        snapshot = ledger.append(record)
        assert snapshot.sequence_length == 1
        assert len(ledger._records) == 1

    def test_append_updates_head(self):
        ledger = EvidenceLedger()
        genesis = ledger._current_head
        record = _make_record(previous_hash=genesis)
        ledger.append(record)
        assert ledger._current_head != genesis

    def test_chain_head_is_deterministic(self):
        """Same record appended to same genesis should yield same head."""
        ledger1 = EvidenceLedger()
        ledger2 = EvidenceLedger()
        
        rec1 = _make_record(previous_hash=ledger1._current_head)
        rec2 = _make_record(previous_hash=ledger2._current_head)
        
        ledger1.append(rec1)
        ledger2.append(rec2)
        
        assert ledger1._current_head == ledger2._current_head

    def test_append_multiple_records(self):
        ledger = EvidenceLedger()
        for i in range(5):
            rec = _make_record(
                execution_id=f"exec-{i}",
                trace_id=f"trace-{i}",
                previous_hash=ledger._current_head,
                runtime_hash=f"hash-{i}",
            )
            ledger.append(rec)
        assert len(ledger._records) == 5
        assert len(ledger._evidence_hashes) == 5

    def test_invalid_previous_hash_raises(self):
        ledger = EvidenceLedger()
        # First record with wrong previous hash
        rec = _make_record(previous_hash="wrong_hash")
        with pytest.raises(ValueError, match="Invalid previous hash"):
            ledger.append(rec)

    def test_empty_previous_hash_allowed(self):
        """Records with empty previous_hash skip the continuity check."""
        ledger = EvidenceLedger()
        rec = _make_record(previous_hash="")
        snapshot = ledger.append(rec)
        assert snapshot.sequence_length == 1


# ═══════════════════════════════════════════════════════════════════════════
# Merkle Root
# ═══════════════════════════════════════════════════════════════════════════

class TestMerkleRoot:

    def test_single_record_merkle_root(self):
        ledger = EvidenceLedger()
        rec = _make_record(previous_hash=ledger._current_head)
        ledger.append(rec)
        root = ledger.get_merkle_root()
        # Single hash — the root IS the single evidence hash
        assert root == ledger._evidence_hashes[0]

    def test_merkle_root_changes_with_new_record(self):
        ledger = EvidenceLedger()
        rec1 = _make_record(previous_hash=ledger._current_head, trace_id="t1", runtime_hash="h1")
        ledger.append(rec1)
        root1 = ledger.get_merkle_root()

        rec2 = _make_record(
            execution_id="exec-002",
            previous_hash=ledger._current_head,
            trace_id="t2",
            runtime_hash="h2",
        )
        ledger.append(rec2)
        root2 = ledger.get_merkle_root()

        assert root1 != root2

    def test_merkle_root_deterministic(self):
        """Two ledgers with identical records should have same root."""
        def build_ledger():
            ledger = EvidenceLedger()
            for i in range(3):
                rec = _make_record(
                    execution_id=f"exec-{i}",
                    trace_id=f"trace-{i}",
                    previous_hash=ledger._current_head,
                    runtime_hash=f"hash-{i}",
                )
                ledger.append(rec)
            return ledger

        l1 = build_ledger()
        l2 = build_ledger()
        assert l1.get_merkle_root() == l2.get_merkle_root()

    def test_hash_pair_helper(self):
        result = _hash_pair("left", "right")
        expected = hashlib.sha256(b"leftright").hexdigest()
        assert result == expected


# ═══════════════════════════════════════════════════════════════════════════
# Chain Verification
# ═══════════════════════════════════════════════════════════════════════════

class TestChainVerification:

    def test_verify_empty_chain(self):
        ledger = EvidenceLedger()
        assert ledger.verify_chain() is True

    def test_verify_valid_chain(self):
        ledger = EvidenceLedger()
        for i in range(5):
            rec = _make_record(
                execution_id=f"exec-{i}",
                trace_id=f"trace-{i}",
                previous_hash=ledger._current_head,
                runtime_hash=f"hash-{i}",
            )
            ledger.append(rec)
        assert ledger.verify_chain() is True

    def test_verify_tampered_chain_fails(self):
        ledger = EvidenceLedger()
        for i in range(3):
            rec = _make_record(
                execution_id=f"exec-{i}",
                trace_id=f"trace-{i}",
                previous_hash=ledger._current_head,
                runtime_hash=f"hash-{i}",
            )
            ledger.append(rec)

        # Tamper with evidence hashes
        ledger._evidence_hashes[1] = "tampered_hash"
        assert ledger.verify_chain() is False


# ═══════════════════════════════════════════════════════════════════════════
# Persistence
# ═══════════════════════════════════════════════════════════════════════════

class TestPersistence:

    def test_save_and_load_roundtrip(self):
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        try:
            # Save
            ledger = EvidenceLedger(persistence_path=path)
            for i in range(3):
                rec = _make_record(
                    execution_id=f"exec-{i}",
                    trace_id=f"trace-{i}",
                    previous_hash=ledger._current_head,
                    runtime_hash=f"hash-{i}",
                )
                ledger.append(rec)
            original_head = ledger._current_head
            original_root = ledger.get_merkle_root()

            # Load into new instance
            ledger2 = EvidenceLedger(persistence_path=path)
            assert len(ledger2._records) == 3
            assert ledger2._current_head == original_head
            assert ledger2.get_merkle_root() == original_root
            assert ledger2.verify_chain() is True
        finally:
            os.unlink(path)

    def test_load_from_nonexistent_path(self):
        ledger = EvidenceLedger(persistence_path="/nonexistent/path.json")
        # Should gracefully fall back to empty ledger
        assert len(ledger._records) == 0


# ═══════════════════════════════════════════════════════════════════════════
# Snapshot
# ═══════════════════════════════════════════════════════════════════════════

class TestSnapshot:

    def test_snapshot_after_appends(self):
        ledger = EvidenceLedger()
        for i in range(3):
            rec = _make_record(
                execution_id=f"exec-{i}",
                trace_id=f"trace-{i}",
                previous_hash=ledger._current_head,
                runtime_hash=f"hash-{i}",
            )
            ledger.append(rec)

        snapshot = ledger.get_snapshot()
        assert snapshot.sequence_length == 3
        assert snapshot.merkle_root == ledger.get_merkle_root()
        assert snapshot.latest_evidence_hash == ledger._current_head
        assert snapshot.timestamp is not None
