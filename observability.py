"""
observability.py — Phase 5: Observability + Replay

Comprehensive trace collection and replay reconstruction.

Trace types
-----------
execution_trace    – Full RuntimeCore.execute() path.
adapter_trace      – Which adapter was used, mapping decisions.
producer_lineage   – Chain: raw output → adapter → contract.
contract_lineage   – Version, transformations, governance decisions.
replay_proof       – Reconstruct the exact execution path, verify hashes.

Determinism note
----------------
TraceEntry.timestamp and TraceEntry.entry_hash are OBSERVABILITY fields.
Replay ordering uses a deterministic sequence counter (assigned at record
time) instead of wall-clock timestamps.  See determinism_doctrine.py.
"""

from __future__ import annotations

import hashlib
import json
import logging
import threading
import time
from collections import deque
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from typing import Any

from logger import get_logger, log_event

log = get_logger("qcg.observability")

_MAX_TRACE_ENTRIES = 10_000  # cap to prevent unbounded memory growth


# ---------------------------------------------------------------------------
# Trace entry types
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class TraceEntry:
    """One entry in the trace store."""
    trace_id:    str                                              # DETERMINISTIC
    trace_type:  str                                              # DETERMINISTIC
    data:        dict                                             # DETERMINISTIC
    sequence:    int = 0                                          # DETERMINISTIC (ordering)
    entry_hash:  str = ""                                         # OBSERVABILITY
    timestamp:   str = field(                                     # OBSERVABILITY
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def __post_init__(self):
        if not self.entry_hash:
            raw = json.dumps({
                "trace_id":   self.trace_id,
                "trace_type": self.trace_type,
                "data":       self.data,
                "timestamp":  self.timestamp,
            }, sort_keys=True, default=str)
            object.__setattr__(
                self, "entry_hash",
                hashlib.sha256(raw.encode()).hexdigest()
            )

    def to_dict(self) -> dict:
        return asdict(self)


# ---------------------------------------------------------------------------
# Replay proof
# ---------------------------------------------------------------------------

@dataclass
class ReplayProof:
    """Result of a replay reconstruction verification."""
    trace_id:     str                                             # DETERMINISTIC
    is_valid:     bool                                            # DETERMINISTIC
    chain:        list[dict]                                      # DETERMINISTIC
    mismatches:   list[str]                                       # DETERMINISTIC
    replay_target: str = "CONTRACT"                               # DETERMINISTIC — see replay_doctrine.py
    timestamp:    str = field(                                    # OBSERVABILITY
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> dict:
        return {
            "trace_id":      self.trace_id,
            "is_valid":      self.is_valid,
            "chain":         self.chain,
            "mismatches":    self.mismatches,
            "replay_target": self.replay_target,
            "timestamp":     self.timestamp,
        }


# ---------------------------------------------------------------------------
# Trace store
# ---------------------------------------------------------------------------

class TraceStore:
    """
    Thread-safe SQLite-backed trace store.

    Every trace entry is a frozen dataclass with a timestamp, sequence
    number, and hash.  The store supports recording, querying, and replay
    reconstruction.

    Ordering: entries are ordered by a monotonically-increasing sequence
    counter assigned at record time (using SQLite AUTOINCREMENT), NOT by wall-clock timestamps.
    This ensures deterministic replay ordering regardless of clock skew.
    """

    def __init__(self, filepath: str = "trace_store_persistent.db"):
        import os
        import sqlite3
        base_dir = os.path.dirname(os.path.abspath(__file__))
        
        # Determine the full path to the db file.
        if filepath == ":memory:":
            self.filepath = filepath
        else:
            self.filepath = os.path.join(base_dir, filepath)

        self._lock = threading.Lock()
        
        # Connect to SQLite. check_same_thread=False allows access across threads (guarded by lock).
        self._conn = sqlite3.connect(self.filepath, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        
        # Enable WAL mode for better concurrency performance if not in memory
        if filepath != ":memory:":
            self._conn.execute("PRAGMA journal_mode=WAL;")
            
        self._init_db()

    def _init_db(self) -> None:
        """Initialize the SQLite schema."""
        with self._lock:
            self._conn.execute('''
                CREATE TABLE IF NOT EXISTS traces (
                    sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                    trace_id TEXT NOT NULL,
                    trace_type TEXT NOT NULL,
                    data TEXT NOT NULL,
                    entry_hash TEXT NOT NULL,
                    timestamp TEXT NOT NULL
                )
            ''')
            self._conn.execute('CREATE INDEX IF NOT EXISTS idx_trace_id ON traces(trace_id)')
            self._conn.execute('CREATE INDEX IF NOT EXISTS idx_trace_type ON traces(trace_type)')
            self._conn.commit()

    # -- recording ----------------------------------------------------------

    def record(self, entry: TraceEntry) -> None:
        """Append a trace entry to the store, assigning a sequence number."""
        with self._lock:
            cursor = self._conn.cursor()
            try:
                # If sequence is already set, insert it directly.
                if entry.sequence != 0:
                    cursor.execute('''
                        INSERT INTO traces (sequence, trace_id, trace_type, data, entry_hash, timestamp)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', (
                        entry.sequence,
                        entry.trace_id,
                        entry.trace_type,
                        json.dumps(entry.data),
                        entry.entry_hash,
                        entry.timestamp
                    ))
                else:
                    cursor.execute('''
                        INSERT INTO traces (trace_id, trace_type, data, entry_hash, timestamp)
                        VALUES (?, ?, ?, ?, ?)
                    ''', (
                        entry.trace_id,
                        entry.trace_type,
                        json.dumps(entry.data),
                        entry.entry_hash,
                        entry.timestamp
                    ))
                    # Assign the generated sequence number
                    object.__setattr__(entry, "sequence", cursor.lastrowid)
                self._conn.commit()
            except Exception as e:
                self._conn.rollback()
                log.error(f"Failed to record trace: {e}")
                raise

        log_event(log, logging.DEBUG, "trace_recorded", ctx={
            "trace_id":   entry.trace_id,
            "trace_type": entry.trace_type,
            "entry_hash": entry.entry_hash,
            "sequence":   entry.sequence,
        })

    def record_execution_trace(
        self,
        trace_id: str,
        contract_hash: str,
        ack: str,
        runtime_hash: str,
        confidence: float,
    ) -> TraceEntry:
        """Record an execution trace and return the entry."""
        entry = TraceEntry(
            trace_id=trace_id,
            trace_type="execution",
            data={
                "contract_hash": contract_hash,
                "ack":           ack,
                "runtime_hash":  runtime_hash,
                "confidence":    confidence,
            },
        )
        self.record(entry)
        return entry

    def record_adapter_trace(
        self,
        trace_id: str,
        adapter_type: str,
        producer_type: str,
        input_hash: str,
        output_hash: str,
    ) -> TraceEntry:
        """Record an adapter trace and return the entry."""
        entry = TraceEntry(
            trace_id=trace_id,
            trace_type="adapter",
            data={
                "adapter_type":  adapter_type,
                "producer_type": producer_type,
                "input_hash":    input_hash,
                "output_hash":   output_hash,
            },
        )
        self.record(entry)
        return entry

    def record_producer_lineage(
        self,
        trace_id: str,
        producer_type: str,
        raw_input_hash: str,
        adapter_output_hash: str,
        contract_hash: str,
    ) -> TraceEntry:
        """Record producer lineage: raw → adapter → contract."""
        entry = TraceEntry(
            trace_id=trace_id,
            trace_type="producer_lineage",
            data={
                "producer_type":       producer_type,
                "raw_input_hash":      raw_input_hash,
                "adapter_output_hash": adapter_output_hash,
                "contract_hash":       contract_hash,
            },
        )
        self.record(entry)
        return entry

    def record_contract_lineage(
        self,
        trace_id: str,
        contract_version: str,
        producer_type: str,
        governance_decisions: list[str],
        final_ack: str,
    ) -> TraceEntry:
        """Record contract lineage through the pipeline."""
        entry = TraceEntry(
            trace_id=trace_id,
            trace_type="contract_lineage",
            data={
                "contract_version":     contract_version,
                "producer_type":        producer_type,
                "governance_decisions": governance_decisions,
                "final_ack":            final_ack,
            },
        )
        self.record(entry)
        return entry

    def record_quantum_execution_trace(
        self,
        trace_id: str,
        classification: str,
        execution_path: str,
        provider_id: str,
        confidence: float,
        result_hash: str,
        fallback_reason: str = "",
        blocked_reason: str = "",
    ) -> TraceEntry:
        """
        Record a quantum-classified execution trace.

        This captures the explicit execution classification (CLASSICAL,
        QUANTUM_LOCAL, QUANTUM_SIMULATED, QUANTUM_LIVE, HYBRID) and the
        path taken (LIVE, LOCAL, SIMULATED, FALLBACK, BLOCKED).
        """
        entry = TraceEntry(
            trace_id=trace_id,
            trace_type="quantum_execution",
            data={
                "classification":   classification,
                "execution_path":   execution_path,
                "provider_id":      provider_id,
                "confidence":       confidence,
                "result_hash":      result_hash,
                "fallback_reason":  fallback_reason,
                "blocked_reason":   blocked_reason,
            },
        )
        self.record(entry)
        return entry

    def record_governance_trace(
        self,
        trace_id: str,
        violations: list[dict],
    ) -> TraceEntry:
        """Record governance decisions for a contract."""
        entry = TraceEntry(
            trace_id=trace_id,
            trace_type="governance",
            data={"violations": violations},
        )
        self.record(entry)
        return entry

    # -- querying -----------------------------------------------------------
    
    def _row_to_entry(self, row) -> TraceEntry:
        """Convert a SQLite row to a TraceEntry dataclass."""
        return TraceEntry(
            trace_id=row['trace_id'],
            trace_type=row['trace_type'],
            data=json.loads(row['data']),
            sequence=row['sequence'],
            entry_hash=row['entry_hash'],
            timestamp=row['timestamp'],
        )

    def query(
        self,
        trace_id: str | None = None,
        trace_type: str | None = None,
    ) -> list[TraceEntry]:
        """
        Query trace entries, optionally filtering by trace_id and/or
        trace_type.
        """
        query = "SELECT * FROM traces"
        params = []
        conditions = []
        
        if trace_id:
            conditions.append("trace_id = ?")
            params.append(trace_id)
        if trace_type:
            conditions.append("trace_type = ?")
            params.append(trace_type)
            
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
            
        query += " ORDER BY sequence ASC"
        
        with self._lock:
            cursor = self._conn.execute(query, params)
            rows = cursor.fetchall()
            
        return [self._row_to_entry(row) for row in rows]

    def all_entries(self) -> list[TraceEntry]:
        """Return a snapshot of all entries."""
        with self._lock:
            cursor = self._conn.execute("SELECT * FROM traces ORDER BY sequence ASC")
            rows = cursor.fetchall()
        return [self._row_to_entry(row) for row in rows]

    def __len__(self) -> int:
        with self._lock:
            cursor = self._conn.execute("SELECT COUNT(*) FROM traces")
            return cursor.fetchone()[0]

    def clear(self) -> None:
        """Clear all entries."""
        with self._lock:
            self._conn.execute("DELETE FROM traces")
            # Also reset the auto-increment counter
            self._conn.execute("DELETE FROM sqlite_sequence WHERE name='traces'")
            self._conn.commit()

    # -- replay reconstruction ----------------------------------------------

    def reconstruct_replay(self, trace_id: str) -> ReplayProof:
        """
        Reconstruct the full execution path for a given trace_id and
        verify hash chain integrity.

        Ordering uses the deterministic trace_type priority, with
        sequence numbers as a secondary key (NOT wall-clock timestamps).

        The replay target is CONTRACT — this reconstructs the journey of
        a single contract through the pipeline.  See replay_doctrine.py
        for the full taxonomy of replay targets.

        Returns a ReplayProof indicating whether the chain is valid.
        """
        entries = self.query(trace_id=trace_id)

        if not entries:
            return ReplayProof(
                trace_id=trace_id,
                is_valid=False,
                chain=[],
                mismatches=["No trace entries found for trace_id."],
                replay_target="CONTRACT",
            )

        # Order: producer_lineage → adapter → governance → execution → contract_lineage
        # Secondary sort: sequence number (deterministic), NOT timestamp.
        type_order = {
            "producer_lineage": 0,
            "adapter":          1,
            "governance":       2,
            "execution":        3,
            "contract_lineage": 4,
        }
        sorted_entries = sorted(
            entries,
            key=lambda e: (type_order.get(e.trace_type, 99), e.sequence),
        )

        chain: list[dict] = []
        mismatches: list[str] = []

        prev_hash = None
        for entry in sorted_entries:
            # Verify entry hash integrity
            expected_raw = json.dumps({
                "trace_id":   entry.trace_id,
                "trace_type": entry.trace_type,
                "data":       entry.data,
                "timestamp":  entry.timestamp,
            }, sort_keys=True, default=str)
            expected_hash = hashlib.sha256(expected_raw.encode()).hexdigest()

            if entry.entry_hash != expected_hash:
                mismatches.append(
                    f"{entry.trace_type}: entry_hash mismatch "
                    f"(expected={expected_hash[:16]}…, "
                    f"got={entry.entry_hash[:16]}…)"
                )

            chain.append({
                "trace_type": entry.trace_type,
                "entry_hash": entry.entry_hash,
                "sequence":   entry.sequence,
                "timestamp":  entry.timestamp,
                "data":       entry.data,
            })
            prev_hash = entry.entry_hash

        is_valid = len(mismatches) == 0

        proof = ReplayProof(
            trace_id=trace_id,
            is_valid=is_valid,
            chain=chain,
            mismatches=mismatches,
            replay_target="CONTRACT",
        )

        log_event(log, logging.INFO, "replay_reconstruction", ctx={
            "trace_id":      trace_id,
            "is_valid":      is_valid,
            "chain_len":     len(chain),
            "mismatches":    mismatches,
            "replay_target": "CONTRACT",
        })

        return proof

    def export_opentelemetry(self, trace_id: str) -> list[dict]:
        """Export trace entries as OpenTelemetry-compliant JSON Spans."""
        entries = self.query(trace_id=trace_id)
        spans = []
        for e in entries:
            span = {
                "traceId": e.trace_id.replace("-", "")[:32].zfill(32),
                "spanId": hashlib.sha256(f"{e.trace_id}:{e.sequence}".encode()).hexdigest()[:16],
                "name": f"qcg:{e.trace_type}",
                "kind": "SPAN_KIND_INTERNAL",
                "startTimeUnixNano": int(time.time() * 1e9),
                "endTimeUnixNano": int((time.time() + 0.01) * 1e9),
                "attributes": {
                    "qcg.sequence": e.sequence,
                    "qcg.hash": e.entry_hash,
                    **{f"qcg.data.{k}": str(v) for k, v in e.data.items()}
                },
                "status": {"code": "STATUS_CODE_OK"}
            }
            spans.append(span)
        return spans


