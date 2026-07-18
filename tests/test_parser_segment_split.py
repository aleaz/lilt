"""Parser regression tests for dense segment splitting."""

from lilt.parser.ast_parser import LatexParser


def test_noindent_emph_paragraphs_are_split() -> None:
    tex = (
        "\\begin{document}\n"
        "\\noindent\\emph{First paragraph.}\n"
        "\\noindent\\emph{Second paragraph.}\n"
        "\\end{document}\n"
    )
    parser = LatexParser()
    blocks = parser.parse_text(tex)
    translatable = [block for block in blocks if block.is_translatable()]
    assert len(translatable) == 2
