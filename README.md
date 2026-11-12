# Hybrid Quantum Communication Gateway (QCG)

A deterministic hybrid quantum/classical communication gateway built with Qiskit.
Bridges probabilistic quantum output to deterministic classical contracts.

## Architecture ..

```
TransmissionRequest
      |
      v
[Layer 1] QuantumProducer       -- Qiskit superdense coding simulation
      |
      v  QuantumDistribution
      |
[Layer 2] TranslationLayer      -- Probabilistic -> deterministic contract
      |
      v  ClassicalContract
      |
[Layer 3] QuantumGateway        -- Orchestrates devices + replay guard
      |
      v
[IndustrialEndpoint]            -- Deterministic ACK
```

### ClassicalContract schema
```json
{
  "trace_id":           "<uuid5>",
  "confidence":         0.9287,
  "decoded_message":    "NODE_READY",
  "transmission_status":"OK",
  "uncertainty_score":  0.0713,
  "contract_version":   "1.0.0"
}
```

Transmission statuses:
- `OK`       -- confidence >= 0.70, bits match
- `DEGRADED` -- confidence in [0.40, 0.70), bits match
- `REJECTED` -- confidence < 0.40, or bit mismatch (raises TranslationError)

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env   # optional: tune thresholds / log format
```

## Run

```bash
# Full gateway demo + failure tests
python hybrid_gateway.py

# Determinism proof (20 runs, exits 0 on pass, 1 on fail)
python determinism_proof.py

# Three-process pipeline demo
python process_runner.py

# Crash simulation
python process_runner.py --crash producer
python process_runner.py --crash execution
python process_runner.py --crash consensus

# Replay enforcer demo
python replay_enforcer.py

# KESHAV live integration test
python keshav_live_client.py

# Full evidence collection (KESHAV + unavailable services)
python live_integration_evidence.py
```

## Test

```bash
pytest tests/ -v  # 384 tests, 0 failures
```

## Configuration

All constants are in `config.py` and overridable via environment variables.
See `.env.example` for the full list.

## File Structure

```
# Core pipeline
config.py                  -- All constants, env-overridable
logger.py                  -- Structured JSON logger
models.py                  -- Typed, validated data models
quantum_producer.py        -- Layer 1: Qiskit quantum simulation
translation_layer.py       -- Layer 2: QuantumDistribution -> ClassicalContract
hybrid_gateway.py          -- Layers 3+4+5: Gateway, devices, failure handling
determinism_proof.py       -- Layer 6: Determinism verification (20 runs + failure injection)
tests/test_all.py          -- Full pytest suite (65 tests)
.env.example               -- Config reference
requirements.txt           -- Dependencies

# Phase 2: Trust Layer
node_identity.py           -- NodeIdentity, NodeSigner, NodeProof
provenance.py              -- Contract signing and provenance verification
consensus_simulation.py    -- Distributed consensus with signed attestations
replay_bundle.py           -- Complete execution lineage artifact
byzantine_simulation.py    -- Byzantine fault tolerance (6 cases)
audit_trail.py             -- Merkle tamper-evident audit trail
trust_chain.py             -- Chain-of-custody with NodeRegistry
determinism_doctrine.py    -- Field classification oracle

# Phase 3: Execution Infrastructure
replay_enforcer.py         -- Sequence tracking, TTL, ACCEPTED/REJECTED_DUPLICATE/REJECTED_STALE
producer_process.py        -- Independent OS process: contract production
execution_process.py       -- Independent OS process: replay enforcement + execution
consensus_process.py       -- Independent OS process: consensus verification
process_runner.py          -- Orchestrator: spawns 3 processes, crash detection
logs/process_1.log         -- Producer process evidence
logs/process_2.log         -- Execution process evidence
logs/process_3.log         -- Consensus process evidence

# Communication Layer
communication_contract.py  -- CommunicationRequest, TranslationContract, AcknowledgementContract, CommunicationResponse
gateway.py                 -- Producer-agnostic CommunicationGateway (Q/C/H → same send())
simulation.py              -- All 4 cross-system paths (Q→C, C→Q, H→C, H→Q)

# Semantic & Authority Layer
semantic_registry.py       -- 12 canonical term definitions
governance_authority.py    -- Explicit authority declarations for GovernanceLayer, RuntimeCore, TraceStore
participation_proof.py     -- Bytecode-level proof of identical execution path across producer types
ecosystem_participation.py -- 6 ecosystem participants through universal trust pipeline
runtime_demo.py            -- Full 6-phase demonstration

# Live Ecosystem Integration
keshav_live_client.py      -- Production HTTP client for live KESHAV API
pritesh_live_client.py     -- Production HTTP client to simulate Pritesh payload to web server
web_server.py              -- Local web server endpoint to ingest Pritesh payloads at /verify
live_integration_evidence.py -- Evidence collection script for all live integrations
integration_harness.py     -- TANTRA pipeline harness with KESHAV live integration

# Handover documents
ARCHITECTURE.md            -- System architecture reference
DEPLOYMENT_GUIDE.md        -- Docker/K8s deployment instructions
ECOSYSTEM_INTEGRATION.md   -- Ecosystem federation status (live vs pending)
OPERATIONAL_RUNBOOK.md     -- On-call troubleshooting guide
HANDOVER.md                -- Final system state and developer handover
review_packets/            -- Review packet with evidence and code packets
```

## BHQ-INFRA-EOD-001 Integration & Handover

### External Ecosystem Clients & Env Configuration
All live ecosystem connectors are configured in `config.py` and `.env.example`:
- `QCG_KESHAV_API_URL` (default `https://keshav-cia7.onrender.com`), `QCG_KESHAV_ENABLED`
- `QCG_PRANA_API_URL` (default `http://163.128.209.18:8103`), `QCG_PRANA_TIMEOUT_SECONDS` (`40`), `QCG_PRANA_ENABLED`
- `QCG_BUCKET_API_URL` (default `https://bhiv-bucket-i1l6.onrender.com`), `QCG_BUCKET_ENABLED`
- `QCG_GANESH_API_URL` (default `https://bhiv-quantum-application-layer.onrender.com`), `QCG_GANESH_ENABLED`
- `QCG_VAJRA_API_URL` (default `https://vajra.blackholeinfiverse.com`), `QCG_VAJRA_TIMEOUT_SECONDS` (`15`), `QCG_VAJRA_ENABLED`, and `VAJRA_TANTRA_SECRET` (set out-of-band; never commit secrets)

### Reproducible Verification Commands
```bash
# Full regression + integration test suite (758 passed, 8 warnings on Python 3.11.9)
python -m pytest tests/ -v

# Targeted VAJRA + WS-C + discovery + harness suites
python -m pytest tests/test_vajra_integration.py tests/test_ws_c_tantra_vajra_integration.py tests/test_platform_service_registration.py tests/test_integration_harness.py -v

# Quick VAJRA health check
python -c "from vajra_client import VajraClient; print(VajraClient().health())"
```

### Known Limitations & External Dependencies
- Quantum execution uses Qiskit `AerSimulator` (`SIMULATED AND TESTED`); physical QPU execution remains `BLOCKED (MQR-01)`.
- VAJRA `/api/health` and `/api/tantra/chain-integrity` are live (`200 OK`, note `/health` returns `404`); authenticated provenance writes (`POST /api/vajra/provenance/retrieval`) fail closed (`401`) without `VAJRA_TANTRA_SECRET` (`REQUIRES_EXTERNAL_ACCESS`).
- Standalone `runtime_core.py` calls `PlatformCapabilitySDK` against `http://127.0.0.1:9010` (`start_platform_servers.py`) unless `PYTEST_CURRENT_TEST=1` is set.
- `web_server.py` `/gc/validate` checks for a `Bearer ` header prefix and forwards to `TANTRAIntegrationHarness` (mutating replay/ledger state without parsing RS256 JWT claims); `/evidence/{hashed_trace}` returns a placeholder proof while `/evidence/certificate/{execution_id}` and `/evidence/trace/{trace_id}` use `EvidenceLedger`.
- Bucket (`https://bhiv-bucket-i1l6.onrender.com/health` `503`, `:8012` timeout) and Marine Quantum Runtime `X-API-Key` remain externally blocked.

### Rollback
1. Disable external connectors without code changes by setting `QCG_VAJRA_ENABLED=false` (and/or `QCG_PRANA_ENABLED=false`, `QCG_KESHAV_ENABLED=false`) in `.env` and restarting `web_server.py` (or `kubectl rollout undo deployment/qcg-service`).
2. Or revert code changes via `git revert <commit_sha>` and re-run `python -m pytest tests/ -v`.

### Next Three Tasks After EOD
1. **Integration hardening and defect closure** (provision `VAJRA_TANTRA_SECRET` & MQR `RUNTIME_API_KEY`, restore Bucket, align `/gc/validate` JWT & read-only behavior, replace `/evidence/{hashed_trace}` mock).
2. **Parikshak workflow automation validation** (live `task -> submission -> evidence review -> decision -> next task`).
3. **BIQOS ecosystem convergence map and release plan** (map verified capabilities to owners/interfaces and define the next increment).