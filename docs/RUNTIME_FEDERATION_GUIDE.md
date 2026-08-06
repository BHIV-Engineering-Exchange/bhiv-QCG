# Runtime Federation Guide

## Participant Role
The Universal Solver Fabric and QCG operate as a *Participant* within the TANTRA runtime ecosystem. 
**Crucial Rule**: USF/QCG must never attempt to own governance or the canonical truth layer. Its sole responsibility is deterministic execution and evidence exchange.

## Joining the Federation
1. **Network Connectivity**: QCG must configure its `.env` to point to the live bucket via `BUCKET_API_URL`.
2. **Health Verification**: On startup, the gateway performs an initial `GET /docs` (or `/health`) call to ensure the Bucket is reachable.
3. **Evidence Publication**: Every completed execution sequence (Quantum input -> classical translation -> consensus) triggers an automatic background publish to the Bucket.
4. **Federation Validation**: The internal integrity of the federation is mathematically verifiable at any time by querying the `/bucket/validate-chain/{artifact_id}` endpoint.
