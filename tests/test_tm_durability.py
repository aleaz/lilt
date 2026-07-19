"""Tests for TM durability policy (strict vs batched fsync)."""

from unittest.mock import patch

from lilt.models.cost_plane import DurabilityPolicy
from lilt.models.segment import SegmentStatus, StoredSegment
from lilt.tm.repository import TMRepository


def _seg(sid: str = "abcd1234ef01") -> StoredSegment:
    return StoredSegment(
        id=sid,
        source_text="Hello",
        source_hash="a" * 64,
        translation="",
        status=SegmentStatus.GENERATED,
        order=0,
        file_path="a.tex",
    )


def test_strict_append_calls_fsync(tmp_path):
    repo = TMRepository(base_dir=str(tmp_path), durability="strict")
    assert repo.durability == DurabilityPolicy.STRICT
    with patch("lilt.tm.repository.os.fsync") as fsync:
        repo.append_segment("ns", _seg())
        assert fsync.called


def test_batched_append_skips_fsync(tmp_path):
    repo = TMRepository(base_dir=str(tmp_path), durability="batched")
    with patch("lilt.tm.repository.os.fsync") as fsync:
        repo.append_segment("ns", _seg())
        assert not fsync.called
    # finalize / save still fsyncs
    with patch("lilt.tm.repository.os.fsync") as fsync:
        repo.save_namespace("ns", [_seg()])
        assert fsync.called
