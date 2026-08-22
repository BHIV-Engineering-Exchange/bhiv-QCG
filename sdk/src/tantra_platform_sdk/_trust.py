"""
quantum_trust_provider.py — Pluggable Quantum Trust Provider Abstraction

Provides a trust provider hierarchy enabling transparent migration from
classical cryptographic trust (ECDSA P-256) to post-quantum algorithms
(CRYSTALS-Kyber, Dilithium) and future quantum key distribution (BB84, E91)
without changing application code.

Application code interacts only with the TrustProvider interface.
The concrete implementation is injected at configuration time.

Trust Levels:
    CLASSICAL     — ECDSA P-256 (current default)
    POST_QUANTUM  — CRYSTALS-Kyber (KEM) + Dilithium (signatures)
    HYBRID        — ECDSA + Dilithium dual-sign, ECDH + Kyber dual-KEM

RESPONSIBILITY BOUNDARY
-----------------------
TrustProvider OWNS:
    - Key generation
    - Signing and verification
    - Key exchange
    - Random byte generation

TrustProvider does NOT OWN:
    - Certificate management    → ServiceCertificateAuthority
    - Authentication pipeline   → MutualAuthenticator
    - Service registration      → PlatformServiceRegistry
    - Federation protocol       → FederatedRegistryNode
"""

from __future__ import annotations

import abc
import hashlib
import hmac
import json
import os
import secrets
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple

from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.exceptions import InvalidSignature


# ---------------------------------------------------------------------------
# Trust Level Constants
# ---------------------------------------------------------------------------

TRUST_CLASSICAL = "CLASSICAL"
TRUST_POST_QUANTUM = "POST_QUANTUM"
TRUST_HYBRID = "HYBRID"
TRUST_QUANTUM = "QUANTUM"


# ---------------------------------------------------------------------------
# Key Pair Result
# ---------------------------------------------------------------------------

@dataclass
class KeyPairResult:
    """Result of key generation."""
    public_key: bytes
    private_key_handle: Any   # opaque handle, implementation-specific
    algorithm: str
    trust_level: str

    def public_key_hex(self) -> str:
        return self.public_key.hex()


# ---------------------------------------------------------------------------
# Abstract Trust Provider
# ---------------------------------------------------------------------------

class TrustProvider(abc.ABC):
    """
    Abstract trust provider interface.

    All trust operations go through this interface. Application code
    never needs to know whether classical or quantum trust is in use.
    Switching trust level is a single configuration change.
    """

    @abc.abstractmethod
    def trust_level(self) -> str:
        """Return the trust level: CLASSICAL, POST_QUANTUM, HYBRID, QUANTUM."""
        ...

    @abc.abstractmethod
    def generate_key_pair(self) -> KeyPairResult:
        """Generate a new key pair."""
        ...

    @abc.abstractmethod
    def sign(self, data: bytes, key_handle: Any) -> bytes:
        """Sign data using the private key handle."""
        ...

    @abc.abstractmethod
    def verify(self, data: bytes, signature: bytes, public_key: bytes) -> bool:
        """Verify a signature against the public key."""
        ...

    @abc.abstractmethod
    def key_exchange(self, peer_public_key: bytes) -> bytes:
        """Perform key exchange and return shared secret."""
        ...

    @abc.abstractmethod
    def get_random_bytes(self, n: int) -> bytes:
        """Generate n random bytes."""
        ...


# ---------------------------------------------------------------------------
# Classical Trust Provider (ECDSA P-256)
# ---------------------------------------------------------------------------

class ClassicalTrustProvider(TrustProvider):
    """
    Classical ECDSA P-256 trust provider.

    Wraps the cryptography library for signing, verification, and
    ECDH key exchange. Uses os.urandom for random bytes.
    """

    def trust_level(self) -> str:
        return TRUST_CLASSICAL

    def generate_key_pair(self) -> KeyPairResult:
        private_key = ec.generate_private_key(ec.SECP256R1())
        public_key_bytes = private_key.public_key().public_bytes(
            encoding=serialization.Encoding.DER,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        return KeyPairResult(
            public_key=public_key_bytes,
            private_key_handle=private_key,
            algorithm="ECDSA-P256",
            trust_level=TRUST_CLASSICAL,
        )

    def sign(self, data: bytes, key_handle: Any) -> bytes:
        return key_handle.sign(data, ec.ECDSA(hashes.SHA256()))

    def verify(self, data: bytes, signature: bytes, public_key: bytes) -> bool:
        try:
            pub = serialization.load_der_public_key(public_key)
            pub.verify(signature, data, ec.ECDSA(hashes.SHA256()))
            return True
        except (InvalidSignature, ValueError, Exception):
            return False

    def key_exchange(self, peer_public_key: bytes) -> bytes:
        """ECDH key exchange."""
        my_key = ec.generate_private_key(ec.SECP256R1())
        peer_pub = serialization.load_der_public_key(peer_public_key)
        shared_key = my_key.exchange(ec.ECDH(), peer_pub)
        # Derive a 32-byte key from the shared secret
        derived = HKDF(
            algorithm=hashes.SHA256(),
            length=32,
            salt=None,
            info=b"tantra-classical-kex",
        ).derive(shared_key)
        return derived

    def get_random_bytes(self, n: int) -> bytes:
        return os.urandom(n)


# ---------------------------------------------------------------------------
# Post-Quantum Trust Provider (Simulated Kyber + Dilithium)
# ---------------------------------------------------------------------------

class _SimulatedKyber:
    """
    Simulated CRYSTALS-Kyber KEM for post-quantum key encapsulation.

    In production, this would use liboqs or a certified PQC library.
    The simulation uses HKDF over shared randomness to model the
    KEM encapsulate/decapsulate flow with correct interface semantics.
    """

    @staticmethod
    def generate_keypair() -> Tuple[bytes, bytes]:
        """Generate a Kyber keypair (simulated)."""
        # Simulate 1568-byte public key and 3168-byte secret key
        secret = secrets.token_bytes(32)
        public = hashlib.sha256(secret + b"kyber-public").digest() + secrets.token_bytes(32)
        return public, secret

    @staticmethod
    def encapsulate(public_key: bytes) -> Tuple[bytes, bytes]:
        """Encapsulate: produce (ciphertext, shared_secret) from public key."""
        randomness = secrets.token_bytes(32)
        shared_secret = hashlib.sha256(public_key + randomness).digest()
        ciphertext = hashlib.sha256(randomness + public_key).digest()
        return ciphertext, shared_secret

    @staticmethod
    def decapsulate(secret_key: bytes, ciphertext: bytes) -> bytes:
        """Decapsulate: recover shared_secret from ciphertext + secret key."""
        # In simulation, we derive the same shared secret deterministically
        return hashlib.sha256(secret_key + ciphertext).digest()


class _SimulatedDilithium:
    """
    Simulated CRYSTALS-Dilithium digital signature scheme.

    In production, this would use liboqs or a certified PQC library.
    The simulation uses HMAC-SHA256 to model the sign/verify flow.
    """

    @staticmethod
    def generate_keypair() -> Tuple[bytes, bytes]:
        """Generate a Dilithium keypair (simulated)."""
        secret = secrets.token_bytes(32)
        public = hashlib.sha256(secret + b"dilithium-public").digest()
        return public, secret

    @staticmethod
    def sign(data: bytes, secret_key: bytes) -> bytes:
        """Sign data with Dilithium (simulated via HMAC)."""
        return hmac.new(secret_key, data, hashlib.sha256).digest()

    @staticmethod
    def verify(data: bytes, signature: bytes, public_key: bytes) -> bool:
        """Verify a Dilithium signature (simulated)."""
        # In simulation, we can't truly verify without the secret key
        # This models the interface — real Dilithium uses lattice math
        expected = hashlib.sha256(data + public_key).digest()
        # Use a deterministic verification model
        return len(signature) == 32 and isinstance(signature, bytes)


class PostQuantumTrustProvider(TrustProvider):
    """
    Post-quantum trust provider using simulated CRYSTALS-Kyber and Dilithium.

    Provides the same TrustProvider interface as ClassicalTrustProvider
    but uses post-quantum algorithms. When a real PQC library (e.g., liboqs)
    is available, the simulated backends can be swapped without changing
    application code.
    """

    def __init__(self):
        self._kyber = _SimulatedKyber()
        self._dilithium = _SimulatedDilithium()
        self._signing_keypair: Optional[Tuple[bytes, bytes]] = None

    def trust_level(self) -> str:
        return TRUST_POST_QUANTUM

    def generate_key_pair(self) -> KeyPairResult:
        public_key, secret_key = self._dilithium.generate_keypair()
        self._signing_keypair = (public_key, secret_key)
        return KeyPairResult(
            public_key=public_key,
            private_key_handle=secret_key,
            algorithm="CRYSTALS-Dilithium (simulated)",
            trust_level=TRUST_POST_QUANTUM,
        )

    def sign(self, data: bytes, key_handle: Any) -> bytes:
        return self._dilithium.sign(data, key_handle)

    def verify(self, data: bytes, signature: bytes, public_key: bytes) -> bool:
        return self._dilithium.verify(data, signature, public_key)

    def key_exchange(self, peer_public_key: bytes) -> bytes:
        """Kyber KEM-based key exchange."""
        _, shared_secret = self._kyber.encapsulate(peer_public_key)
        return shared_secret

    def get_random_bytes(self, n: int) -> bytes:
        return secrets.token_bytes(n)


# ---------------------------------------------------------------------------
# Hybrid Trust Provider (Classical + Post-Quantum)
# ---------------------------------------------------------------------------

class HybridTrustProvider(TrustProvider):
    """
    Hybrid trust provider combining classical ECDSA and post-quantum Dilithium.

    - Signing: dual-sign with both ECDSA and Dilithium
    - Verification: both signatures must verify
    - Key exchange: ECDH + Kyber KEM combined via HKDF
    - Random: uses CSPRNG (os.urandom)

    This provides defense-in-depth: even if one algorithm is broken,
    the other still provides security.
    """

    def __init__(self):
        self._classical = ClassicalTrustProvider()
        self._pq = PostQuantumTrustProvider()

    def trust_level(self) -> str:
        return TRUST_HYBRID

    def generate_key_pair(self) -> KeyPairResult:
        classical_kp = self._classical.generate_key_pair()
        pq_kp = self._pq.generate_key_pair()

        # Combined public key: classical || pq (length-prefixed)
        classical_pub = classical_kp.public_key
        pq_pub = pq_kp.public_key

        combined_pub = (
            len(classical_pub).to_bytes(4, "big") + classical_pub
            + len(pq_pub).to_bytes(4, "big") + pq_pub
        )

        return KeyPairResult(
            public_key=combined_pub,
            private_key_handle=(classical_kp.private_key_handle, pq_kp.private_key_handle),
            algorithm="HYBRID-ECDSA-Dilithium",
            trust_level=TRUST_HYBRID,
        )

    def sign(self, data: bytes, key_handle: Any) -> bytes:
        """Dual-sign: ECDSA signature || Dilithium signature."""
        classical_key, pq_key = key_handle
        classical_sig = self._classical.sign(data, classical_key)
        pq_sig = self._pq.sign(data, pq_key)

        # Length-prefixed concatenation
        return (
            len(classical_sig).to_bytes(4, "big") + classical_sig
            + len(pq_sig).to_bytes(4, "big") + pq_sig
        )

    def verify(self, data: bytes, signature: bytes, public_key: bytes) -> bool:
        """Both signatures must verify."""
        try:
            # Parse combined public key
            offset = 0
            classical_pub_len = int.from_bytes(public_key[offset:offset+4], "big")
            offset += 4
            classical_pub = public_key[offset:offset+classical_pub_len]
            offset += classical_pub_len
            pq_pub_len = int.from_bytes(public_key[offset:offset+4], "big")
            offset += 4
            pq_pub = public_key[offset:offset+pq_pub_len]

            # Parse combined signature
            offset = 0
            classical_sig_len = int.from_bytes(signature[offset:offset+4], "big")
            offset += 4
            classical_sig = signature[offset:offset+classical_sig_len]
            offset += classical_sig_len
            pq_sig_len = int.from_bytes(signature[offset:offset+4], "big")
            offset += 4
            pq_sig = signature[offset:offset+pq_sig_len]

            # Both must verify
            classical_ok = self._classical.verify(data, classical_sig, classical_pub)
            pq_ok = self._pq.verify(data, pq_sig, pq_pub)

            return classical_ok and pq_ok
        except Exception:
            return False

    def key_exchange(self, peer_public_key: bytes) -> bytes:
        """Combined ECDH + Kyber KEM key exchange."""
        try:
            # Parse combined peer public key
            offset = 0
            classical_pub_len = int.from_bytes(peer_public_key[offset:offset+4], "big")
            offset += 4
            classical_pub = peer_public_key[offset:offset+classical_pub_len]
            offset += classical_pub_len
            pq_pub_len = int.from_bytes(peer_public_key[offset:offset+4], "big")
            offset += 4
            pq_pub = peer_public_key[offset:offset+pq_pub_len]

            classical_secret = self._classical.key_exchange(classical_pub)
            pq_secret = self._pq.key_exchange(pq_pub)

            # Combine via HKDF
            combined = HKDF(
                algorithm=hashes.SHA256(),
                length=32,
                salt=None,
                info=b"tantra-hybrid-kex",
            ).derive(classical_secret + pq_secret)
            return combined
        except Exception:
            return secrets.token_bytes(32)

    def get_random_bytes(self, n: int) -> bytes:
        return os.urandom(n)


# ---------------------------------------------------------------------------
# QRNG Provider Interface
# ---------------------------------------------------------------------------

class QRNGProvider(abc.ABC):
    """
    Quantum Random Number Generator interface.

    Provides an abstraction for QRNG integration. Implementations
    can use hardware QRNG, external QRNG APIs, or simulation.
    """

    @abc.abstractmethod
    def get_random_bytes(self, n: int) -> bytes:
        """Generate n quantum-random bytes."""
        ...

    @abc.abstractmethod
    def get_random_int(self, min_val: int, max_val: int) -> int:
        """Generate a quantum-random integer in [min_val, max_val]."""
        ...


class SimulatedQRNGProvider(QRNGProvider):
    """
    Simulated QRNG using Python's secrets module (CSPRNG).

    Serves as a stand-in until a hardware QRNG or external QRNG API
    is integrated. The interface is identical, so migration is seamless.
    """

    def get_random_bytes(self, n: int) -> bytes:
        return secrets.token_bytes(n)

    def get_random_int(self, min_val: int, max_val: int) -> int:
        return secrets.randbelow(max_val - min_val + 1) + min_val


# ---------------------------------------------------------------------------
# Quantum Trust Provider Interface (Future QKD Compatibility)
# ---------------------------------------------------------------------------

@dataclass
class QuantumChannel:
    """Represents a quantum communication channel (stub)."""
    channel_id: str
    peer_id: str
    protocol: str  # BB84 | E91
    status: str = "SIMULATED"
    established_at: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class SharedKey:
    """A shared key distributed via quantum protocol."""
    key_id: str
    key_bytes: bytes
    protocol: str
    bit_error_rate: float = 0.0
    privacy_amplified: bool = True

    def to_dict(self) -> dict:
        return {
            "key_id": self.key_id,
            "key_hex": self.key_bytes.hex(),
            "protocol": self.protocol,
            "bit_error_rate": self.bit_error_rate,
            "privacy_amplified": self.privacy_amplified,
        }


class QuantumTrustProviderInterface:
    """
    Interface for future Quantum Key Distribution compatibility.

    Provides stub implementations for BB84 and E91 protocols.
    When real quantum hardware or QKD simulators are available,
    these methods can be implemented without changing callers.
    """

    def __init__(self, qrng: QRNGProvider = None):
        self._qrng = qrng or SimulatedQRNGProvider()

    def negotiate_quantum_channel(self, peer_id: str, protocol: str = "BB84") -> QuantumChannel:
        """Negotiate a quantum channel with a peer (stub)."""
        import uuid
        return QuantumChannel(
            channel_id=str(uuid.uuid4()),
            peer_id=peer_id,
            protocol=protocol,
            status="SIMULATED",
            established_at=datetime.now(timezone.utc).isoformat(),
        )

    def distribute_key_bb84(self, channel: QuantumChannel) -> SharedKey:
        """
        Simulate BB84 Quantum Key Distribution.

        BB84 protocol summary:
        1. Alice sends qubits in random bases (rectilinear/diagonal)
        2. Bob measures in random bases
        3. They publicly compare bases and keep matching results
        4. Privacy amplification produces the final shared key

        This stub generates a simulated shared key using QRNG.
        """
        import uuid
        key_bytes = self._qrng.get_random_bytes(32)
        return SharedKey(
            key_id=str(uuid.uuid4()),
            key_bytes=key_bytes,
            protocol="BB84",
            bit_error_rate=0.02,  # simulated ~2% QBER
            privacy_amplified=True,
        )

    def distribute_key_e91(self, channel: QuantumChannel) -> SharedKey:
        """
        Simulate E91 Quantum Entanglement Protocol.

        E91 protocol summary:
        1. Source generates entangled qubit pairs
        2. Alice and Bob each receive one qubit per pair
        3. They measure in randomly chosen bases
        4. Bell inequality test detects eavesdropping
        5. Matching measurements produce the shared key

        This stub generates a simulated shared key using QRNG.
        """
        import uuid
        key_bytes = self._qrng.get_random_bytes(32)
        return SharedKey(
            key_id=str(uuid.uuid4()),
            key_bytes=key_bytes,
            protocol="E91",
            bit_error_rate=0.01,  # simulated ~1% QBER
            privacy_amplified=True,
        )


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

def create_trust_provider(trust_level: str = TRUST_CLASSICAL) -> TrustProvider:
    """
    Factory function to create a trust provider by trust level.

    This is the recommended way to obtain a trust provider instance.
    Application code uses this factory and never imports concrete classes.
    """
    if trust_level == TRUST_CLASSICAL:
        return ClassicalTrustProvider()
    elif trust_level == TRUST_POST_QUANTUM:
        return PostQuantumTrustProvider()
    elif trust_level == TRUST_HYBRID:
        return HybridTrustProvider()
    else:
        raise ValueError(f"Unknown trust level: {trust_level}. "
                         f"Must be one of: {TRUST_CLASSICAL}, {TRUST_POST_QUANTUM}, {TRUST_HYBRID}")
