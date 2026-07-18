import os
import tempfile

from lilt.models.segment import SegmentStatus, StoredSegment
from lilt.tm.checkpoint import TranslationCheckpoint, deduplicate_ordered_segments
from lilt.tm.repository import TMRepository


def _make_segment(seg_id: str, text: str, translation: str = "") -> StoredSegment:
    return StoredSegment(
        id=seg_id,
        source_hash=f"hash-{seg_id}",
        source_text=text,
        status=SegmentStatus.GENERATED,
        translation=translation,
    )


def test_record_segment_last_wins_on_load():
    with tempfile.TemporaryDirectory() as tmpdir:
        repo = TMRepository(base_dir=tmpdir)
        checkpoint = TranslationCheckpoint(repo)
        namespace = "ns"
        seg = _make_segment("a", "Hello")

        repo.save_namespace(namespace, [seg])
        seg.translation = "Hola v1"
        checkpoint.record_segment(namespace, seg)
        seg.translation = "Hola v2"
        checkpoint.record_segment(namespace, seg)

        loaded = repo.load_namespace(namespace)
        assert loaded["a"].translation == "Hola v2"


def test_finalize_stage_compacts_to_one_line_per_segment():
    with tempfile.TemporaryDirectory() as tmpdir:
        repo = TMRepository(base_dir=tmpdir)
        checkpoint = TranslationCheckpoint(repo)
        namespace = "ns"
        seg = _make_segment("a", "Hello")

        repo.save_namespace(namespace, [seg])
        seg.translation = "Hola"
        checkpoint.record_segment(namespace, seg)
        checkpoint.finalize_stage(namespace, [seg])

        filepath = repo._get_filepath(namespace)
        with open(filepath, encoding="utf-8") as handle:
            lines = [line for line in handle if line.strip()]
        assert len(lines) == 1
        assert repo.load_namespace(namespace)["a"].translation == "Hola"


def test_crash_recovery_without_finalize():
    with tempfile.TemporaryDirectory() as tmpdir:
        repo = TMRepository(base_dir=tmpdir)
        checkpoint = TranslationCheckpoint(repo)
        namespace = "ns"
        seg = _make_segment("a", "Hello")

        repo.save_namespace(namespace, [seg])
        seg.translation = "Partial"
        checkpoint.record_segment(namespace, seg)

        loaded = repo.load_namespace(namespace)
        assert loaded["a"].translation == "Partial"


def test_deduplicate_ordered_segments_keeps_latest_and_order():
    first = _make_segment("a", "A1")
    second = _make_segment("b", "B")
    first_updated = _make_segment("a", "A2")
    first_updated.translation = "ta2"

    deduped = deduplicate_ordered_segments([first, second, first_updated])
    assert [seg.id for seg in deduped] == ["a", "b"]
    assert deduped[0].source_text == "A2"
    assert deduped[0].translation == "ta2"


def test_record_and_finalize_if_last_compacts_on_last_segment():
    with tempfile.TemporaryDirectory() as tmpdir:
        repo = TMRepository(base_dir=tmpdir)
        checkpoint = TranslationCheckpoint(repo)
        namespace = "ns"
        seg_a = _make_segment("a", "Hello")
        seg_b = _make_segment("b", "World")
        repo.save_namespace(namespace, [seg_a, seg_b])

        seg_a.translation = "Hola"
        checkpoint.record_and_finalize_if_last(
            namespace, seg_a, [seg_a, seg_b], is_last_in_batch=False
        )
        seg_b.translation = "Mundo"
        checkpoint.record_and_finalize_if_last(
            namespace, seg_b, [seg_a, seg_b], is_last_in_batch=True
        )

        filepath = repo._get_filepath(namespace)
        with open(filepath, encoding="utf-8") as handle:
            lines = [line for line in handle if line.strip()]
        assert len(lines) == 2
        loaded = repo.load_namespace(namespace)
        assert loaded["a"].translation == "Hola"
        assert loaded["b"].translation == "Mundo"


def test_sync_uses_deduplicated_order_for_alignment():
    with tempfile.TemporaryDirectory() as tmpdir:
        repo = TMRepository(base_dir=tmpdir)
        namespace = "ns"
        seg = _make_segment("a", "Hello")
        repo.save_namespace(namespace, [seg])

        seg.translation = "Hola"
        repo.append_segment(namespace, seg)

        ordered = repo.load_namespace_report(namespace).ordered_segments
        assert len(ordered) == 2
        assert len(deduplicate_ordered_segments(ordered)) == 1

        filepath = repo._get_filepath(namespace)
        assert os.path.exists(filepath)


def test_finalize_stage_after_workflow_stage_prevents_duplicate_lines():
    with tempfile.TemporaryDirectory() as tmpdir:
        repo = TMRepository(base_dir=tmpdir)
        checkpoint = TranslationCheckpoint(repo)
        namespace = "ns"
        seg_a = _make_segment("a", "Hello")
        seg_b = _make_segment("b", "World")
        repo.save_namespace(namespace, [seg_a, seg_b])

        seg_a.status = SegmentStatus.DRAFTED
        seg_a.translation = "Hola"
        checkpoint.record_segment(namespace, seg_a)
        checkpoint.finalize_stage(namespace, [seg_a, seg_b])

        filepath = repo._get_filepath(namespace)
        with open(filepath, encoding="utf-8") as handle:
            lines = [line for line in handle if line.strip()]
        assert len(lines) == 2
