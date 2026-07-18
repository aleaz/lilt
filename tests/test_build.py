import os
from unittest.mock import MagicMock

import pytest

from lilt.core.build import Builder
from lilt.exceptions import BuildError
from lilt.models.segment import SegmentStatus, StoredSegment


def test_builder_build_file(tmpdir):
    mock_tm = MagicMock()
    mock_parser = MagicMock()

    class FakeEngine:
        def unmask(self, text):
            return text.replace("unmasked_", "")

    class FakeBlock:
        def __init__(self, seg_id, raw_text, source_hash="a", translatable=True):
            self.id = seg_id
            self.raw_text = raw_text
            self.source_hash = source_hash
            self.engine = FakeEngine()
            self._translatable = translatable

        def is_translatable(self):
            return self._translatable

    mock_parser.parse_file.return_value = [
        FakeBlock("1", "Hello World\n"),
        FakeBlock("2", "Untranslated text\n"),
    ]

    seg1 = StoredSegment(
        id="1",
        source_hash="a",
        source_text="Hello World",
        status=SegmentStatus.APPROVED,
        translation="unmasked_Hola Mundo",
    )
    mock_tm.load_namespace.return_value = {"1": seg1}

    builder = Builder(tm=mock_tm, parser=mock_parser)

    out_file = os.path.join(tmpdir, "out.tex")
    builder.build_file("in.tex", out_file, "test_ns", allow_partial=True)

    with open(out_file, encoding="utf-8") as f:
        content = f.read()

    assert "Hola Mundo\n" in content
    assert "Untranslated text\n" in content


def test_builder_blocks_on_conflict_segment(tmpdir):
    mock_tm = MagicMock()
    mock_parser = MagicMock()

    class FakeBlock:
        def __init__(self, seg_id, raw_text, source_hash="a"):
            self.id = seg_id
            self.raw_text = raw_text
            self.source_hash = source_hash

        def is_translatable(self):
            return True

    mock_parser.parse_file.return_value = [FakeBlock("1", "Hello World\n")]

    seg1 = StoredSegment(
        id="1",
        source_hash="a",
        source_text="Hello World",
        status=SegmentStatus.CONFLICT,
        translation="Broken draft",
    )
    mock_tm.load_namespace.return_value = {"1": seg1}

    builder = Builder(tm=mock_tm, parser=mock_parser)
    out_file = os.path.join(tmpdir, "out.tex")

    with pytest.raises(BuildError, match="Build blocked"):
        builder.build_file("in.tex", out_file, "test_ns")


def test_builder_injections(tmpdir):
    mock_tm = MagicMock()
    mock_parser = MagicMock()

    class FakeBlock:
        def __init__(self, seg_id, raw_text):
            self.id = seg_id
            self.raw_text = raw_text

        def is_translatable(self):
            return False

    mock_parser.parse_file.return_value = [
        FakeBlock(
            "1", "\\documentclass{article}\n\\begin{document}\nTest\n\\end{document}"
        )
    ]
    mock_tm.load_namespace.return_value = {}

    builder = Builder(
        tm=mock_tm, parser=mock_parser, injections=["\\usepackage{babel}"]
    )

    out_file = os.path.join(tmpdir, "out.tex")
    builder.build_file("in.tex", out_file, "test_ns", allow_partial=True)

    with open(out_file, encoding="utf-8") as f:
        content = f.read()

    assert "\\documentclass{article}" in content
    assert "\\usepackage{babel}" in content


def test_builder_includes_locked_segment(tmpdir):
    mock_tm = MagicMock()
    mock_parser = MagicMock()

    class FakeBlock:
        def __init__(self, seg_id, raw_text, source_hash="a"):
            self.id = seg_id
            self.raw_text = raw_text
            self.source_hash = source_hash

        def is_translatable(self):
            return True

    mock_parser.parse_file.return_value = [FakeBlock("1", "Hello World\n")]

    seg1 = StoredSegment(
        id="1",
        source_hash="a",
        source_text="Hello World",
        status=SegmentStatus.LOCKED,
        translation="Hola Mundo",
    )
    mock_tm.load_namespace.return_value = {"1": seg1}

    builder = Builder(tm=mock_tm, parser=mock_parser)
    out_file = os.path.join(tmpdir, "out.tex")
    builder.build_file("in.tex", out_file, "test_ns", allow_partial=True)

    with open(out_file, encoding="utf-8") as f:
        content = f.read()

    assert "Hola Mundo\n" in content


def test_builder_empty_map_with_uppercase_placeholder_raises(tmpdir):
    mock_tm = MagicMock()
    mock_parser = MagicMock()

    class FakeEngine:
        mapping: dict = {}

    class FakeBlock:
        def __init__(self):
            self.id = "1"
            self.raw_text = "See X\n"
            self.source_hash = "a"
            self.engine = FakeEngine()

        def is_translatable(self):
            return True

    mock_parser.parse_file.return_value = [FakeBlock()]
    seg1 = StoredSegment(
        id="1",
        source_hash="a",
        source_text='See <MACRO id="1"/>',
        status=SegmentStatus.APPROVED,
        translation="See Y",
        placeholders={},
    )
    mock_tm.load_namespace.return_value = {"1": seg1}
    builder = Builder(tm=mock_tm, parser=mock_parser)
    out_file = os.path.join(tmpdir, "out.tex")
    with pytest.raises(BuildError, match="no placeholder mapping"):
        builder.build_file("in.tex", out_file, "test_ns")
