# Deployment Guide: Quantum Communication Gateway (QCG) & Universal Solver Fabric (USF)

This repository is fully configured for a 1-click deployment on Render.com as a comprehensive **Monolithic** platform.

By deploying via the `render.yaml` Blueprint, Render will automatically spin up the entire ecosystem on a single Web Service. This combines the QCG Core and the External Runtime execution modules, automatically preventing endpoint collisions through namespacing.

## Ecosystem Architecture (Namespaced Monolith)

### 1. CORE: The QCG Gateway (`/qcg`)
The main authoritative gateway for the platform. It acts as the primary ingestion pipeline for BHIV contracts from Pravah/NICAI. It is the lead orchestrator of the ecosystem.

### 2. PLUGIN: USF External Quantum Node (`/external`)
A domain-specific quantum execution node integrated into the Universal Solver Fabric. It utilizes a non-intrusive platform agent to dynamically register its capabilities and endpoints with the core QCG registries. 

---

## How to Deploy (1-Click Blueprint)

1. Push this entire codebase to a GitHub repository.
2. Go to the [Render Dashboard](https://dashboard.render.com).
3. Click **New** -> **Blueprint**.
4. Connect your GitHub repository.
5. Render will automatically detect the `render.yaml` file and deploy the Monolith!

## Testing Your Live Platform

Once Render assigns your public URL (e.g., `https://tantra-platform-monolith.onrender.com`), you can verify the ecosystem integration:

### 1. Core QCG Gateway (Lead)
- **Check Platform Health:**
  ```bash
  curl https://tantra-platform-monolith.onrender.com/qcg/health/live
  ```
- **Ingest Execution Contract:**
  ```bash
  curl -X POST https://tantra-platform-monolith.onrender.com/qcg/verify \
    -H "Content-Type: application/json" \
    -d '{"contract": {"producer_type": "QUANTUM"}, "producer_public_key": "..."}'
  ```

### 2. USF Quantum Node (External Integration)
- **Trigger USF Registration Sync:**
  ```bash
  curl -X POST https://tantra-platform-monolith.onrender.com/external/platform/integrate
  ```
- **Direct Node Execution:**
  ```bash
  curl -X POST https://tantra-platform-monolith.onrender.com/external/execute \
    -H "Content-Type: application/json" \
    -d '{"trace_id": "test-123", "producer_type": "QUANTUM", "payload": {}, "confidence": 0.85}'
  ```
### 3. Capability Registry (SANSKAR Integration)
- **Check Capabilities:**
  ```bash
  curl https://tantra-platform-monolith.onrender.com/registry/capabilities/capabilities
  ```

### 4. Platform Discovery (SANSKAR Integration)
- **Register Service:**
  ```bash
  curl -X POST https://tantra-platform-monolith.onrender.com/registry/platform/v1/register \
    -H "Content-Type: application/json" \
    -d '{"service_id": "TEST", "service_name": "Test Service", "version": "1.0", "endpoints": {}}'
  ```
