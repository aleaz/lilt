"""Regression tests for xv6-style listings and lineref patterns."""

from __future__ import annotations

import pytest

from lilt.parser.ast_parser import LatexParser
from lilt.parser.roundtrip import verify_lossless_roundtrip

SOURCE_FIXTURE = r"""
\begin{document}
Here is some text.
\begin{lstlisting}
int main() {
    // This is a comment containing \end{lstlisting} which should be ignored by standard parsing if literal, but handled by fallback if dirty.
    return 0;
}
\end{lstlisting}
And more text to translate.
\end{document}
"""


@pytest.fixture
def source() -> str:
    return SOURCE_FIXTURE


def test_xv6_listings_fixture_roundtrip(source: str) -> None:
    parser = LatexParser()
    blocks = parser.parse_text(source)
    verify_lossless_roundtrip(source, blocks)


def test_xv6_listings_no_literal_end_in_masked(source: str) -> None:
    parser = LatexParser()
    blocks = parser.parse_text(source)
    for block in blocks:
        assert r"\end{lstlisting}" not in block.masked_text


def test_xv6_listings_has_translatable_segments(source: str) -> None:
    parser = LatexParser()
    blocks = parser.parse_text(source)
    assert sum(1 for b in blocks if b.is_translatable()) >= 1
