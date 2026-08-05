"""
sdk_auth.py — SDK Authentication Helpers

Provides SDK-side authentication header construction and response
signature verification. Works with any TrustProvider implementation.

RESPONSIBILITY BOUNDARY
-----------------------
SDKAuthenticator OWNS:
    - Building authentication headers for outgoing requests
    - Verifying response signatures from servers

SDKAuthenticator does NOT OWN:
    - Trust provider implementation   → quantum_trust_provider.py
    - Certificate management          → service_identity.py
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, Optional

from quantum_trust_provider import TrustProvider, ClassicalTrustProvider, KeyPairResult


class SDKAuthenticator:
    """
    SDK-side authentication for outgoing requests and incoming responses.

    Uses a TrustProvider for all cryptographic operations, ensuring
    that trust level migration (classical → PQ → hybrid) requires
    no code changes in the SDK consumer.
    """

    def __init__(
        self,
        service_id: str,
        trust_provider: TrustProvider = None,
    ):
        self.service_id = service_id
        self._provider = trust_provider or ClassicalTrustProvider()
        self._keypair: Optional[KeyPairResult] = None

    def initialise(self):
        """Generate the SDK's own identity keypair."""
        self._keypair = self._provider.generate_key_pair()

    @property
    def public_key(self) -> bytes:
        if not self._keypair:
            self.initialise()
        return self._keypair.public_key

    @property
    def public_key_hex(self) -> str:
        return self.public_key.hex()

    def build_auth_headers(self, request_payload: dict) -> Dict[str, str]:
        """
        Build authentication headers for an outgoing request.

        Returns headers:
        - X-Service-ID: the SDK's service identity
        - X-Service-Signature: signature over the request payload
        - X-Service-PublicKey: hex-encoded public key
        - X-Trust-Level: current trust level
        """
        if not self._keypair:
            self.initialise()

        payload_bytes = json.dumps(request_payload, sort_keys=True, default=str).encode()
        signature = self._provider.sign(payload_bytes, self._keypair.private_key_handle)

        return {
            "X-Service-ID": self.service_id,
            "X-Service-Signature": signature.hex(),
            "X-Service-PublicKey": self._keypair.public_key.hex(),
            "X-Trust-Level": self._provider.trust_level(),
        }

    def verify_response_signature(
        self,
        response_body: dict,
        signature_hex: str,
        server_public_key_hex: str,
    ) -> bool:
        """
        Verify a response signature from a server.

        Returns True if the server's signature over the response
        body is valid for the given public key.
        """
        try:
            response_bytes = json.dumps(response_body, sort_keys=True, default=str).encode()
            signature = bytes.fromhex(signature_hex)
            server_pub = bytes.fromhex(server_public_key_hex)
            return self._provider.verify(response_bytes, signature, server_pub)
        except Exception:
            return False

    def sign_payload(self, payload: dict) -> str:
        """Sign a payload and return the hex-encoded signature."""
        if not self._keypair:
            self.initialise()
        payload_bytes = json.dumps(payload, sort_keys=True, default=str).encode()
        sig = self._provider.sign(payload_bytes, self._keypair.private_key_handle)
        return sig.hex()
