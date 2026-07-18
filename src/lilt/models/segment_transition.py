"""Allowed segment status transitions for human and CLI operations."""

from lilt.exceptions import InvalidTransitionError
from lilt.models.segment import IMMUTABLE_STATUSES, SegmentStatus

_HUMAN_AUTHORING_TARGETS = frozenset(
    {
        SegmentStatus.GENERATED,
        SegmentStatus.CONFLICT,
        SegmentStatus.REVIEWED,
        SegmentStatus.APPROVED,
    }
)

_ALLOWED: dict[SegmentStatus, set[SegmentStatus]] = {
    SegmentStatus.GENERATED: {
        SegmentStatus.CONFLICT,
        SegmentStatus.ERROR,
        SegmentStatus.DRAFTED,
        SegmentStatus.REFINED,
    },
    SegmentStatus.DRAFTED: {
        SegmentStatus.CRITIQUED,
        SegmentStatus.CONFLICT,
        SegmentStatus.ERROR,
        SegmentStatus.GENERATED,
    },
    SegmentStatus.CRITIQUED: {
        SegmentStatus.REFINED,
        SegmentStatus.CONFLICT,
        SegmentStatus.ERROR,
        SegmentStatus.GENERATED,
    },
    SegmentStatus.REFINED: {
        SegmentStatus.REVIEWED,
        SegmentStatus.APPROVED,
        SegmentStatus.CONFLICT,
        SegmentStatus.ERROR,
        SegmentStatus.GENERATED,
    },
    SegmentStatus.REVIEWED: {
        SegmentStatus.APPROVED,
        SegmentStatus.CONFLICT,
        SegmentStatus.REFINED,
        SegmentStatus.GENERATED,
    },
    SegmentStatus.APPROVED: {
        SegmentStatus.LOCKED,
        SegmentStatus.CONFLICT,
        SegmentStatus.REVIEWED,
        SegmentStatus.GENERATED,
    },
    SegmentStatus.LOCKED: {
        SegmentStatus.CONFLICT,
        SegmentStatus.APPROVED,
    },
    SegmentStatus.CONFLICT: {
        SegmentStatus.GENERATED,
        SegmentStatus.REFINED,
        SegmentStatus.REVIEWED,
        SegmentStatus.APPROVED,
    },
    SegmentStatus.ERROR: {
        SegmentStatus.GENERATED,
        SegmentStatus.CONFLICT,
    },
    SegmentStatus.DEPRECATED: set(),
}


class SegmentTransitionPolicy:
    """Validates explicit status transitions initiated by users or import."""

    @staticmethod
    def validate(
        from_status: SegmentStatus,
        to_status: SegmentStatus,
        *,
        force: bool = False,
    ) -> None:
        """Raise InvalidTransitionError when the transition is not permitted."""
        if from_status == to_status:
            return
        if from_status in IMMUTABLE_STATUSES:
            if from_status == SegmentStatus.DEPRECATED:
                raise InvalidTransitionError(from_status.value, to_status.value)
            if not force:
                raise InvalidTransitionError(from_status.value, to_status.value)
        if to_status == SegmentStatus.GENERATED and force:
            return
        allowed = _ALLOWED.get(from_status, set())
        if to_status not in allowed:
            raise InvalidTransitionError(from_status.value, to_status.value)

    @staticmethod
    def validate_human_authoring(
        from_status: SegmentStatus,
        to_status: SegmentStatus,
    ) -> None:
        """Validate a human authoring transition (edit/review supplies a translation)."""
        if from_status == to_status:
            return
        if from_status in IMMUTABLE_STATUSES:
            raise InvalidTransitionError(from_status.value, to_status.value)
        if to_status not in _HUMAN_AUTHORING_TARGETS:
            raise InvalidTransitionError(from_status.value, to_status.value)
