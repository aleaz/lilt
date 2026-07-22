"""Deterministic Session Manager reclaim contracts (R-01-F4 / SM-06..SM-10).

Forces the Timeout → reclaim branch so Unix flock cannot skip
``_force_clear_session_lock``. No LLM, no sleeps-as-sync.
"""

from __future__ import annotations

import logging
import os
import socket
from pathlib import Path

import pytest
from filelock import FileLock, Timeout

from lilt.exceptions import NamespaceBusyError
from lilt.models.segment import SegmentStatus, StoredSegment
from lilt.tm.repository import TMRepository
from lilt.tm.session_lease import SessionLease, lease_path_for_session_lock, write_lease


def _seed(repo: TMRepository, namespace: str = "main") -> StoredSegment:
    seg = StoredSegment(
        id="aaaaaaaaaaaa",
        source_hash="aaaaaaaaaaaa",
        source_text="Hello reclaim",
        status=SegmentStatus.GENERATED,
    )
    repo.save_namespace(namespace, [seg])
    return seg


def _dead_lease(*, hostname: str | None = None) -> SessionLease:
    return SessionLease(
        pid=2_147_483_646,
        hostname=hostname or socket.gethostname(),
        started_at="2020-01-01T00:00:00+00:00",
        lease_id="stale",
        operation="translate",
    )


_ORIG_ACQUIRE = FileLock.acquire


def _force_first_acquire_timeout(monkeypatch: pytest.MonkeyPatch) -> dict[str, int]:
    """First ``FileLock.acquire`` raises Timeout; subsequent calls use real acquire."""
    state = {"n": 0}

    def acquire(
        self: FileLock, timeout: float | None = None, poll_interval: float = 0.05
    ):
        state["n"] += 1
        if state["n"] == 1:
            raise Timeout(str(self.lock_file))
        return _ORIG_ACQUIRE(self, timeout=timeout, poll_interval=poll_interval)

    monkeypatch.setattr(FileLock, "acquire", acquire)
    return state


def test_reclaim_dead_pid_under_timeout(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = TMRepository(str(tmp_path))
    _seed(repo)
    lock_path = repo._get_session_lock_path("main")
    meta_path = lease_path_for_session_lock(lock_path)
    Path(lock_path).write_text("", encoding="utf-8")
    write_lease(meta_path, _dead_lease())

    clears: list[tuple[str, str]] = []
    real_clear = TMRepository._force_clear_session_lock

    def spy_clear(lp: str, mp: str) -> None:
        clears.append((lp, mp))
        real_clear(lp, mp)

    monkeypatch.setattr(
        TMRepository, "_force_clear_session_lock", staticmethod(spy_clear)
    )
    _force_first_acquire_timeout(monkeypatch)

    before = Path(repo._get_filepath("main")).read_bytes()
    with repo.namespace_session("main"):
        assert clears, "reclaim must call _force_clear_session_lock"
        assert os.path.exists(meta_path)
        assert str(os.getpid()) in Path(meta_path).read_text(encoding="utf-8")
    assert not os.path.exists(meta_path)
    assert Path(repo._get_filepath("main")).read_bytes() == before


def test_reclaim_missing_lease_under_timeout(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = TMRepository(str(tmp_path))
    _seed(repo)
    lock_path = repo._get_session_lock_path("main")
    meta_path = lease_path_for_session_lock(lock_path)
    Path(lock_path).write_text("", encoding="utf-8")
    assert not os.path.exists(meta_path)

    clears: list[str] = []
    real_clear = TMRepository._force_clear_session_lock

    def spy_clear(lp: str, mp: str) -> None:
        clears.append(mp)
        real_clear(lp, mp)

    monkeypatch.setattr(
        TMRepository, "_force_clear_session_lock", staticmethod(spy_clear)
    )
    _force_first_acquire_timeout(monkeypatch)

    with repo.namespace_session("main"):
        assert clears
    assert not os.path.exists(meta_path)


def test_reclaim_corrupt_lease_under_timeout(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    repo = TMRepository(str(tmp_path))
    _seed(repo)
    lock_path = repo._get_session_lock_path("main")
    meta_path = lease_path_for_session_lock(lock_path)
    Path(lock_path).write_text("", encoding="utf-8")
    Path(meta_path).write_text("{not-json", encoding="utf-8")

    clears: list[str] = []
    real_clear = TMRepository._force_clear_session_lock

    def spy_clear(lp: str, mp: str) -> None:
        clears.append(mp)
        real_clear(lp, mp)

    monkeypatch.setattr(
        TMRepository, "_force_clear_session_lock", staticmethod(spy_clear)
    )
    _force_first_acquire_timeout(monkeypatch)

    with (
        caplog.at_level(logging.WARNING),
        repo.namespace_session("main"),
    ):
        assert clears
    assert not os.path.exists(meta_path)


def test_reclaim_invalid_metadata_under_timeout(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Lease JSON missing required keys → read_lease None → reclaim."""
    repo = TMRepository(str(tmp_path))
    _seed(repo)
    lock_path = repo._get_session_lock_path("main")
    meta_path = lease_path_for_session_lock(lock_path)
    Path(lock_path).write_text("", encoding="utf-8")
    Path(meta_path).write_text('{"pid": "nope"}\n', encoding="utf-8")

    clears: list[str] = []
    real_clear = TMRepository._force_clear_session_lock

    def spy_clear(lp: str, mp: str) -> None:
        clears.append(mp)
        real_clear(lp, mp)

    monkeypatch.setattr(
        TMRepository, "_force_clear_session_lock", staticmethod(spy_clear)
    )
    _force_first_acquire_timeout(monkeypatch)

    with repo.namespace_session("main"):
        assert clears
    assert not os.path.exists(meta_path)


def test_cross_host_busy_no_reclaim(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = TMRepository(str(tmp_path))
    _seed(repo)
    lock_path = repo._get_session_lock_path("main")
    meta_path = lease_path_for_session_lock(lock_path)
    Path(lock_path).write_text("", encoding="utf-8")
    write_lease(meta_path, _dead_lease(hostname="other-host.example"))

    clears: list[tuple[str, str]] = []

    def spy_clear(lp: str, mp: str) -> None:
        clears.append((lp, mp))

    monkeypatch.setattr(
        TMRepository, "_force_clear_session_lock", staticmethod(spy_clear)
    )
    _force_first_acquire_timeout(monkeypatch)

    with (
        pytest.raises(NamespaceBusyError) as exc_info,
        repo.namespace_session("main"),
    ):
        pass
    err = exc_info.value
    assert not clears
    assert err.cross_host is True
    assert err.hostname == "other-host.example"
    assert "another host" in str(err).lower() or "host=" in str(err)


def test_force_clear_removes_softfilelock_companion(tmp_path: Path) -> None:
    repo = TMRepository(str(tmp_path))
    _seed(repo)
    lock_path = repo._get_session_lock_path("main")
    meta_path = lease_path_for_session_lock(lock_path)
    Path(lock_path).write_text("", encoding="utf-8")
    companion = f"{lock_path}.lock"
    Path(companion).write_text("", encoding="utf-8")
    write_lease(meta_path, _dead_lease())

    TMRepository._force_clear_session_lock(lock_path, meta_path)
    assert not os.path.exists(meta_path)
    assert not os.path.exists(lock_path)
    assert not os.path.exists(companion)


def test_reclaim_idempotent_repeated(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = TMRepository(str(tmp_path))
    _seed(repo)
    lock_path = repo._get_session_lock_path("main")
    meta_path = lease_path_for_session_lock(lock_path)
    before = Path(repo._get_filepath("main")).read_bytes()

    for _ in range(3):
        Path(lock_path).write_text("", encoding="utf-8")
        write_lease(meta_path, _dead_lease())
        # Fresh Timeout-first sequence each iteration
        _force_first_acquire_timeout(monkeypatch)
        with repo.namespace_session("main"):
            assert str(os.getpid()) in Path(meta_path).read_text(encoding="utf-8")
        assert not os.path.exists(meta_path)

    assert Path(repo._get_filepath("main")).read_bytes() == before
