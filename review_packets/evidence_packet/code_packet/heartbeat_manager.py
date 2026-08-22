"""
heartbeat_manager.py — Lease-Based Heartbeat Protocol

Manages service liveness through lease grants, heartbeat renewals,
and automatic expiry detection. Every mutation is recorded as evidence
in the RegistrationEvidenceRecorder.

RESPONSIBILITY BOUNDARY
-----------------------
HeartbeatManager OWNS:
    - Lease grant / renewal / revocation
    - Heartbeat tracking
    - Automatic expiry detection
    - Reaper thread lifecycle

HeartbeatManager does NOT OWN:
    - Service registration          → PlatformServiceRegistry
    - Certificate management        → ServiceCertificateAuthority
    - Federation sync               → FederatedRegistryNode
    - Lifecycle transitions          → LifecycleManager
"""

from __future__ import annotations

import logging
import threading
import time
import uuid
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone, timedelta
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger("tantra.platform.heartbeat")


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_LEASE_TTL_SECONDS = 30
DEFAULT_CHECK_INTERVAL_SECONDS = 5


# ---------------------------------------------------------------------------
# Service Lease
# ---------------------------------------------------------------------------

@dataclass
class ServiceLease:
    """
    Represents a time-limited lease for a registered service.

    Services must send heartbeats before the lease expires or they
    will be automatically deregistered from the federation.
    """
    service_id: str
    lease_id: str
    granted_at: str           # ISO-8601 UTC
    expires_at: str           # ISO-8601 UTC
    ttl_seconds: int
    last_heartbeat: str       # ISO-8601 UTC
    renewal_count: int = 0
    status: str = "ACTIVE"    # ACTIVE | EXPIRED | REVOKED

    def to_dict(self) -> dict:
        return asdict(self)

    def is_expired(self) -> bool:
        """Check if the lease has expired."""
        now = datetime.now(timezone.utc)
        expires = datetime.fromisoformat(self.expires_at)
        return now > expires

    def time_remaining_seconds(self) -> float:
        """Seconds until expiry. Negative means already expired."""
        now = datetime.now(timezone.utc)
        expires = datetime.fromisoformat(self.expires_at)
        return (expires - now).total_seconds()


# ---------------------------------------------------------------------------
# Heartbeat Manager
# ---------------------------------------------------------------------------

class HeartbeatManager:
    """
    Manages service leases and heartbeat tracking.

    Runs a background reaper thread that periodically checks for expired
    leases and invokes the expiry callback. The reaper is a daemon thread
    and will not prevent process exit.

    Thread-safe: all mutable state is protected by a lock.
    """

    def __init__(
        self,
        ttl_seconds: int = DEFAULT_LEASE_TTL_SECONDS,
        check_interval: int = DEFAULT_CHECK_INTERVAL_SECONDS,
        on_expiry_callback: Optional[Callable[[str], None]] = None,
        evidence_recorder=None,
    ):
        self._ttl_seconds = ttl_seconds
        self._check_interval = check_interval
        self._on_expiry = on_expiry_callback
        self._evidence = evidence_recorder

        self._leases: Dict[str, ServiceLease] = {}
        self._lock = threading.Lock()

        # Reaper thread
        self._reaper_running = False
        self._reaper_thread: Optional[threading.Thread] = None

    # -- Lease management ---------------------------------------------------

    def grant_lease(self, service_id: str, ttl_seconds: int = None) -> ServiceLease:
        """
        Grant a new lease for a service.

        If a lease already exists for this service, it is replaced.
        """
        ttl = ttl_seconds or self._ttl_seconds
        now = datetime.now(timezone.utc)
        expires = now + timedelta(seconds=ttl)

        lease = ServiceLease(
            service_id=service_id,
            lease_id=str(uuid.uuid4()),
            granted_at=now.isoformat(),
            expires_at=expires.isoformat(),
            ttl_seconds=ttl,
            last_heartbeat=now.isoformat(),
            renewal_count=0,
            status="ACTIVE",
        )

        with self._lock:
            self._leases[service_id] = lease

        self._record_evidence("LEASE_GRANTED", service_id, {
            "lease_id": lease.lease_id,
            "ttl_seconds": ttl,
            "expires_at": lease.expires_at,
        })

        logger.info(f"Lease granted: {service_id} (TTL={ttl}s, expires={lease.expires_at})")
        return lease

    def renew_lease(self, service_id: str) -> Optional[ServiceLease]:
        """
        Renew an existing lease by extending its expiry by TTL.

        Returns the updated lease, or None if no lease exists.
        """
        with self._lock:
            lease = self._leases.get(service_id)
            if lease is None or lease.status != "ACTIVE":
                return None

            now = datetime.now(timezone.utc)
            new_expires = now + timedelta(seconds=lease.ttl_seconds)

            # Rebuild with updated fields (dataclass is not frozen)
            lease.expires_at = new_expires.isoformat()
            lease.last_heartbeat = now.isoformat()
            lease.renewal_count += 1

        self._record_evidence("LEASE_RENEWED", service_id, {
            "lease_id": lease.lease_id,
            "renewal_count": lease.renewal_count,
            "new_expires_at": lease.expires_at,
        })

        logger.debug(f"Lease renewed: {service_id} (renewal #{lease.renewal_count})")
        return lease

    def receive_heartbeat(self, service_id: str) -> bool:
        """
        Record a heartbeat from a service. Automatically renews the lease.

        Returns True if heartbeat was accepted, False if no active lease.
        """
        with self._lock:
            lease = self._leases.get(service_id)
            if lease is None or lease.status != "ACTIVE":
                return False

            now = datetime.now(timezone.utc)
            lease.last_heartbeat = now.isoformat()

            # Also extend the lease
            new_expires = now + timedelta(seconds=lease.ttl_seconds)
            lease.expires_at = new_expires.isoformat()
            lease.renewal_count += 1

        logger.debug(f"Heartbeat received: {service_id}")
        return True

    def revoke_lease(self, service_id: str) -> bool:
        """
        Immediately revoke a service's lease.

        Returns True if revoked, False if no lease exists.
        """
        with self._lock:
            lease = self._leases.get(service_id)
            if lease is None:
                return False
            lease.status = "REVOKED"

        self._record_evidence("LEASE_REVOKED", service_id, {
            "lease_id": lease.lease_id,
            "reason": "Manual revocation",
        })

        logger.info(f"Lease revoked: {service_id}")
        return True

    def check_expired(self) -> List[str]:
        """
        Check for expired leases. Returns list of expired service_ids.

        Does NOT invoke callbacks — the caller or reaper thread does that.
        """
        expired = []
        with self._lock:
            for sid, lease in self._leases.items():
                if lease.status == "ACTIVE" and lease.is_expired():
                    lease.status = "EXPIRED"
                    expired.append(sid)

        for sid in expired:
            self._record_evidence("LEASE_EXPIRED", sid, {
                "reason": "TTL exceeded without heartbeat renewal",
            })
            logger.info(f"Lease expired: {sid}")

        return expired

    # -- Queries ------------------------------------------------------------

    def get_lease(self, service_id: str) -> Optional[ServiceLease]:
        """Get the current lease for a service."""
        with self._lock:
            return self._leases.get(service_id)

    def get_active_leases(self) -> List[ServiceLease]:
        """Return all active (non-expired, non-revoked) leases."""
        with self._lock:
            return [
                lease for lease in self._leases.values()
                if lease.status == "ACTIVE" and not lease.is_expired()
            ]

    def get_all_leases(self) -> List[ServiceLease]:
        """Return all leases regardless of status."""
        with self._lock:
            return list(self._leases.values())

    def has_active_lease(self, service_id: str) -> bool:
        """Check if a service has an active, non-expired lease."""
        with self._lock:
            lease = self._leases.get(service_id)
            return (
                lease is not None
                and lease.status == "ACTIVE"
                and not lease.is_expired()
            )

    # -- Reaper thread ------------------------------------------------------

    def start_reaper(self):
        """Start the background reaper thread that checks for expired leases."""
        if self._reaper_running:
            return

        self._reaper_running = True
        self._reaper_thread = threading.Thread(
            target=self._reaper_loop,
            name="heartbeat-reaper",
            daemon=True,
        )
        self._reaper_thread.start()
        logger.info(f"Heartbeat reaper started (interval={self._check_interval}s)")

    def stop_reaper(self):
        """Stop the background reaper thread."""
        self._reaper_running = False
        if self._reaper_thread:
            self._reaper_thread.join(timeout=self._check_interval + 1)
            self._reaper_thread = None
        logger.info("Heartbeat reaper stopped")

    def _reaper_loop(self):
        """Background loop that periodically checks for expired leases."""
        while self._reaper_running:
            try:
                expired = self.check_expired()
                if expired and self._on_expiry:
                    for sid in expired:
                        try:
                            self._on_expiry(sid)
                        except Exception as e:
                            logger.error(f"Expiry callback error for {sid}: {e}")
            except Exception as e:
                logger.error(f"Reaper loop error: {e}")

            # Sleep in small increments so stop_reaper() is responsive
            for _ in range(self._check_interval * 10):
                if not self._reaper_running:
                    return
                time.sleep(0.1)

    # -- Evidence -----------------------------------------------------------

    def _record_evidence(self, event_type: str, service_id: str, details: dict):
        """Record an evidence entry if an evidence recorder is attached."""
        if self._evidence:
            try:
                self._evidence.record(event_type, service_id, details)
            except Exception as e:
                logger.error(f"Evidence recording failed: {e}")
