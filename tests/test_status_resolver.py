"""Tests for StatusResolver alias mapping."""

import pytest

from lilt.exceptions import InvalidStatusError
from lilt.models.segment import SegmentStatus
from lilt.models.status_resolver import StatusResolver


def test_resolve_untranslated_alias():
    assert StatusResolver.resolve("untranslated") == SegmentStatus.GENERATED


def test_resolve_enum_value():
    assert StatusResolver.resolve("conflict") == SegmentStatus.CONFLICT


def test_resolve_invalid_raises():
    with pytest.raises(InvalidStatusError):
        StatusResolver.resolve("not_a_status")


def test_matches_with_alias():
    assert StatusResolver.matches(SegmentStatus.GENERATED, "untranslated")
