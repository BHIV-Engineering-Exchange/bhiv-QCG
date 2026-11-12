# VAJRA Trust & Provenance Boundary Handover (Task: BHQ-INFRA-EOD-001)

**Programme:** BHQ Sovereign Quantum Computing and Networking / BIQOS  
**Workstream:** Trust, Provenance & Integration (TANTRA–VAJRA Path)  
**Author:** **Pritesh Patra** (Trust, Provenance & Integration Lead)  
**Target Leads:** Kanishk Singh (Platform Integration Lead) & Ganesh Vishwakarma (Programme Lead)  
**Date:** Thursday, 12 November 2026  
**Status:** ✅ **SUBMISSION READY (100% VERIFIED)**

---

## 1. Response to Integration Queries

### Query 1: Exact VAJRA Service/API Endpoints & Architecture
In the sovereign BIQOS / QCG architecture, **VAJRA does not operate as an isolated, unintegrated daemon**. Instead, its trust, identity, and cryptographic provenance capabilities are exposed **directly through the unified gateway surface**:

1. **`POST /verify` (Primary Ingestion & Trust Pipeline):**
   - Ingests incoming TANTRA contracts, verifies replay validity via `CanonicalReplayAuthority`, checks producer identity in `TrustRegistry`, verifies dual-layer ECDSA P-256 signatures via `verify_contract_provenance`, executes deterministic runtime simulation, reaches Byzantine consensus, and appends the commitment to `EvidenceLedger`.
2. **`POST /gc/validate` (Constitutional Governance Validation):**
   - Applies strict constitutional policy checks against contracts without mutating state. Requires bearer authorization (`Authorization: Bearer <TOKEN>`).
3. **`GET /evidence/certificate/{execution_id}` (MDU Merkle Certificate Retrieval):**
   - Issues a canonical `DeterministicExecutionCertificate` containing the leaf hash, sequential chain hash, and global pairwise Merkle root.
4. **`GET /replay/lineage/{trace_id}` (Replay Lineage Query):**
   - Queries `CanonicalReplayAuthority` to retrieve historical monotonic sequence numbers and duplicate detection verdicts.

---

### Query 2: Contract Schema, Public Key & Auth Header Specifications

#### A. Request Payload Envelope for `POST /verify`
```json
{
  "contract": {
    "producer_type": "QUANTUM",
    "producer_id": "VAJRA_PROV_01",
    "payload": {
      "algorithm": "QAOA",
      "shots": 2048,
      "qubits": 4
    },
    "confidence": 0.995,
    "trace_id": "4fe8692c-15a0-569e-8c01-7fa29df34211",
    "contract_version": "2.0.0",
    "timestamp": "2026-11-12T18:00:00+00:00",
    "payload_hash": "SHA-256(canonical JSON of payload)",
    "execution_classification": "QUANTUM_SIMULATED",
    "execution_path": "SIMULATOR",
    "producer_signature": "<hex-encoded DER ECDSA signature of payload_hash>",
    "contract_signature": "<hex-encoded DER ECDSA signature of full deterministic contract>"
  },
  "producer_public_key": "3059301306072a8648ce3d020106082a8648ce3d03010703420004..."
}
```

#### B. Cryptographic Standards
- **Asymmetric Algorithm:** ECDSA over standard NIST P-256 curve (`secp256r1`) with SHA-256 digests.
- **Public Key Encoding:** DER-encoded `SubjectPublicKeyInfo`, serialized as lower-case hexadecimal string.
- **Signature Encoding:** Standard DER-encoded ECDSA signature $(r, s)$ hex string.
- **Authorization Header (for `/gc/validate`):** `Authorization: Bearer <VALID_TOKEN>` (returns HTTP 401 if absent or malformed).

---

## 2. Reproducible Test Evidence Summary

Verified via [`scripts/run_vajra_qcg_endpoint_validation.py`](file:///c:/Users/PRITESH/Desktop/QCG/QCG_task1/scripts/run_vajra_qcg_endpoint_validation.py) and [`tests/test_vajra_qcg_endpoint_validation.py`](file:///c:/Users/PRITESH/Desktop/QCG/QCG_task1/tests/test_vajra_qcg_endpoint_validation.py):

| Test ID | Test Case Name | Operation / Fault Injected | System Response | Outcome |
|:---:|:---|:---|:---:|:---:|
| `POS-01` | **Valid Contract Ingestion** | Full pipeline ingestion of signed contract | `flow_status: COMPLETED` | **PASS** |
| `POS-02` | **MDU Execution Certificate** | Retrieve Merkle certificate via `/evidence/certificate/{id}` | Certificate issued with Merkle root | **PASS** |
| `POS-03` | **Replay Lineage Query** | Retrieve lineage verdict via `/replay/lineage/{trace_id}` | Verdict returned (`status: VALID`) | **PASS** |
| `POS-04` | **GC Constitutional Flow** | Submit valid contract to `/gc/validate` with Bearer auth | `status: GC_APPROVED` | **PASS** |
| `NEG-01` | **Replay Duplicate Rejection** | Re-submit exact same `trace_id` | Rejected: `REPLAY_DUPLICATE` | **PASS (Rejected)** |
| `NEG-02` | **Payload Mutation Rejection** | Alter payload `shots: 1024 -> 1025` after signing | Rejected: `HALT:INVALID_SIGNATURE` | **PASS (Rejected)** |
| `NEG-03` | **Forged Signature Rejection** | Modify signature bytes (`cafebabe`) | Rejected: `HALT:INVALID_SIGNATURE` | **PASS (Rejected)** |
| `NEG-04` | **Missing Public Key Rejection** | Submit unregistered producer with empty public key | Rejected: `TRUST_REJECTED` | **PASS (Rejected)** |
| `NEG-05` | **Missing Bearer Header** | Call `/gc/validate` without Authorization header | Rejected: HTTP 401 Unauthorized | **PASS (Rejected)** |
| `NEG-06` | **Non-Existent Certificate** | Query unknown execution ID | Rejected: HTTP 404 Not Found | **PASS (Rejected)** |

---

## 3. Section 10 Formal Delivery Report

* **Task ID:** `BHQ-INFRA-EOD-001`
* **Owner:** Pritesh Patra (Trust, Provenance & Integration Lead)
* **Objective:** Validate signing, verification, trace/provenance, and evidence contracts across assigned TANTRA–VAJRA path alongside QCG's `NodeSigner`, `CanonicalReplayAuthority`, and `EvidenceLedger`.
* **Current Status:** `COMPLETED AND VERIFIED (100%)`
* **Implemented Components:**
  - `NodeSigner` & `NodeIdentity`: Asymmetric ECDSA P-256 signing without shared secrets.
  - `CanonicalReplayAuthority`: Enforces monotonic sequence numbers and stops replay attacks.
  - `EvidenceLedger`: Chained cryptographic ledger with pairwise Merkle tree authority.
  - Unified HTTP Endpoints: `/verify`, `/gc/validate`, `/evidence/certificate/{id}`, `/replay/lineage/{trace_id}`.
* **Simulation or Experiment:** Real execution on `AerSimulator` (4-qubit GHZ state, 4096 shots, 100% fidelity) and end-to-end gateway ingestion.
* **Integration Path Verified:**
  $$\text{Workload} \longrightarrow \text{TANTRA} \longrightarrow \text{QCG Gateway} \longrightarrow \mathbf{\text{VAJRA Trust}} \longrightarrow \text{Observability}$$
* **Results and Evidence:**
  - 4 Positive Integration Tests passed.
  - 6 Negative & Adversarial Rejection Tests passed (100% rejection rate).
  - Primary Evidence: [`evidence/02_PRITESH_VAJRA_ENDPOINTS_E2E.json`](file:///c:/Users/PRITESH/Desktop/QCG/QCG_task1/evidence/02_PRITESH_VAJRA_ENDPOINTS_E2E.json)
* **Assumptions:** Private keys remain in-process inside `NodeSigner`; deterministic JSON serialization with sorted keys.
* **Truth Classification:** `IMPLEMENTED AND TESTED`
* **Application Security Proof Doctrine:**
  > **Note on Ledger / Blockchain Presence:** Ledger presence alone is not application security proof. Every commitment is backed by mathematical application-level verification: ECDSA P-256 public key verification, canonical payload hashing, monotonic sequence enforcement, and Merkle inclusion proofs.

---

## 4. Short WhatsApp Message for Immediate Dispatch

```text
Hi Kanishk & Ganesh, 

Pritesh here. Workstream D (VAJRA Trust & Provenance) integration is 100% verified & submission-ready for BHQ-INFRA-EOD-001:

1. Endpoints & Protocol:
- Ingestion & Verification: POST /verify (no separate daemon needed; VAJRA trust is natively bound to QCG gateway).
- Governance Validation: POST /gc/validate (requires header: Authorization: Bearer <TOKEN>).
- MDU Certificate & Merkle Proof: GET /evidence/certificate/{execution_id}.
- Replay Lineage: GET /replay/lineage/{trace_id}.

2. Expected Contract Schema:
- Payload: ComputationExecutionContract (requires producer_id, trace_id, confidence, payload, payload_hash, producer_signature, contract_signature).
- Key Format: Hex-encoded DER SubjectPublicKeyInfo (ECDSA P-256 / SHA-256; zero shared secrets).

3. Verified Evidence (4/4 Positive, 6/6 Negative PASS):
- Positives: Valid signed contract accepted (HTTP 200 / COMPLETED), MDU certificate issued with pairwise Merkle root, replay lineage tracked.
- Negatives: Replay/duplicate trace rejected (REPLAY_DUPLICATE), payload bit-flip rejected, forged signature rejected, missing public key rejected (TRUST_REJECTED), missing auth header rejected (401).

Full JSON evidence & pytest suite pushed to:
- evidence/02_PRITESH_VAJRA_ENDPOINTS_E2E.json
- tests/test_vajra_qcg_endpoint_validation.py
- review_packets/VAJRA_TRUST_BOUNDARY_INTEGRATION_HANDOVER.md
```

