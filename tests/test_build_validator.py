"""Tests for BuildValidator placeholder drift detection."""

import pytest

from lilt.validation.validators import BuildValidator, ValidationError


def test_no_drift_when_mappings_match():
    mapping = {'<macro id="1"/>': "\\textbf{x}"}
    BuildValidator.validate_placeholder_mapping("seg1", mapping, dict(mapping))


def test_drift_raises_when_keys_differ():
    persisted = {'<macro id="1"/>': "\\textbf{x}"}
    fresh = {'<macro id="2"/>': "\\textbf{x}"}
    with pytest.raises(ValidationError, match="drift"):
        BuildValidator.validate_placeholder_mapping("seg1", persisted, fresh)
