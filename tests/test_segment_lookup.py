import pytest

from lilt.exceptions import MultipleSegmentsFoundError, SegmentNotFoundError
from lilt.models.segment import SegmentStatus, StoredSegment
from lilt.tm.segment_lookup import match_segments_by_prefix, resolve_unique_segment


def _seg(seg_id: str) -> StoredSegment:
    return StoredSegment(
        id=seg_id,
        source_hash=f"hash-{seg_id}",
        source_text="text",
        status=SegmentStatus.GENERATED,
        translation="",
    )


def test_match_segments_by_prefix():
    segments = {"abcd1234": _seg("abcd1234"), "zyxw9876": _seg("zyxw9876")}
    matches = match_segments_by_prefix(segments, "abcd")
    assert len(matches) == 1
    assert matches[0].id == "abcd1234"


def test_resolve_unique_segment_success():
    segments = {"abcd1234": _seg("abcd1234")}
    seg = resolve_unique_segment(segments, "abcd", "chapter1")
    assert seg.id == "abcd1234"


def test_resolve_unique_segment_not_found():
    with pytest.raises(SegmentNotFoundError):
        resolve_unique_segment({}, "abcd", "chapter1")


def test_resolve_unique_segment_multiple_matches():
    segments = {"abcd1111": _seg("abcd1111"), "abcd2222": _seg("abcd2222")}
    with pytest.raises(MultipleSegmentsFoundError):
        resolve_unique_segment(segments, "abcd", "chapter1")
