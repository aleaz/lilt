from lilt.models.segment import SegmentStatus, StoredSegment
from lilt.telemetry.reflection_cost import (
    ReflectionCostParams,
    _context_window_average,
    estimate_reflection_tokens,
)
from lilt.utils.token_utils import count_tokens


def _segment(text: str) -> StoredSegment:
    return StoredSegment(
        id="a" * 12,
        source_hash="a" * 64,
        source_text=text,
        status=SegmentStatus.GENERATED,
    )


def test_reflection_cost_zero_translatable_segments():
    segments = [_segment("12345")]
    config = {"llm": {"translation_mode": "workflow"}}
    assert estimate_reflection_tokens(segments, config) == 0


def test_reflection_cost_workflow_mode(monkeypatch):
    monkeypatch.setattr("lilt.utils.token_utils.count_tokens", lambda _: 75)
    segments = [_segment("Hello world"), _segment("Second")]
    config = {
        "llm": {
            "translation_mode": "workflow",
            "context_window": {"draft": 3, "critique": 3, "refine": 3},
        }
    }
    params = ReflectionCostParams(s_prompt=600, r_ratio=0.7)
    result = estimate_reflection_tokens(segments, config, params=params)
    n = 2
    tokens_source = sum(count_tokens(seg.source_text) for seg in segments)
    c_avg = 3.0
    multiplier = 2.0 + 0.7
    expected = int(
        n * 600 * multiplier + tokens_source * (1.2 * c_avg * multiplier + 2.4)
    )
    assert result == expected


def test_reflection_cost_sequential_mode(monkeypatch):
    monkeypatch.setattr("lilt.utils.token_utils.count_tokens", lambda _: 40)
    segments = [_segment("Hello")]
    config = {"llm": {"translation_mode": "sequential", "context_window": 2}}
    workflow = estimate_reflection_tokens(
        segments, {**config, "llm": {**config["llm"], "translation_mode": "workflow"}}
    )
    sequential = estimate_reflection_tokens(segments, config)
    assert sequential < workflow


def test_context_window_average_dict():
    assert _context_window_average({"draft": 2, "critique": 4, "refine": 6}) == 4.0
