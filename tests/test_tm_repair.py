"""Tests for TM JSONL corruption recovery and repair."""

import glob
import os
import tempfile

import pytest

from lilt.exceptions import TMCorruptionError
from lilt.models.segment import SegmentStatus, StoredSegment
from lilt.tm.repository import TMRepository


def _valid_segment_json(seg_id: str = "seg1") -> str:
    seg = StoredSegment(
        id=seg_id,
        source_hash=seg_id,
        source_text="Source text",
        status=SegmentStatus.GENERATED,
        translation="",
    )
    return seg.model_dump_json(by_alias=True)


def test_load_namespace_skip_corrupt_ignores_bad_lines():
    with tempfile.TemporaryDirectory() as tmpdir:
        repo = TMRepository(tmpdir)
        path = os.path.join(tmpdir, "main.jsonl")
        with open(path, "w", encoding="utf-8") as f:
            f.write(_valid_segment_json() + "\n")
            f.write("{not valid json}\n")
            f.write(_valid_segment_json("seg2") + "\n")

        report = repo.load_namespace_report("main", skip_corrupt=True)
        assert len(report.segments) == 2
        assert len(report.corrupt_lines) == 1
        assert report.corrupt_lines[0].line_number == 2


def test_load_namespace_strict_raises_on_corrupt_line():
    with tempfile.TemporaryDirectory() as tmpdir:
        repo = TMRepository(tmpdir)
        path = os.path.join(tmpdir, "main.jsonl")
        with open(path, "w", encoding="utf-8") as f:
            f.write("{not valid json}\n")
        with pytest.raises(TMCorruptionError):
            repo.load_namespace("main")


def test_repair_namespace_compacts_and_backups():
    with tempfile.TemporaryDirectory() as tmpdir:
        repo = TMRepository(tmpdir)
        path = os.path.join(tmpdir, "main.jsonl")
        with open(path, "w", encoding="utf-8") as f:
            f.write(_valid_segment_json() + "\n")
            f.write("{truncated json\n")

        corrupt = repo.repair_namespace("main", dry_run=False)
        assert len(corrupt) == 1

        segments = repo.load_namespace("main")
        assert len(segments) == 1
        assert "seg1" in segments

        backups = glob.glob(os.path.join(tmpdir, "main.jsonl.corrupt-*"))
        assert len(backups) == 1


def test_repair_dry_run_does_not_rewrite_file():
    with tempfile.TemporaryDirectory() as tmpdir:
        repo = TMRepository(tmpdir)
        path = os.path.join(tmpdir, "main.jsonl")
        with open(path, "w", encoding="utf-8") as f:
            f.write(_valid_segment_json() + "\n")
            f.write("{bad}\n")

        corrupt = repo.repair_namespace("main", dry_run=True)
        assert len(corrupt) == 1
        with open(path, encoding="utf-8") as f:
            assert f.read().count("\n") == 2
        assert not glob.glob(os.path.join(tmpdir, "main.jsonl.corrupt-*"))
