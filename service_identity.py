"""
service_identity.py — Service Certificate Authority & Mutual Authentication

Provides per-service cryptographic identity for the Secure Federated
Capability Fabric. Every service that registers must present a valid
certificate issued by the registry's Certificate Authority.

RESPONSIBILITY BOUNDARY
-----------------------
ServiceCertificateAuthority OWNS:
    - Certificate issuance
    - Certificate revocation (CRL management)
    - Certificate verification

MutualAuthenticator OWNS:
    - Registration authentication pipeline
    - Proof + certificate + identity cross-validation

Neither component owns:
    - Service registration logic       → PlatformServiceRegistry
    - Federation synchronisation       → FederatedRegistryNode
    - Lifecycle transitions            → LifecycleManager
"""

from __future__ import annotations

import hashlib
import json
import secrets
import threading
import uuid
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.exceptions import InvalidSignature

from node_identity import NodeIdentity, NodeProof, NodeSigner, verify_node_proof


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_CERT_TTL_SECONDS = 3600  # 1 hour
CERT_SERIAL_PREFIX = "TANTRA-CERT"


# ---------------------------------------------------------------------------
# Service Certificate
# ---------------------------------------------------------------------------

@dataclass
class ServiceCertificate:
    """
    Cryptographic certificate binding a service_id to a public key.

    Issued by the ServiceCertificateAuthority and verified during
    mutual authentication. The certificate is signed by the CA's
    private key, making forgery detectable.
    """
    serial_number: str
    service_id: str
    public_key: str          # hex-encoded DER SubjectPublicKeyInfo
    issuer_id: str           # CA node_id
    issued_at: str           # ISO-8601 UTC
    expires_at: str          # ISO-8601 UTC
    ca_signature: str        # hex-encoded ECDSA signature over cert fields
    cert_hash: str = ""      # SHA-256 of canonical cert fields

    def to_dict(self) -> dict:
        return asdict(self)

    def is_expired(self) -> bool:
        """Check if the certificate has expired."""
        now = datetime.now(timezone.utc)
        expires = datetime.fromisoformat(self.expires_at)
        return now > expires

    @property
    def canonical_payload(self) -> str:
        """Deterministic string for hashing / signing."""
        return json.dumps({
            "serial_number": self.serial_number,
            "service_id": self.service_id,
            "public_key": self.public_key,
            "issuer_id": self.issuer_id,
            "issued_at": self.issued_at,
            "expires_at": self.expires_at,
        }, sort_keys=True)


# ---------------------------------------------------------------------------
# Authentication Result
# ---------------------------------------------------------------------------

@dataclass
class AuthResult:
    """Result of a mutual authentication attempt."""
    authenticated: bool
    service_id: str
    reason: str
    trust_level: str = "CLASSICAL"       # CLASSICAL | POST_QUANTUM | HYBRID
    certificate_serial: str = ""
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> dict:
        return asdict(self)


# ---------------------------------------------------------------------------
# Service Certificate Authority
# ---------------------------------------------------------------------------

class ServiceCertificateAuthority:
    """
    Issues, revokes, and verifies service certificates.

    Uses ECDSA P-256 for CA signing. The CA generates its own key pair
    on construction; its public key is published so that any participant
    can verify certificates independently.

    Thread-safe: all mutable state is protected by a lock.
    """

    def __init__(self, ca_id: str = "TANTRA-CA-001"):
        self.ca_id = ca_id
        self._ca_signer = NodeSigner(ca_id, "CERTIFICATE_AUTHORITY")
        self._issued: Dict[str, ServiceCertificate] = {}   # serial -> cert
        self._revoked: set = set()                          # serial numbers
        self._lock = threading.Lock()

    @property
    def ca_public_key(self) -> str:
        return self._ca_signer.identity.public_key

    @property
    def ca_identity(self) -> NodeIdentity:
        return self._ca_signer.identity

    # -- Issuance -----------------------------------------------------------

    def issue_certificate(
        self,
        service_id: str,
        public_key: str,
        ttl_seconds: int = DEFAULT_CERT_TTL_SECONDS,
    ) -> ServiceCertificate:
        """
        Issue a certificate binding service_id to public_key.

        The certificate is signed by the CA and stored for later
        verification and revocation.
        """
        with self._lock:
            serial = f"{CERT_SERIAL_PREFIX}-{uuid.uuid4().hex[:12].upper()}"
            now = datetime.now(timezone.utc)
            expires = now + timedelta(seconds=ttl_seconds)

            cert = ServiceCertificate(
                serial_number=serial,
                service_id=service_id,
                public_key=public_key,
                issuer_id=self.ca_id,
                issued_at=now.isoformat(),
                expires_at=expires.isoformat(),
                ca_signature="",   # filled below
                cert_hash="",      # filled below
            )

            # Compute cert hash
            cert_hash = hashlib.sha256(cert.canonical_payload.encode()).hexdigest()

            # Sign the canonical payload
            proof = self._ca_signer.sign_payload(cert.canonical_payload)

            # Build final certificate with signature and hash
            cert = ServiceCertificate(
                serial_number=serial,
                service_id=service_id,
                public_key=public_key,
                issuer_id=self.ca_id,
                issued_at=now.isoformat(),
                expires_at=expires.isoformat(),
                ca_signature=proof.signature,
                cert_hash=cert_hash,
            )

            self._issued[serial] = cert
            return cert

    # -- Revocation ---------------------------------------------------------

    def revoke_certificate(self, serial_number: str) -> bool:
        """Add a certificate to the revocation list. Returns True if found."""
        with self._lock:
            if serial_number in self._issued:
                self._revoked.add(serial_number)
                return True
            return False

    def is_revoked(self, serial_number: str) -> bool:
        """Check if a certificate has been revoked."""
        with self._lock:
            return serial_number in self._revoked

    def list_revoked(self) -> List[str]:
        """Return all revoked serial numbers."""
        with self._lock:
            return list(self._revoked)

    def list_active_certificates(self) -> List[ServiceCertificate]:
        """Return all non-revoked, non-expired certificates."""
        with self._lock:
            result = []
            for serial, cert in self._issued.items():
                if serial not in self._revoked and not cert.is_expired():
                    result.append(cert)
            return result

    # -- Verification -------------------------------------------------------

    def verify_certificate(self, cert: ServiceCertificate) -> bool:
        """
        Verify a certificate:
        1. Check serial is known and not revoked
        2. Check not expired
        3. Verify CA signature over canonical payload
        """
        with self._lock:
            # Check known
            if cert.serial_number not in self._issued:
                return False

            # Check not revoked
            if cert.serial_number in self._revoked:
                return False

        # Check not expired
        if cert.is_expired():
            return False

        # Verify hash
        expected_hash = hashlib.sha256(cert.canonical_payload.encode()).hexdigest()
        if cert.cert_hash != expected_hash:
            return False

        # Verify CA signature
        return verify_node_proof(
            NodeProof(
                node_id=self.ca_id,
                signature=cert.ca_signature,
                signed_hash=hashlib.sha256(cert.canonical_payload.encode()).hexdigest(),
            ),
            self.ca_public_key,
            cert.canonical_payload,
        )


# ---------------------------------------------------------------------------
# Mutual Authenticator
# ---------------------------------------------------------------------------

class MutualAuthenticator:
    """
    Authenticates service registration requests using mutual authentication.

    Verification pipeline:
    1. Certificate is valid (issued by CA, not revoked, not expired)
    2. Proof signature matches the certificate's public key
    3. service_id in proof matches certificate's service_id
    """

    def __init__(self, ca: ServiceCertificateAuthority):
        self._ca = ca

    def authenticate(
        self,
        service_id: str,
        proof: NodeProof,
        certificate: ServiceCertificate,
        registration_payload: dict,
    ) -> AuthResult:
        """
        Authenticate a service registration request.

        Parameters
        ----------
        service_id         : claimed service identity
        proof              : ECDSA proof of the registration payload
        certificate        : service certificate to validate
        registration_payload : the payload that was signed
        """
        # 1. service_id must match certificate
        if certificate.service_id != service_id:
            return AuthResult(
                authenticated=False,
                service_id=service_id,
                reason=f"Certificate service_id mismatch: "
                       f"cert={certificate.service_id}, claimed={service_id}",
            )

        # 2. Certificate must be valid
        if not self._ca.verify_certificate(certificate):
            reason = "Certificate verification failed"
            if certificate.is_expired():
                reason = "Certificate has expired"
            elif self._ca.is_revoked(certificate.serial_number):
                reason = "Certificate has been revoked"
            return AuthResult(
                authenticated=False,
                service_id=service_id,
                reason=reason,
            )

        # 3. Proof must be valid against certificate's public key
        if not verify_node_proof(proof, certificate.public_key, registration_payload):
            return AuthResult(
                authenticated=False,
                service_id=service_id,
                reason="Proof signature verification failed against certificate public key",
            )

        # 4. Proof node_id should match service_id
        if proof.node_id != service_id:
            return AuthResult(
                authenticated=False,
                service_id=service_id,
                reason=f"Proof node_id mismatch: proof={proof.node_id}, claimed={service_id}",
            )

        return AuthResult(
            authenticated=True,
            service_id=service_id,
            reason="Mutual authentication successful",
            certificate_serial=certificate.serial_number,
        )
