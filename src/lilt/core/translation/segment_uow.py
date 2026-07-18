"""Per-segment translation durability with interrupt-safe rollback."""

from collections.abc import Generator
from contextlib import contextmanager

from lilt.exceptions import PreconditionError
from lilt.models.segment import StoredSegment
from lilt.tm.checkpoint import TranslationCheckpoint


@contextmanager
def process_segment(
    checkpoint: TranslationCheckpoint,
    namespace: str,
    seg: StoredSegment,
    active_segments: list[StoredSegment],
    *,
    is_last: bool,
) -> Generator[StoredSegment]:
    """Run one segment mutation inside a durability boundary.

    On KeyboardInterrupt, restores the pre-mutation snapshot before persisting.
    On PreconditionError, rolls back and skips persistence to avoid duplicate TM lines.
    """
    snapshot = seg.model_copy(deep=True)
    persist = True
    try:
        yield seg
    except KeyboardInterrupt:
        _restore_segment(seg, snapshot, active_segments)
        persist = False
        raise
    except PreconditionError:
        _restore_segment(seg, snapshot, active_segments)
        persist = False
        raise
    finally:
        if persist:
            checkpoint.record_and_finalize_if_last(
                namespace,
                seg,
                active_segments,
                is_last_in_batch=is_last,
            )


def _restore_segment(
    seg: StoredSegment,
    snapshot: StoredSegment,
    active_segments: list[StoredSegment],
) -> None:
    for idx, candidate in enumerate(active_segments):
        if candidate.id == seg.id:
            restored = snapshot.model_copy(deep=True)
            active_segments[idx] = restored
            for field_name in StoredSegment.model_fields:
                setattr(seg, field_name, getattr(restored, field_name))
            return
