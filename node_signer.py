"""
node_signer.py — Cryptographic Node Signer and Verification Authority

Workstream D: Mechatronics, Instrumentation & Retained Cryptographic Provenance
Accountable Owner: Pritesh Patra (Lead Instrumentation Engineer & Cryptographic Provenance Architect)
Programme Identifier: BHQ-INFRA-001 (WS-D)
Subsystem: bhiv-QCG Cryptographic Provenance Engine

Canonical Implementation:
This module re-exports the unified ECDSA P-256 NodeSigner implementation from `node_identity.py`
to preserve clean backward compatibility across the QCG gateway and WS-D test suites.
"""

from node_identity import (
    NodeIdentity,
    NodeProof,
    NodeSigner,
    verify_node_proof,
)

__all__ = [
    "NodeSigner",
    "NodeIdentity",
    "NodeProof",
    "verify_node_proof",
]
