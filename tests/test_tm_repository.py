"""TM repository sync and durability tests."""

import tempfile
from unittest.mock import MagicMock

from lilt.core.sync import sync_parsed_blocks
from lilt.models.segment import SegmentStatus, StageArtifact, StoredSegment
from lilt.parser.ast_parser import LatexParser
from lilt.tm.repository import TMRepository
from lilt.tm.source_change import SourceChangePolicy


def test_tm_sync() -> None:
    """Sync parsed blocks into JSONL and verify deprecation retention."""
    tex = r"""
\documentclass{article}
\begin{document}
First paragraph with enough prose to be a segment.

Second paragraph also has enough linguistic content here.
\end{document}
"""
    with tempfile.TemporaryDirectory() as tmpdir:
        tex_path = f"{tmpdir}/main.tex"
        with open(tex_path, "w", encoding="utf-8") as f:
            f.write(tex)

        parser = LatexParser()
        blocks = parser.parse_file(tex_path)
        translatable_blocks = [b for b in blocks if b.is_translatable()]
        assert len(translatable_blocks) >= 2

        repo = TMRepository(base_dir=tmpdir)
        with repo.namespace_session("unix"):
            result = sync_parsed_blocks("unix", blocks, repo)
        active_segments = result.active_segments

        assert len(active_segments) == len(translatable_blocks)

        jsonl_path = f"{tmpdir}/unix.jsonl"
        with open(jsonl_path, encoding="utf-8") as _:
            pass

        loaded_segments = repo.load_namespace("unix")
        assert len(loaded_segments) == len(translatable_blocks)

        first_key = list(loaded_segments.keys())[0]
        first_seg = loaded_segments[first_key]
        assert first_seg.status == SegmentStatus.GENERATED
        assert first_seg.translation == ""
        assert first_seg.source_text != ""

        blocks_without_first = [
            b for b in blocks if b.is_translatable() and b.id != first_key
        ]
        # Keep non-translatable blocks so parse shape stays coherent for sync helper
        reduced = [b for b in blocks if not b.is_translatable() or b.id != first_key]
        with repo.namespace_session("unix"):
            sync_parsed_blocks("unix", reduced, repo)

        loaded_segments_after = repo.load_namespace("unix")
        assert len(loaded_segments_after) == len(translatable_blocks)
        assert loaded_segments_after[first_key].status == SegmentStatus.DEPRECATED
        active_only = [
            s
            for s in loaded_segments_after.values()
            if s.status != SegmentStatus.DEPRECATED
        ]
        assert len(active_only) == len(blocks_without_first)


def test_tm_append():
    with tempfile.TemporaryDirectory() as tmpdir:
        repo = TMRepository(base_dir=tmpdir)

        seg = StoredSegment(
            id="test-1",
            source_hash="hash-1",
            source_text="Hello",
            status=SegmentStatus.GENERATED,
            translation="",
        )

        repo.save_namespace("test_ns", [seg])

        seg.translation = "Hola"
        seg.status = SegmentStatus.REVIEWED
        repo.append_segment("test_ns", seg)

        loaded = repo.load_namespace("test_ns")
        assert "test-1" in loaded
        assert loaded["test-1"].translation == "Hola"
        assert loaded["test-1"].status == SegmentStatus.REVIEWED

        filepath = repo._get_filepath("test_ns")
        with open(filepath) as f:
            lines = f.readlines()
            assert len(lines) == 2


def _make_block(seg_id: str, masked_text: str, source_hash: str = "hash"):
    """Helper to build a minimal SegmentBlock for sync tests."""
    block = MagicMock()
    block.id = seg_id
    block.masked_text = masked_text
    block.source_hash = source_hash
    block.is_translatable.return_value = True
    block.engine.mapping = {}
    return block


def test_sync_locked_source_change_sets_conflict_preserves_translation():
    with tempfile.TemporaryDirectory() as tmpdir:
        repo = TMRepository(base_dir=tmpdir)
        seg = StoredSegment(
            id="locked-1",
            source_hash="old-hash",
            source_text="Old source",
            status=SegmentStatus.LOCKED,
            translation="Traduccion bloqueada",
        )
        repo.save_namespace("ns", [seg])

        blocks = [_make_block("locked-1", "New source", "new-hash")]
        result = sync_parsed_blocks("ns", blocks, repo)
        active = result.active_segments
        conflicts = result.new_conflicts

        loaded = repo.load_namespace("ns")["locked-1"]
        assert loaded.status == SegmentStatus.CONFLICT
        assert loaded.translation == "Traduccion bloqueada"
        assert loaded.source_text == "New source"
        assert conflicts == 1
        assert len(active) == 1


def test_sync_approved_source_change_sets_conflict():
    with tempfile.TemporaryDirectory() as tmpdir:
        repo = TMRepository(base_dir=tmpdir)
        seg = StoredSegment(
            id="approved-1",
            source_hash="old-hash",
            source_text="Old source",
            status=SegmentStatus.APPROVED,
            translation="Traduccion aprobada",
        )
        repo.save_namespace("ns", [seg])

        blocks = [_make_block("approved-1", "New source", "new-hash")]
        conflicts = sync_parsed_blocks("ns", blocks, repo).new_conflicts

        loaded = repo.load_namespace("ns")["approved-1"]
        assert loaded.status == SegmentStatus.CONFLICT
        assert loaded.translation == "Traduccion aprobada"
        assert conflicts == 1


def test_sync_reviewed_source_change_sets_conflict():
    with tempfile.TemporaryDirectory() as tmpdir:
        repo = TMRepository(base_dir=tmpdir)
        seg = StoredSegment(
            id="reviewed-1",
            source_hash="old-hash",
            source_text="Old source",
            status=SegmentStatus.REVIEWED,
            translation="Traduccion revisada",
        )
        repo.save_namespace("ns", [seg])

        blocks = [_make_block("reviewed-1", "New source", "new-hash")]
        conflicts = sync_parsed_blocks("ns", blocks, repo).new_conflicts

        loaded = repo.load_namespace("ns")["reviewed-1"]
        assert loaded.status == SegmentStatus.CONFLICT
        assert loaded.translation == "Traduccion revisada"
        assert conflicts == 1


def test_sync_refined_source_change_resets_to_generated():
    with tempfile.TemporaryDirectory() as tmpdir:
        repo = TMRepository(base_dir=tmpdir)

        seg = StoredSegment(
            id="refined-1",
            source_hash="old-hash",
            source_text="Old source",
            status=SegmentStatus.REFINED,
            translation="Traduccion LLM",
            draft=StageArtifact(content="draft", model="m"),
            refined=StageArtifact(content="refined", model="m"),
        )
        repo.save_namespace("ns", [seg])

        blocks = [_make_block("refined-1", "New source", "new-hash")]
        sync_parsed_blocks("ns", blocks, repo)

        loaded = repo.load_namespace("ns")["refined-1"]
        assert loaded.status == SegmentStatus.GENERATED
        assert loaded.translation == ""
        assert loaded.draft is None
        assert loaded.refined is None


def test_sync_unchanged_source_preserves_status():
    with tempfile.TemporaryDirectory() as tmpdir:
        repo = TMRepository(base_dir=tmpdir)
        seg = StoredSegment(
            id="stable-1",
            source_hash="same-hash",
            source_text="Same source",
            status=SegmentStatus.APPROVED,
            translation="Traduccion",
        )
        repo.save_namespace("ns", [seg])

        blocks = [_make_block("stable-1", "Same source", "same-hash")]
        conflicts = sync_parsed_blocks("ns", blocks, repo).new_conflicts

        loaded = repo.load_namespace("ns")["stable-1"]
        assert loaded.status == SegmentStatus.APPROVED
        assert loaded.translation == "Traduccion"
        assert conflicts == 0


def test_deprecated_revival_invalid_translation_resets_to_generated():
    seg = StoredSegment(
        id="dep1",
        source_hash="dep1",
        source_text='Hello <macro id="1"/>',
        status=SegmentStatus.DEPRECATED,
        translation="Hola sin placeholder",
        history=[],
    )
    SourceChangePolicy.apply(
        seg,
        'Hello <macro id="1"/>',
        "dep1",
        {'<macro id="1"/>': "\\foo{}"},
    )
    assert seg.status == SegmentStatus.GENERATED
    assert seg.translation == ""
