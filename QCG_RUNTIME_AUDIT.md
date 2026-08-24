# Ecosystem Convergence Audit: QCG (Execution Provenance)

## 1. LIVE
* **URL/IP:** `0.0.0.0:8080` (or `localhost:8080`)
* **Service/Location:** Configured via `docker-compose.yml` and `deployment.yaml`. Runs natively via FastAPI/Uvicorn (`web_server.py`) exposing HTTP REST endpoints.

## 2. E2E PROOF
* **Verified Path:** Real execution path is verified via `smoke_test_live.py`. Contract is processed via `POST /verify` → `ReplayVerifierInterface` → `TrustVerifierInterface` (ECDSA) → `ExecutionValidatorInterface` → `ConsensusVerifierInterface` → Returns structured `trace_continuity` (`sequence_number`, `runtime_hash`, `final_hash`).
* **Trace evidence:** Securely appended to Merkle Audit Trail, retrievable via `/evidence/{hash}` and `/replay/lineage/{trace_id}`.

## 3. INTEGRATION
* **Connected:** KESHAV live `/analyze` endpoint integration is built and `opentelemetry-python` telemetry is active.
* **MOCKS/SIMULATIONS (Explicitly Noted):**
  * **Consensus:** Byzantine consensus is *simulated* using a 3-node mock due to the lack of live adjacent TANTRA peers.
  * **Dhiraj Runtime:** `DhirajRuntimeClient` attempts live HTTP POST to `.local` network, but gracefully fails-over to simulated runtime data.
  * **KESHAV Authentication:** Uses a pseudo token (`VALID_GC_TOKEN`) to bypass authenticated routing; real public RSA/ECDSA key sync is not yet implemented.

## 4. PROJECT STATE
* **QCG / TANTRA Ecosystem Participant Handover**
  * **Completed:** Transitioned from simulation to real API participant. Live GC governance validation flows (`/gc/validate`), node ECDSA signing, and load testing benchmarking completed.
  * **Updates in Process:** Resolving hardcoded dependency URLs and migrating from transient memory to permanent ledger storage.

## 5. PRODUCTION
* **Accessibility:** No Vercel/Render. Accessible internally or via local Docker. 
* **Health Checks:** Functional APIs at `/health` and `/health/live`.
* **Persistence (DISCONNECTED/LOCAL ONLY):** The `EvidenceLedger` uses transient memory/tmp dicts. Data will **NOT** survive system restarts yet.

## 6. GAPS/BLOCKERS
* **Network Address:** Need real production FQDN for Dhiraj Runtime passed via Env Vars (currently points to `.local`). *(Owner: Pritesh)*
* **Auth Key:** Live public key sync (JWKs) is required to replace the KESHAV bypass token. *(Owner: Pritesh)*
* **Persistent Ledger:** Transient memory storage lacks a bind to a true Block Store/LevelDB volume. *(Owner: Pritesh)*

## 7. AI TOOLS
* Google/Deepmind Antigravity (Enterprise) for codebase analysis, integration testing, and execution tracking compilation.

## 8. NEXT 3
1. Sync real public keys for KESHAV Provider Auth.
2. Configure a persistent volume (RocksDB/LevelDB) for `EvidenceLedger` to ensure continuity across restarts.
3. Replace hardcoded `.local` addresses with deterministic dynamic Environment Variables. 

## 9. Subscriptions
* Google/Deepmind Enterprise AI ecosystem.
