"""Segment ID prefix matching for Translation Memory namespaces."""

from lilt.exceptions import MultipleSegmentsFoundError, SegmentNotFoundError
from lilt.models.segment import StoredSegment


def match_segments_by_prefix(
    segments: dict[str, StoredSegment], prefix: str
) -> list[StoredSegment]:
    """Return all segments whose ID starts with *prefix*."""
    return [seg for seg in segments.values() if seg.id.startswith(prefix)]


def resolve_unique_segment(
    segments: dict[str, StoredSegment],
    prefix: str,
    namespace: str,
) -> StoredSegment:
    """Resolve a unique segment by ID prefix or raise a domain error."""
    matches = match_segments_by_prefix(segments, prefix)
    if not matches:
        raise SegmentNotFoundError(prefix, namespace)
    if len(matches) > 1:
        raise MultipleSegmentsFoundError(prefix)
    return matches[0]
