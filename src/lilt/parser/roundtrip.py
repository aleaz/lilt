"""Lossless roundtrip verification for parsed LaTeX segments."""

from __future__ import annotations

from lilt.parser.ast_parser import SegmentBlock


def verify_lossless_roundtrip(source: str, blocks: list[SegmentBlock]) -> None:
    """Assert that concatenating block raw_text reproduces source byte-for-byte."""
    reconstructed = "".join(block.raw_text for block in blocks)
    if reconstructed == source:
        return

    min_len = min(len(reconstructed), len(source))
    offset = min_len
    for i in range(min_len):
        if reconstructed[i] != source[i]:
            offset = i
            break

    raise ValueError(
        f"Lossless roundtrip failed at offset {offset}: "
        f"expected {len(source)} bytes, got {len(reconstructed)} bytes"
    )
