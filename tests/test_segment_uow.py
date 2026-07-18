"""Tests for segment unit-of-work interrupt handling."""

from unittest.mock import MagicMock

import pytest

from lilt.core.translation.segment_uow import process_segment
from lilt.exceptions import PreconditionError
from lilt.models.segment import SegmentStatus, StoredSegment
from lilt.tm.checkpoint import TranslationCheckpoint


def test_process_segment_restores_on_keyboard_interrupt():
    repo = MagicMock()
    checkpoint = TranslationCheckpoint(repo)
    seg = StoredSegment(
        id="abc",
        source_hash="h",
        source_text="Hello",
        status=SegmentStatus.GENERATED,
        translation="",
    )
    active = [seg]
    with (
        pytest.raises(KeyboardInterrupt),
        process_segment(checkpoint, "ns", seg, active, is_last=True),
    ):
        seg.translation = "partial"
        raise KeyboardInterrupt

    assert seg.translation == ""
    repo.append_segment.assert_not_called()


def test_process_segment_skips_persist_on_precondition_error():
    repo = MagicMock()
    checkpoint = TranslationCheckpoint(repo)
    seg = StoredSegment(
        id="abc",
        source_hash="h",
        source_text="Hello",
        status=SegmentStatus.GENERATED,
        translation="",
    )
    active = [seg]
    with (
        pytest.raises(PreconditionError),
        process_segment(checkpoint, "ns", seg, active, is_last=False),
    ):
        raise PreconditionError("missing draft")

    repo.append_segment.assert_not_called()
