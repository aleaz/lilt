"""Shared segment eligibility and build-status policies."""

from lilt.models.segment import IMMUTABLE_STATUSES, SegmentStatus, StoredSegment
from lilt.models.status_resolver import StatusResolver


class SegmentPolicy:
    """Defines eligibility rules and status sets for segment lifecycle decisions."""

    IMMUTABLE_STATUSES = IMMUTABLE_STATUSES

    HUMAN_PROTECTED_STATUSES = frozenset(
        {SegmentStatus.LOCKED, SegmentStatus.APPROVED, SegmentStatus.REVIEWED}
    )

    LLM_ARTIFACT_STATUSES = frozenset(
        {SegmentStatus.REFINED, SegmentStatus.DRAFTED, SegmentStatus.CRITIQUED}
    )

    BUILDABLE_STATUSES = frozenset(
        {
            SegmentStatus.REFINED,
            SegmentStatus.REVIEWED,
            SegmentStatus.APPROVED,
            SegmentStatus.LOCKED,
        }
    )

    @staticmethod
    def is_immutable(seg: StoredSegment) -> bool:
        """Return True if the segment must never be auto-translated."""
        return seg.status in SegmentPolicy.IMMUTABLE_STATUSES

    @staticmethod
    def is_human_protected(seg: StoredSegment) -> bool:
        """Return True if the segment has human-finalized status."""
        return seg.status in SegmentPolicy.HUMAN_PROTECTED_STATUSES

    @staticmethod
    def is_eligible_for_sequential(
        seg: StoredSegment,
        force: bool,
        status_filter: str | None,
        segment_id: str | None,
    ) -> bool:
        """Determine whether a segment is eligible for SequentialReflectionStrategy."""
        if SegmentPolicy.is_immutable(seg):
            return False
        if segment_id and not seg.id.startswith(segment_id):
            return False
        if status_filter:
            if SegmentPolicy.is_human_protected(seg) and not force:
                return False
            return StatusResolver.matches(seg.status, status_filter)
        if seg.status == SegmentStatus.GENERATED:
            return True
        if seg.status == SegmentStatus.ERROR:
            return True
        return force

    @staticmethod
    def is_eligible_for_workflow_stage(
        seg: StoredSegment,
        stage: str,
        force: bool,
    ) -> bool:
        """Determine whether a segment is eligible for a workflow stage pass."""
        if SegmentPolicy.is_immutable(seg):
            return False
        if stage == "draft":
            if seg.status in (SegmentStatus.GENERATED, SegmentStatus.ERROR):
                return True
            return force
        if stage == "critique":
            return seg.status == SegmentStatus.DRAFTED
        if stage == "refine":
            return seg.status == SegmentStatus.CRITIQUED
        return False
