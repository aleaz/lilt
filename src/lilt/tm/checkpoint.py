"""Translation-time persistence checkpoint over the TM JSONL store."""

import time

from lilt.models.segment import StoredSegment
from lilt.tm.repository import TMRepository, deduplicate_ordered_segments

__all__ = ["TranslationCheckpoint", "deduplicate_ordered_segments"]


class TranslationCheckpoint:
    """Durability boundary during translation.

    Contract:
    - Call :meth:`record_segment` after each segment mutation so progress survives
      process crashes (append-only JSONL).
    - Call :meth:`finalize_stage` once per workflow stage or sequential batch to
      compact duplicate lines via :func:`deduplicate_ordered_segments`.
    - Strategies own scheduling; this type only encapsulates TM persistence policy.
    """

    def __init__(self, repo: TMRepository) -> None:
        self._repo = repo
        self.last_record_ms: int | None = None

    def record_segment(self, namespace: str, segment: StoredSegment) -> int:
        """Append a single segment update for crash-safe incremental progress."""
        t0 = time.perf_counter()
        self._repo.append_segment(namespace, segment)
        self.last_record_ms = int((time.perf_counter() - t0) * 1000)
        return self.last_record_ms

    def finalize_stage(
        self, namespace: str, active_segments: list[StoredSegment]
    ) -> None:
        """Compact the namespace to one JSONL line per segment after a stage completes."""
        self._repo.save_namespace(namespace, active_segments)

    def record_and_finalize_if_last(
        self,
        namespace: str,
        segment: StoredSegment,
        active_segments: list[StoredSegment],
        *,
        is_last_in_batch: bool,
    ) -> int:
        """Append one segment and compact the namespace when the batch ends."""
        ms = self.record_segment(namespace, segment)
        if is_last_in_batch:
            t0 = time.perf_counter()
            self.finalize_stage(namespace, active_segments)
            ms += int((time.perf_counter() - t0) * 1000)
            self.last_record_ms = ms
        return ms
