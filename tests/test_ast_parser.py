from pylatexenc.macrospec import MacroSpec

from lilt.parser.ast_parser import LatexParser
from lilt.parser.roundtrip import verify_lossless_roundtrip


def test_ast_parser_masks_macro_with_args():
    parser = LatexParser()
    parser.custom_macros.add("lineref")

    parser.db.add_context_category(
        "lilt_custom", macros=[MacroSpec("lineref", args_parser="{")]
    )

    latex_text = r"El código está en \lineref{kernel/trap.c}."

    blocks = parser.parse_text(latex_text)
    block = blocks[0]
    masked_text = block.masked_text
    placeholder_map = block.engine.mapping

    # \lineref{kernel/trap.c} should be masked entirely since translatable=False by default for opaque macros
    # Actually, if it's not in transparent_macros, it's fully masked.
    assert '<macro id="1"/>' in masked_text
    assert "kernel/trap.c" not in masked_text
    assert placeholder_map['<macro id="1"/>'] == r"\lineref{kernel/trap.c}"
    assert masked_text == 'El código está en <macro id="1"/>.'


def test_ast_parser_transparent_macro():
    parser = LatexParser()
    parser.inline_transparent_macros.add("textbf")

    latex_text = r"Este texto es \textbf{negrita}."
    blocks = parser.parse_text(latex_text)
    masked_text = blocks[0].masked_text

    # \textbf should be transparent. Its arguments should be traversed,
    # but the macro itself and braces should be masked as GROUP_START / GROUP_END?
    # Actually, inline_transparent_macros just traverses arguments.
    assert "negrita" in masked_text


def test_ast_parser_malformed_group_closes():
    parser = LatexParser()
    parser.inline_transparent_macros.add("textbf")

    # The input has a missing closing brace '}'
    latex_text = r"Este texto es \textbf{negrita"
    blocks = parser.parse_text(latex_text)
    masked_text = blocks[0].masked_text
    mapping = blocks[0].engine.mapping

    # Verify we did not destructively mask the last character 'a' as GROUP_END
    assert "a" not in mapping.values()
    assert "negrita" in masked_text
    # We should have GROUP_START '{' masked but no GROUP_END
    assert '<group_start id="1"/>' in masked_text
    assert '<group_end id="1"/>' not in masked_text


def test_boundaries_never_split_opaque_ranges():
    """Paragraph gaps inside opaque spans must not split masking ranges."""
    parser = LatexParser()
    source = (
        r"\begin{document}" + "\n\n" + r"\section{Title}" + "\n\n"
        r"Body paragraph." + "\n" + r"\end{document}"
    )
    blocks = parser.parse_text(source)

    verify_lossless_roundtrip(source, blocks)
    combined_masked = "".join(block.masked_text for block in blocks)
    assert r"\end{document}" not in combined_masked
    assert "<end_env" in combined_masked.lower()
