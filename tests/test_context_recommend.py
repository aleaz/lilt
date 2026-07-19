"""Tests for post-sync context capacity recommendation."""

from lilt.llm.context_recommend import (
    format_capacity_warnings,
    recommend_context_limits,
)
from lilt.llm.openai_provider import OpenAIProvider
from lilt.models.cost_plane import build_reflection_cost_plane
from lilt.models.segment import SegmentStatus, StoredSegment


def _seg(sid: str, text: str) -> StoredSegment:
    return StoredSegment(
        id=sid,
        source_text=text,
        source_hash=f"hash-{sid}",
        status=SegmentStatus.GENERATED,
    )


def test_recommend_min_full_ge_min_bare():
    plane = build_reflection_cost_plane(cost_profile="balanced")
    provider = OpenAIProvider(
        api_key="test",
        base_url="http://test",
        model_context_limit=8192,
        max_tokens=2048,
        cost_plane=plane,
    )
    segments = [
        _seg("a", "alpha " * 40),
        _seg("b", "bravo " * 40),
        _seg("c", "charlie " * 40),
        _seg("d", "delta " * 40),
    ]
    report = recommend_context_limits(segments, provider, configured_limit=8192)
    assert "draft" in report.stages
    for stage in report.stages.values():
        assert stage.min_full_neighbors >= stage.min_bare
    assert report.recommend_min >= report.stages["draft"].min_bare
    assert report.verdict in {
        "ok",
        "raise_config",
        "oversized_vs_need",
        "bare_infeasible",
    }


def test_raise_config_when_limit_too_small():
    plane = build_reflection_cost_plane(cost_profile="balanced")
    provider = OpenAIProvider(
        api_key="test",
        base_url="http://test",
        model_context_limit=4096,
        max_tokens=2048,
        cost_plane=plane,
    )
    segments = [_seg(f"s{i}", ("word " * 80) + f"seg{i}") for i in range(6)]
    report = recommend_context_limits(segments, provider, configured_limit=2048)
    assert report.configured_limit == 2048
    warnings = format_capacity_warnings(report)
    if report.verdict == "raise_config" or report.neighbors_truncated_under_configured:
        assert warnings
    assert report.recommend_min >= report.stages["draft"].min_bare
