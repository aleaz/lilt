"""Human review queue eligibility for translated segments."""

from lilt.models.segment import SegmentStatus, StoredSegment


class ReviewPolicy:
    """Defines which segment statuses enter the human review queue."""

    DEFAULT_QUEUE: tuple[SegmentStatus, ...] = (
        SegmentStatus.REFINED,
        SegmentStatus.REVIEWED,
    )

    def __init__(self, queue_statuses: list[SegmentStatus] | None = None) -> None:
        self.queue_statuses = list(queue_statuses or self.DEFAULT_QUEUE)

    def is_reviewable(self, segment: StoredSegment) -> bool:
        """Return True if the segment should appear in the review queue."""
        return segment.status in self.queue_statuses and bool(
            segment.translation.strip()
        )

    @classmethod
    def from_config(cls, config: dict) -> "ReviewPolicy":
        """Build a ReviewPolicy from the review section of lilt.yaml."""
        review_cfg = config.get("review", {})
        raw_statuses = review_cfg.get(
            "queue_statuses", [s.value for s in cls.DEFAULT_QUEUE]
        )
        queue = [SegmentStatus(str(s).lower()) for s in raw_statuses]
        return cls(queue)
