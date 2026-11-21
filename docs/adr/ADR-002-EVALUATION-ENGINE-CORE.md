# Architecture Decision Record: ADR-002
## Evaluation Engine Logic, Deterministic Verification & Gov-OS Core Compliance

**Status**: `APPROVED & IMPLEMENTED`  
**Date**: `2026-11-21`  
**Authors**: `Kanishk Singh`, `Pritesh Patra`, `BHQ Architecture Board`  
**Target Product**: `Parikshak Engineering Review Runtime (PARIKSHAK)`  
**Standard**: `Governed Operational System (Gov-OS) Core Compliance`  

---

## 1. Context and Problem Statement
Parikshak Engineering Review Runtime requires a government-grade, operational evaluation engine capable of processing engineering submissions, executing deterministic scoring rules, enforcing strict inbound and outbound schema contracts (v1.0), and producing verifiable cryptographic runtime proofs.

Superficial UI redesigns or non-deterministic heuristics cannot meet the Gov-OS standard. Reviewers, developers, and governance authorities require:
1. Deterministic transitions across state machine states.
2. 50-run identical SHA-256 state hashes for immutable replay audits.
3. Complete error boundary coverage with zero unhandled 500 exceptions on malformed or adversarial inputs.
4. Prohibition of architectural anti-patterns (`workflow_execution_engine`, `direct_masterdb_schema_mutation`).
5. Zero-context-switch task handovers via Niyantran orchestrations with complete multi-phase BHIV specifications.

---

## 2. Decision
We have implemented the **Parikshak Evaluation Engine** with the following architectural pillars:

1. **Strict Interface Contracts (v1.0)**:
   - Built on Pydantic models in `contracts/schemas.py` and `evaluation_engine/schemas.py`.
   - Inbound `ReviewSubmissionPayload` validates criteria, test summary, code packets, and metadata with `extra="forbid"`.
   - Outbound `EvaluationVerdictPayload` delivers composite score, score breakdown, criteria results, deterministic state hash, and state machine transition log.

2. **Deterministic State Machine**:
   - `INITIALIZED` $\to$ `INPUT_VALIDATED` $\to$ `GOV_OS_AUDIT` $\to$ `RULES_APPLIED` $\to$ `HASH_COMPUTED` $\to$ `VERIFIED` $\to$ `COMPLETED` (or `REJECTED`).
   - Every transition is immutably logged with source state, destination state, and causal reason.

3. **Deterministic State Hashing (SHA-256)**:
   - State hash is calculated on a canonicalized JSON serialization (sorted keys, stripped volatile clock drift).
   - Proven to generate identical SHA-256 hashes across 50 consecutive runs.

4. **Error Boundary & Exception Handling**:
   - Custom FastAPI exception handlers translate validation errors into HTTP 422 `ErrorEnvelope`.
   - Gov-OS security violations yield HTTP 400 `ErrorEnvelope`.
   - Global exception boundary catches all uncaught exceptions, preventing server crashes and eliminating unhandled 500 errors.

5. **BHIV Ecosystem Integration**:
   - **GC Shakti**: Automated policy authority scanning for forbidden patterns.
   - **Niyantran**: Zero-context-switch task assignment delivering canonical next-task specifications.
   - **Bucket**: Cryptographic evidence indexing and immutable URI generation.
   - **Gov-OS**: State ledger verification and hash replay verification.
   - **Saarthi**: Executive dashboard operational telemetry.

---

## 3. Prohibition of Forbidden Patterns
Per Gov-OS mandate, the following patterns are strictly prohibited and actively audited:
- `workflow_execution_engine`: Runtime evaluation cannot dynamically mutate execution graph logic.
- `direct_masterdb_schema_mutation`: Runtime evaluations must strictly operate read-only against the database schema; mutations must occur via versioned migration pipelines.

---

## 4. Consequences and Verification
- **Positive**: 100% test pass rate across unit, integration, negative, and determinism suites.
- **Positive**: Full compliance with Gov-OS standards and seamless BHIV ecosystem connectivity.
- **Verification**: Verified via 5-Tier test suite in `tests/` (`test_evaluation_engine_unit.py`, `test_evaluation_engine_integration.py`, `test_evaluation_negative.py`, `test_evaluation_determinism.py`).
