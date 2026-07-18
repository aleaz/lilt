from lilt.core.translation.context_resolver import ContextResolver
from lilt.models.segment import SegmentStatus, StageArtifact, StoredSegment


def _seg(
    seg_id: str,
    translation: str = "",
    draft: str | None = None,
    refined: str | None = None,
) -> StoredSegment:
    return StoredSegment(
        id=seg_id,
        source_hash=f"hash-{seg_id}",
        source_text=f"source-{seg_id}",
        status=SegmentStatus.GENERATED,
        translation=translation,
        draft=StageArtifact(content=draft, model="m") if draft else None,
        refined=StageArtifact(content=refined, model="m") if refined else None,
    )


def test_context_resolver_zero_window_returns_empty():
    resolver = ContextResolver(0)
    segments = [_seg("a"), _seg("b", translation="tb")]
    idx = {s.id: i for i, s in enumerate(segments)}
    assert resolver.resolve_for_draft(segments[1], segments, idx) == {
        "backward": [],
        "forward": [],
    }


def test_context_resolver_prefers_translation_over_stale_refined():
    """Translation is authoritative; refined may be stale after re-translation."""
    resolver = ContextResolver(1)
    segments = [_seg("a", translation="ta", refined="ra"), _seg("b")]
    idx = {s.id: i for i, s in enumerate(segments)}
    ctx = resolver.resolve_for_refine(segments[1], segments, idx)
    assert ctx["backward"] == ["ta"]


def test_context_resolver_forward_window_for_critique():
    resolver = ContextResolver({"draft": 1, "critique": 1, "refine": 1})
    segments = [_seg("a"), _seg("b"), _seg("c", draft="dc")]
    idx = {s.id: i for i, s in enumerate(segments)}
    ctx = resolver.resolve_for_critique(segments[1], segments, idx)
    assert ctx["forward"] == ["dc"]
