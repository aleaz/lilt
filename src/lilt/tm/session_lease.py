"""Namespace session lease: ownership metadata + dead-PID reclaim."""

from __future__ import annotations

import json
import logging
import os
import socket
import uuid
from dataclasses import asdict, dataclass
from datetime import UTC, datetime

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SessionLease:
    """Owner record for a namespace session lock."""

    pid: int
    hostname: str
    started_at: str
    lease_id: str
    operation: str | None = None

    @classmethod
    def create(cls, *, operation: str | None = None) -> SessionLease:
        """Build a lease for the current process and host."""
        return cls(
            pid=os.getpid(),
            hostname=socket.gethostname(),
            started_at=datetime.now(UTC).isoformat(),
            lease_id=str(uuid.uuid4()),
            operation=operation,
        )


def lease_path_for_session_lock(session_lock_path: str) -> str:
    """Companion metadata path next to ``*.session.lock``."""
    if session_lock_path.endswith(".session.lock"):
        return session_lock_path[: -len(".session.lock")] + ".session.lease"
    return f"{session_lock_path}.lease"


def write_lease(path: str, lease: SessionLease) -> None:
    """Atomically write lease JSON."""
    payload = asdict(lease)
    directory = os.path.dirname(path) or "."
    os.makedirs(directory, exist_ok=True)
    tmp = f"{path}.tmp.{os.getpid()}"
    with open(tmp, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(tmp, path)


def read_lease(path: str) -> SessionLease | None:
    """Load lease or return None if missing/unreadable."""
    if not os.path.exists(path):
        return None
    try:
        with open(path, encoding="utf-8") as handle:
            data = json.load(handle)
        return SessionLease(
            pid=int(data["pid"]),
            hostname=str(data["hostname"]),
            started_at=str(data["started_at"]),
            lease_id=str(data["lease_id"]),
            operation=data.get("operation"),
        )
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        logger.warning("Could not read session lease %s: %s", path, exc)
        return None


def clear_lease(path: str) -> None:
    """Best-effort remove lease file."""
    try:
        os.remove(path)
    except FileNotFoundError:
        pass
    except OSError as exc:
        logger.warning("Could not clear session lease %s: %s", path, exc)


def is_pid_alive(pid: int) -> bool:
    """Return True if ``pid`` appears to be a live local process."""
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        # Process exists but we cannot signal it — treat as alive.
        return True
    except OSError:
        return False
    return True


def same_host(lease: SessionLease) -> bool:
    """Return True when the lease hostname matches this machine."""
    return lease.hostname == socket.gethostname()


def should_reclaim_lease(lease: SessionLease | None) -> bool:
    """True when the lease is missing or owned by a dead same-host process."""
    if lease is None:
        return True
    if not same_host(lease):
        return False
    return not is_pid_alive(lease.pid)
