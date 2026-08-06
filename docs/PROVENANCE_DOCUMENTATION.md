# Provenance Documentation

## Cryptographic Lineage
Provenance ensures every computation executed within the USF/QCG can be traced back to its origin with mathematical certainty. When integrated with the Live Bucket, provenance metadata moves from local isolated storage into the canonical evidence chain.

## Workflow
1. **Signing**: A producer generates a probabilistic quantum outcome and signs the deterministic translation using ECDSA.
2. **Local Registry Verification**: `ProducerVerificationLayer` ensures the signature is valid and the producer is registered with proper capabilities.
3. **Bucket Archival**: The resulting `ComputationExecutionContract`, along with its signature and `trace_id`, is embedded into the `payload` field of the Evidence Exchange schema.
4. **Independent Verification**: Any third-party can query `/bucket/artifact/{artifact_id}` to retrieve the artifact, extract the public key and signature, and independently verify the computation without trusting the USF orchestrator.

## Cross-System Trust
By publishing provenance to the Bucket, the trust domain extends beyond the local QCG instance to any system federated with the TANTRA runtime.
