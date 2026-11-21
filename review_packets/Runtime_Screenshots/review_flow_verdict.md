# Parikshak Operational UI — Review Flow & Evaluation Verdict
Standard: Governed Operational System (Gov-OS) Core Compliance

```mermaid
sequenceDiagram
    autonumber
    actor Candidate as Candidate (Kanishk Singh)
    participant Engine as Parikshak Evaluation Engine
    participant Shakti as GC Shakti Policy Authority
    participant Ledger as Gov-OS Cryptographic Ledger
    participant Niyantran as Niyantran Orchestrator
    participant Bucket as Bucket Evidence Storage
    actor Reviewer as Engineering Reviewer

    Candidate->>Engine: Submit Review Packet (v1.0 Payload)
    Engine->>Shakti: Validate Gov-OS Compliance & Scan Forbidden Patterns
    Shakti-->>Engine: Compliance Confirmed (Zero Violations)
    Engine->>Engine: Execute Weighted Scoring & State Machine Transitions
    Engine->>Engine: Compute Deterministic SHA-256 State Hash
    Engine->>Ledger: Register Canonical State Hash & Audit Ref
    Engine->>Bucket: Store Immutable Evidence Pointer
    Engine-->>Reviewer: Render 1-Minute High-Density Cognition Surface
    Reviewer->>Niyantran: Single-Click Approve & Auto-Assign Task (Zero Context Switch)
    Niyantran-->>Candidate: Notify Canonical Assignment (T-GOV-003)
```

### Deterministic State Machine Traversal Trail
1. `INITIALIZED` $\to$ `INPUT_VALIDATED`: Inbound payload conforms strictly to v1.0 schema contracts.
2. `INPUT_VALIDATED` $\to$ `GOV_OS_AUDIT`: Submission scanned for forbidden patterns (`workflow_execution_engine`, `direct_masterdb_schema_mutation`).
3. `GOV_OS_AUDIT` $\to$ `RULES_APPLIED`: Normalized scoring weights applied across 4 evaluation categories.
4. `RULES_APPLIED` $\to$ `HASH_COMPUTED`: SHA-256 state hash generated from canonical JSON serialization.
5. `HASH_COMPUTED` $\to$ `VERIFIED`: Replay verification confirms 100% cryptographic equality.
6. `VERIFIED` $\to$ `COMPLETED`: Verdict issued with composite score 100.0/100 and status `PASS`.
