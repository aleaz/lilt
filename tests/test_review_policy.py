"""Tests for ReviewPolicy human review queue."""

from lilt.core.review_policy import ReviewPolicy
from lilt.models.segment import SegmentStatus, StoredSegment


def _seg(status: SegmentStatus, translation: str = "Hola") -> StoredSegment:
    return StoredSegment(
        id="abc123",
        source_hash="hash",
        source_text="Hello",
        status=status,
        translation=translation,
    )


def test_default_queue_includes_refined_and_reviewed():
    policy = ReviewPolicy()
    assert policy.is_reviewable(_seg(SegmentStatus.REFINED))
    assert policy.is_reviewable(_seg(SegmentStatus.REVIEWED))
    assert not policy.is_reviewable(_seg(SegmentStatus.GENERATED))
    assert not policy.is_reviewable(_seg(SegmentStatus.REFINED, translation=""))


def test_from_config_custom_queue():
    policy = ReviewPolicy.from_config({"review": {"queue_statuses": ["approved"]}})
    assert policy.is_reviewable(_seg(SegmentStatus.APPROVED))
    assert not policy.is_reviewable(_seg(SegmentStatus.REFINED))
