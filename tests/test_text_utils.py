from lilt.parser.linguistic import has_linguistic_content


def test_has_linguistic_content():
    # Basic text
    assert has_linguistic_content("Hello world")
    assert has_linguistic_content("Hola mundo")

    # Text with placeholders
    assert has_linguistic_content('See Figure <ref id="1"/> for details.')

    # Pure placeholders
    assert not has_linguistic_content('<macro id="1"/>')
    assert not has_linguistic_content('<math id="1"/> . <math id="2"/>')

    # Numbers and punctuation
    assert not has_linguistic_content("123.45")
    assert not has_linguistic_content("( ) - , .")

    # International characters
    assert has_linguistic_content("你好")  # Chinese
    assert has_linguistic_content("مرحبا")  # Arabic
    assert has_linguistic_content(
        '<math id="1"/> 日本語 <ref id="2"/>'
    )  # Japanese with placeholders


def test_has_linguistic_content_rejects_sty_macro_shards():
    """Masked jmlr2e.sty fragments must not qualify as translatable prose."""
    assert not has_linguistic_content(
        '<block id="1"/>plainnat<block id="2"/>(<block id="3"/>)'
        '<block id="4"/>;<block id="5"/>a<block id="6"/>,<block id="7"/>,'
        '<group_end id="1"/>'
    )
    assert not has_linguistic_content(
        '<macro id="15"/>.25in    <block id="1"/>.25in\n'
        '<macro id="13"/>0.07 true in\n<block id="2"/>-0.5in\n'
        '<block id="3"/>0.25in<block id="4"/>8.5 true in       '
        '<block id="5"/>6.0 true in        <block id="6"/>=10000\n'
        '<macro id="6"/>=10000\n'
        '<macro id="5"/>twosidetrue <macro id="4"/>mparswitchtrue '
        '<block id="7"/>@draft<block id="8"/>5pt<group_end id="1"/>'
    )
    assert not has_linguistic_content(
        '<block id="1"/>startsiction#1#2#3#4#5#6<block id="2"/>@noskipsec '
        '<block id="3"/>tempskipa #4<block id="4"/>afterindenttrue'
    )
    assert not has_linguistic_content(
        '<block id="1"/>section<block id="2"/>.<block id="3"/>subsection<block id="4"/>'
    )
    assert not has_linguistic_content(
        '<block id="1"/>sict#1#2#3#4#5#6[#7]#8<block id="2"/>#2>'
        '<macro id="55"/>secnumdepth\n     <block id="3"/>svsec'
    )


def test_has_linguistic_content_accepts_short_section_titles() -> None:
    assert has_linguistic_content(
        r'\section<group_start id="1"/>Introduction<group_end id="1"/>'
    )
    assert has_linguistic_content(
        r'\section<group_start id="1"/>Conclusion<group_end id="1"/>'
    )
    assert has_linguistic_content(
        r'\caption<group_start id="1"/>Fig. 1<group_end id="1"/>'
    )
