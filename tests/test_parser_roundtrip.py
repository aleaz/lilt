from pathlib import Path

from lilt.parser.ast_parser import LatexParser
from lilt.parser.roundtrip import verify_lossless_roundtrip

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_parse_text_preserves_whitespace_gaps():
    source = "First paragraph.\n\nSecond paragraph."
    parser = LatexParser()
    blocks = parser.parse_text(source)

    verify_lossless_roundtrip(source, blocks)
    translatable = [b for b in blocks if b.is_translatable()]
    assert len(translatable) == 2


def test_whitespace_only_block_not_translatable():
    parser = LatexParser()
    blocks = parser.parse_text("\n\n")
    assert len(blocks) == 1
    assert blocks[0].raw_text == "\n\n"
    assert not blocks[0].is_translatable()
    assert blocks[0].masked_text == "\n\n"
