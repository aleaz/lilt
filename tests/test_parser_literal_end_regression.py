"""Regression for literal \\end{} leaking into masked text."""

from __future__ import annotations

from lilt.parser.ast_parser import LatexParser

LITERAL_END_RE = LatexParser.LITERAL_END_CMD_RE

# Minimal repro: \\end{...} inside prose must be masked or live only in opaque envs.
_DECOY_IN_PROSE = r"""
\documentclass{article}
\begin{document}
See \verb|\end{fake}| for an inline verbatim decoy.
\begin{lstlisting}
void trap() {
  // not a real \end{document}
}
\end{lstlisting}
\end{document}
"""


def test_literal_end_not_in_masked_text_for_verbatim_decoy() -> None:
    parser = LatexParser()
    blocks = parser.parse_text(_DECOY_IN_PROSE)
    for block in blocks:
        if not block.is_translatable():
            continue
        assert not LITERAL_END_RE.search(block.masked_text), block.masked_text


def test_lstlisting_decoy_in_prose_is_masked() -> None:
    parser = LatexParser()
    source = r"""
\documentclass{article}
\begin{document}
Do not confuse with \end{lstlisting} in running text.
\end{document}
"""
    blocks = parser.parse_text(source)
    translatable = [b for b in blocks if b.is_translatable()]
    assert translatable
    for block in translatable:
        if r"\end{lstlisting}" in block.raw_text:
            assert not LITERAL_END_RE.search(block.masked_text), block.masked_text
