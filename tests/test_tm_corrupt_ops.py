"""Soft-skip corrupt namespaces in aggregate TM ops."""

import os
import tempfile

from lilt.models.segment import SegmentStatus, StoredSegment
from lilt.services.tm_service import TMService


def _write_valid(path: str, seg_id: str = "seg1") -> None:
    seg = StoredSegment(
        id=seg_id,
        source_hash=seg_id,
        source_text="Hello",
        status=SegmentStatus.GENERATED,
        translation="",
    )
    with open(path, "w", encoding="utf-8") as f:
        f.write(seg.model_dump_json(by_alias=True) + "\n")


def test_get_all_stats_skips_corrupt_namespace():
    with tempfile.TemporaryDirectory() as tmpdir:
        lilt_dir = os.path.join(tmpdir, ".lilt")
        tm_dir = os.path.join(lilt_dir, "tm")
        os.makedirs(tm_dir)
        with open(os.path.join(lilt_dir, "lilt.yaml"), "w", encoding="utf-8") as f:
            f.write(
                "project:\n  source_lang: en\n  target_lang: es\n"
                "llm:\n  base_url: http://127.0.0.1:9\n  model: mock\n"
            )
        _write_valid(os.path.join(tm_dir, "good.jsonl"))
        with open(os.path.join(tm_dir, "bad.jsonl"), "w", encoding="utf-8") as f:
            f.write("{not json}\n")

        service = TMService(tmpdir)
        stats, corrupt = service.get_all_stats()
        assert corrupt == ["bad"]
        assert stats["total"] == 1
        assert stats["generated"] == 1


def test_list_all_segments_skips_corrupt_namespace():
    with tempfile.TemporaryDirectory() as tmpdir:
        tm_dir = os.path.join(tmpdir, ".lilt", "tm")
        os.makedirs(tm_dir)
        _write_valid(os.path.join(tm_dir, "good.jsonl"))
        with open(os.path.join(tm_dir, "bad.jsonl"), "w", encoding="utf-8") as f:
            f.write("{not json}\n")

        service = TMService(tmpdir)
        results, corrupt = service.list_all_segments()
        assert corrupt == ["bad"]
        assert len(results) == 1
        assert results[0][0] == "good"
