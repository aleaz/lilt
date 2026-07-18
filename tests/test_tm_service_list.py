import os
import tempfile

from lilt.models.segment import SegmentStatus, StoredSegment
from lilt.models.status_resolver import StatusResolver
from lilt.services.tm_service import TMService
from lilt.tm.repository import TMRepository


def test_list_segments_status_alias_machine_done():
    with tempfile.TemporaryDirectory() as tmpdir:
        tm_dir = os.path.join(tmpdir, ".lilt", "tm")
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
