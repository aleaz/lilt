"""Tests for safe \\end{env} detection outside verbatim/comments."""

from lilt.parser.ast_parser import LatexParser
from lilt.parser.roundtrip import verify_lossless_roundtrip


def _masked_for_body(blocks: list, needle: str) -> str:
    for block in blocks:
        if needle in block.raw_text:
            return block.masked_text
    raise AssertionError(f"No block containing {needle!r}")


def test_env_end_ignores_verb_decoy() -> None:
    source = r"""\begin{document}
\verb|\end{document}|
Real body text here.
\end{document}"""
    parser = LatexParser()
    blocks = parser.parse_text(source)
    masked = _masked_for_body(blocks, "Real body")

    assert r"\end{document}" not in masked
    assert "<end_env" in masked
    verify_lossless_roundtrip(source, blocks)


def test_env_end_ignores_comment_decoy() -> None:
    source = r"""\begin{document}
% \end{document}
Real body text here.
\end{document}"""
    parser = LatexParser()
    blocks = parser.parse_text(source)
    masked = _masked_for_body(blocks, "Real body")

    assert r"\end{document}" not in masked
    assert "<end_env" in masked
    verify_lossless_roundtrip(source, blocks)


def test_env_end_ignores_lstlisting_decoy() -> None:
    source = r"""\begin{document}
\begin{lstlisting}
\end{document}
\end{lstlisting}
Real body text here.
\end{document}"""
    parser = LatexParser()
    blocks = parser.parse_text(source)
    masked = _masked_for_body(blocks, "Real body")

    assert r"\end{document}" not in masked
    assert "<end_env" in masked
    verify_lossless_roundtrip(source, blocks)


def test_env_end_ignores_verb_decoy_in_abstract() -> None:
    source = r"""\begin{abstract}
\verb|\end{abstract}|
Abstract body text.
\end{abstract}"""
    parser = LatexParser()
    blocks = parser.parse_text(source)
    masked = _masked_for_body(blocks, "Abstract body")

    assert r"\end{abstract}" not in masked
    assert "<end_env" in masked
    verify_lossless_roundtrip(source, blocks)
