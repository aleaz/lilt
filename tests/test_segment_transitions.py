from lilt.models.segment import SegmentStatus, StoredSegment


def _seg() -> StoredSegment:
    return StoredSegment(
        id="x",
        source_hash="h",
        source_text="Hello",
        status=SegmentStatus.GENERATED,
        translation="Old",
    )


def test_apply_successful_translation_appends_history():
    seg = _seg()
    seg.apply_successful_translation("Hola")
    assert seg.translation == "Hola"
    assert seg.status == SegmentStatus.REFINED
    assert len(seg.history) == 1


def test_mark_validation_conflict_sets_conflict_for_sequential():
    seg = _seg()
    seg.mark_validation_conflict("partial")
    assert seg.status == SegmentStatus.CONFLICT
    assert seg.translation == "partial"


def test_mark_validation_conflict_sets_refined_on_refine_stage():
    seg = _seg()
    seg.mark_validation_conflict(
        "partial refined", stage="refine", refine_model="gpt-4o"
    )
    assert seg.status == SegmentStatus.CONFLICT
    assert seg.refined is not None
    assert seg.refined.content == "partial refined"
    assert seg.translation == "partial refined"


def test_mark_infrastructure_error_sets_error_meta():
    seg = _seg()
    seg.mark_infrastructure_error(RuntimeError("timeout"))
    assert seg.status == SegmentStatus.ERROR
    assert seg.error_meta is not None
    assert seg.error_meta.error_type == "RuntimeError"
