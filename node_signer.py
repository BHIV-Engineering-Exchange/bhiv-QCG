"""
node_signer.py — Cryptographic Node Signer and Verification Authority

Workstream D: Mechatronics, Instrumentation & Retained Cryptographic Provenance
Accountable Owner: Pritesh Patra (Lead Instrumentation Engineer & Cryptographic Provenance Architect)
Programme Identifier: BHQ-INFRA-001 (WS-D)
Subsystem: bhiv-QCG Cryptographic Provenance Engine

Provides:
- ECDSA P-256 (secp256r1) keypair generation and secure lifecycle.
- Cryptographic payload digest signing and DER signature serialization.
- Public key PEM and DER hex export.
- Signature verification against arbitrary payloads and hashes.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.utils import (
    decode_dss_signature,
    encode_dss_signature,
)

# Re-export core identity dataclasses
from node_identity import NodeIdentity, NodeProof, verify_node_proof


class NodeSigner:
    """
    ECDSA P-256 signer. Generates a fresh key pair on construction.
    The private key is held strictly in memory and never leaves this instance.
    """

    def __init__(
        self,
        node_id: str,
        node_role: str = "EXECUTION_NODE",
        version: str = "1.0.0",
    ):
        self._private_key = ec.generate_private_key(ec.SECP256R1())
        pub_der = self._private_key.public_key().public_bytes(
            encoding=serialization.Encoding.DER,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        self._public_key_hex = pub_der.hex()

        self.identity = NodeIdentity(
            node_id=node_id,
            public_key=self._public_key_hex,
            node_role=node_role,
            version=version,
        )

    @property
    def node_id(self) -> str:
        return self.identity.node_id

    @property
    def public_key_hex(self) -> str:
        return self._public_key_hex

    def get_public_key_pem(self) -> str:
        """Export the public key in standard PEM format."""
        return self._private_key.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        ).decode("utf-8")

    def sign_payload(self, payload: dict | str) -> NodeProof:
        """
        Signs a canonicalized payload string or dictionary with SHA-256 and ECDSA P-256.
        Returns a NodeProof containing node_id, hex DER signature, and signed_hash.
        """
        payload_str = (
            json.dumps(payload, sort_keys=True, default=str)
            if isinstance(payload, dict)
            else str(payload)
        )
        payload_bytes = payload_str.encode("utf-8")
        payload_hash = hashlib.sha256(payload_bytes).hexdigest()

        # Sign over canonical payload bytes
        sig_bytes = self._private_key.sign(
            payload_bytes,
            ec.ECDSA(hashes.SHA256()),
        )
        return NodeProof(
            node_id=self.identity.node_id,
            signature=sig_bytes.hex(),
            signed_hash=payload_hash,
        )

    def sign_digest(self, digest: bytes) -> bytes:
        """Sign a precomputed raw 32-byte digest directly."""
        return self._private_key.sign(
            digest,
            ec.ECDSA(hashes.SHA256()),
        )


__all__ = [
    "NodeSigner",
    "NodeIdentity",
    "NodeProof",
    "verify_node_proof",
]

