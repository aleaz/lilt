import os
import tempfile

from lilt.models.segment import SegmentStatus, StoredSegment
from lilt.models.status_resolver import StatusResolver
from lilt.services.tm_service import TMService
from lilt.tm.repository import TMRepository


def test_list_segments_status_alias_machine_done():
    with tempfile.TemporaryDirectory() as tmpdir:
        lilt_dir = os.path.join(tmpdir, ".lilt")
        tm_dir = os.path.join(lilt_dir, "tm")
        os.makedirs(tm_dir)
        with open(os.path.join(lilt_dir, "lilt.yaml"), "w", encoding="utf-8") as f:
            f.write(
                "project:\n  source_lang: en\n  target_lang: es\n"
                "llm:\n  base_url: http://127.0.0.1:9\n  model: mock\n"
            )
        repo = TMRepository(base_dir=tm_dir)
        seg = StoredSegment(
            id="seg1",
            source_hash="h1",
            source_text="Hello",
            status=SegmentStatus.REFINED,
            translation="Hola",
        )
        repo.save_namespace("chapter1", [seg])

        service = TMService(tmpdir)
        results = service.list_segments("chapter1", status="machine_done")
        assert len(results) == 1
        assert results[0].status == SegmentStatus.REFINED
        assert StatusResolver.matches(SegmentStatus.REFINED, "machine_done")

        empty = service.list_segments("chapter1", status="generated")
        assert empty == []
