"""Tests for segment status transition policy."""

import pytest

from lilt.exceptions import InvalidTransitionError
from lilt.models.segment import SegmentStatus
from lilt.models.segment_transition import SegmentTransitionPolicy


def test_allows_refined_to_reviewed():
    SegmentTransitionPolicy.validate(SegmentStatus.REFINED, SegmentStatus.REVIEWED)


def test_rejects_deprecated_to_approved():
    with pytest.raises(InvalidTransitionError):
        SegmentTransitionPolicy.validate(
            SegmentStatus.DEPRECATED, SegmentStatus.APPROVED
        )


def test_force_reset_to_generated():
    SegmentTransitionPolicy.validate(
        SegmentStatus.APPROVED, SegmentStatus.GENERATED, force=True
    )


def test_deprecated_rejects_all_transitions_with_force():
    with pytest.raises(InvalidTransitionError):
        SegmentTransitionPolicy.validate(
            SegmentStatus.DEPRECATED, SegmentStatus.GENERATED, force=True
        )


def test_locked_requires_force():
    with pytest.raises(InvalidTransitionError):
        SegmentTransitionPolicy.validate(SegmentStatus.LOCKED, SegmentStatus.APPROVED)


def test_locked_allows_transition_with_force():
    SegmentTransitionPolicy.validate(
        SegmentStatus.LOCKED, SegmentStatus.APPROVED, force=True
    )


def test_human_authoring_allows_generated_to_approved():
    SegmentTransitionPolicy.validate_human_authoring(
        SegmentStatus.GENERATED, SegmentStatus.APPROVED
    )


def test_human_authoring_allows_refined_to_approved():
    SegmentTransitionPolicy.validate_human_authoring(
        SegmentStatus.REFINED, SegmentStatus.APPROVED
    )


def test_human_authoring_allows_reviewed_to_conflict():
    SegmentTransitionPolicy.validate_human_authoring(
        SegmentStatus.REVIEWED, SegmentStatus.CONFLICT
    )


def test_human_authoring_rejects_locked_to_approved():
    with pytest.raises(InvalidTransitionError):
        SegmentTransitionPolicy.validate_human_authoring(
            SegmentStatus.LOCKED, SegmentStatus.APPROVED
        )


def test_human_authoring_rejects_deprecated_to_approved():
    with pytest.raises(InvalidTransitionError):
        SegmentTransitionPolicy.validate_human_authoring(
            SegmentStatus.DEPRECATED, SegmentStatus.APPROVED
        )


def test_human_authoring_rejects_to_drafted():
    with pytest.raises(InvalidTransitionError):
        SegmentTransitionPolicy.validate_human_authoring(
            SegmentStatus.GENERATED, SegmentStatus.DRAFTED
        )
