"""Unit tests for the production PlaceholderEngine."""

from lilt.parser.placeholder_engine import PlaceholderEngine


def test_placeholder_engine_mask_ranges():
    engine = PlaceholderEngine()
    raw = r"Hello \textbf{world}"
    opaque_ranges = [(6, 14, "MACRO", r"\textbf{world}")]
    masked = engine.mask_ranges(raw, opaque_ranges, offset_start=0)

    assert masked != raw
    assert "<macro" in masked.lower()
