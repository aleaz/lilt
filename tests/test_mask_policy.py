"""Tests for macro mask policies."""

from lilt.parser.ast_parser import LatexParser


def test_textcolor_masks_color_not_body():
    parser = LatexParser()
    blocks = parser.parse_text(r"\textcolor{red}{Hello}")
    assert blocks
    masked = blocks[0].masked_text
    assert "Hello" in masked
    assert "red" not in masked
