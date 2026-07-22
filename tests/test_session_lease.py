"""Unit tests for namespace session lease helpers."""

from __future__ import annotations

import os
from pathlib import Path

from lilt.tm.session_lease import (
    SessionLease,
    clear_lease,
    is_pid_alive,
    lease_path_for_session_lock,
    read_lease,
    should_reclaim_lease,
    write_lease,
)


def test_lease_path_for_session_lock() -> None:
    assert (
        lease_path_for_session_lock("/tmp/main.jsonl.session.lock")
        == "/tmp/main.jsonl.session.lease"
    )


def test_write_read_clear_lease(tmp_path: Path) -> None:
    path = str(tmp_path / "main.jsonl.session.lease")
    lease = SessionLease.create(operation="translate")
    write_lease(path, lease)
    loaded = read_lease(path)
    assert loaded is not None
    assert loaded.pid == os.getpid()
    assert loaded.lease_id == lease.lease_id
    clear_lease(path)
    assert read_lease(path) is None


def test_should_reclaim_missing_or_dead() -> None:
    assert should_reclaim_lease(None) is True
    dead = SessionLease(
        pid=2_147_483_646,
        hostname=__import__("socket").gethostname(),
        started_at="2020-01-01T00:00:00+00:00",
        lease_id="x",
    )
    # Extremely high unused PID is typically dead
    if not is_pid_alive(dead.pid):
        assert should_reclaim_lease(dead) is True

    live = SessionLease.create()
    assert should_reclaim_lease(live) is False


def test_should_not_reclaim_cross_host() -> None:
    foreign = SessionLease(
        pid=1,
        hostname="other-host.example",
        started_at="2020-01-01T00:00:00+00:00",
        lease_id="y",
    )
    assert should_reclaim_lease(foreign) is False
