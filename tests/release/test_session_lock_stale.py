"""Release lock: stale session lease reclaim without manual rm (R-01-F4)."""

from __future__ import annotations

import os
import socket
import threading
from pathlib import Path

import pytest

from lilt.exceptions import NamespaceBusyError
from lilt.models.segment import SegmentStatus, StoredSegment
from lilt.tm.repository import TMRepository
from lilt.tm.session_lease import SessionLease, write_lease

pytestmark = pytest.mark.release


def test_stale_session_lock_reclaimed_for_dead_pid(tmp_path: Path) -> None:
    repo = TMRepository(str(tmp_path))
    repo.save_namespace(
        "main",
        [
            StoredSegment(
                id="aaaaaaaaaaaa",
                source_hash="aaaaaaaaaaaa",
                source_text="Hello",
                status=SegmentStatus.GENERATED,
            )
        ],
    )
    lock_path = repo._get_session_lock_path("main")
    meta_path = lock_path[: -len(".session.lock")] + ".session.lease"
    # Orphan lock file + dead-owner lease (no live holder).
    Path(lock_path).write_text("", encoding="utf-8")
    write_lease(
        meta_path,
        SessionLease(
            pid=2_147_483_646,
            hostname=socket.gethostname(),
            started_at="2020-01-01T00:00:00+00:00",
            lease_id="stale",
            operation="translate",
        ),
    )

    with repo.namespace_session("main"):
        assert os.path.exists(meta_path)
        lease_alive = Path(meta_path).read_text(encoding="utf-8")
        assert str(os.getpid()) in lease_alive

    assert not os.path.exists(meta_path)


def test_live_holder_still_busy(tmp_path: Path) -> None:
    repo = TMRepository(str(tmp_path))
    repo.save_namespace(
        "main",
        [
            StoredSegment(
                id="bbbbbbbbbbbb",
                source_hash="bbbbbbbbbbbb",
                source_text="Hello",
                status=SegmentStatus.GENERATED,
            )
        ],
    )
    acquired = threading.Event()
    release = threading.Event()

    def hold() -> None:
        with repo.namespace_session("main"):
            acquired.set()
            release.wait(timeout=5)

    thread = threading.Thread(target=hold)
    thread.start()
    assert acquired.wait(timeout=5)
    try:
        with (
            pytest.raises(NamespaceBusyError) as exc_info,
            repo.namespace_session("main"),
        ):
            pass
        err = exc_info.value
        assert err.pid == os.getpid()
        assert err.hostname is not None
        assert err.lock_path is not None
        assert "pid=" in str(err)
        assert "host=" in str(err)
        assert "lock=" in str(err)
    finally:
        release.set()
        thread.join(timeout=5)
