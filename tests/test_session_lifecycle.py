"""Session lifecycle and busy identity contracts (SM-01..SM-04)."""

from __future__ import annotations

import os
import socket
import threading
from pathlib import Path

import pytest

from lilt.exceptions import NamespaceBusyError
from lilt.models.segment import SegmentStatus, StoredSegment
from lilt.tm.repository import TMRepository
from lilt.tm.session_lease import lease_path_for_session_lock


def _seed(repo: TMRepository) -> None:
    repo.save_namespace(
        "main",
        [
            StoredSegment(
                id="cccccccccccc",
                source_hash="cccccccccccc",
                source_text="Lifecycle",
                status=SegmentStatus.GENERATED,
            )
        ],
    )


def test_lease_create_and_cleanup(tmp_path: Path) -> None:
    repo = TMRepository(str(tmp_path))
    _seed(repo)
    lock_path = repo._get_session_lock_path("main")
    meta_path = lease_path_for_session_lock(lock_path)
    tm_path = Path(repo._get_filepath("main"))
    before = tm_path.read_bytes()

    with repo.namespace_session("main", operation="translate"):
        assert os.path.exists(meta_path)
        text = Path(meta_path).read_text(encoding="utf-8")
        assert str(os.getpid()) in text
        assert socket.gethostname() in text
        assert '"operation": "translate"' in text or '"operation":"translate"' in text

    assert not os.path.exists(meta_path)
    assert tm_path.read_bytes() == before


def test_busy_reports_owner_identity(tmp_path: Path) -> None:
    repo = TMRepository(str(tmp_path))
    _seed(repo)
    lock_path = repo._get_session_lock_path("main")
    acquired = threading.Event()
    release = threading.Event()

    def hold() -> None:
        with repo.namespace_session("main", operation="sync"):
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
        assert err.hostname == socket.gethostname()
        assert err.lock_path == lock_path
        assert err.started_at
        assert "pid=" in str(err)
        assert "host=" in str(err)
        assert "lock=" in str(err)
        assert err.cross_host is False
    finally:
        release.set()
        thread.join(timeout=5)
