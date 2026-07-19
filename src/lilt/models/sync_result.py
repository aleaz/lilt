"""Structured result of a TM synchronization operation."""

from dataclasses import dataclass, field

from lilt.models.segment import SegmentStatus, StoredSegment


@dataclass
class SyncResult:
    """Outcome metrics for syncing parsed blocks into a namespace."""

    namespace: str
    active_segments: list[StoredSegment] = field(default_factory=list)
    new_segments: int = 0
    updated_segments: int = 0
    new_conflicts: int = 0
    deprecated_marked: int = 0
    capacity_warnings: list[str] = field(default_factory=list)

    @property
    def total_active(self) -> int:
        """Return the number of non-deprecated active segments after sync."""
        return sum(
            1 for seg in self.active_segments if seg.status != SegmentStatus.DEPRECATED
        )
