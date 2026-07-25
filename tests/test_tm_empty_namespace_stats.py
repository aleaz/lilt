"""Empty TM namespace files must not break aggregate tm list/status."""

from __future__ import annotations

import os
import tempfile

from lilt.models.segment import SegmentStatus, StoredSegment
from lilt.services.tm_service import TMService
from lilt.tm.repository import TMRepository


def test_get_all_stats_allows_empty_namespace_files() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        lilt = os.path.join(tmpdir, ".lilt")
        tm = os.path.join(lilt, "tm")
        os.makedirs(tm)
        with open(os.path.join(lilt, "lilt.yaml"), "w", encoding="utf-8") as f:
            f.write(
                "project:\n  source_lang: en\n  target_lang: es\n"
                "llm:\n  base_url: http://127.0.0.1:9\n  model: mock\n"
            )
        repo = TMRepository(tm)
        repo.save_namespace(
            "chapter",
            [
                StoredSegment(
                    id="a" * 40,
                    source_hash="b" * 64,
                    source_text="Hello",
                    status=SegmentStatus.GENERATED,
                    translation="",
                )
            ],
        )
        open(os.path.join(tm, "fig__trap.jsonl"), "w", encoding="utf-8").close()

        service = TMService(tmpdir)
        stats, corrupt = service.get_all_stats()
        assert corrupt == []
        assert stats["total"] == 1
        assert stats[SegmentStatus.GENERATED.value] == 1
        empty_stats = service.get_stats("fig__trap")
        assert empty_stats["total"] == 0
        assert service.list_segments("fig__trap") == []
