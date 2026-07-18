"""Tests for namespace session locking (single-writer contract)."""

import tempfile
import threading

import pytest

from lilt.exceptions import NamespaceBusyError
from lilt.models.segment import SegmentStatus, StoredSegment
from lilt.tm.repository import TMRepository


def test_namespace_session_rejects_concurrent_holder():
    with tempfile.TemporaryDirectory() as tmpdir:
        repo = TMRepository(tmpdir)
        repo.save_namespace(
            "mock",
            [
                StoredSegment(
                    id="seg1",
                    source_hash="seg1",
                    source_text="Source",
                    status=SegmentStatus.GENERATED,
                )
            ],
        )

        acquired = threading.Event()
        release = threading.Event()
        error: list[Exception] = []

        def hold_lock() -> None:
            try:
                with repo.namespace_session("mock"):
                    acquired.set()
                    release.wait(timeout=5)
            except Exception as exc:
                error.append(exc)

        thread = threading.Thread(target=hold_lock)
        thread.start()
        assert acquired.wait(timeout=5)

        try:
            with (
                pytest.raises(NamespaceBusyError),
                repo.namespace_session("mock"),
            ):
                pass
        finally:
            release.set()
            thread.join(timeout=5)

        assert not error
