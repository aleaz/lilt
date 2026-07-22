"""Abort flag stops workflow and sequential between segments (R-01-F3)."""

from __future__ import annotations

from collections.abc import Generator
from unittest.mock import MagicMock

import pytest

from lilt.core.translation.abort import clear_abort, request_abort
from lilt.core.translation.sequential_strategy import SequentialReflectionStrategy
from lilt.core.translation.workflow_strategy import WorkflowReflectionStrategy
from lilt.models.segment import SegmentStatus, StoredSegment
from lilt.tm.repository import TMRepository


@pytest.fixture(autouse=True)
def _clear_abort_flag() -> Generator[None]:
    clear_abort()
    yield
    clear_abort()


def _seed_pending(repo: TMRepository, n: int = 3) -> None:
    segs = [
        StoredSegment(
            id=f"{i:012d}",
            source_hash=f"{i:012d}",
            source_text=f"Source {i}",
            status=SegmentStatus.GENERATED,
        )
        for i in range(n)
    ]
    repo.save_namespace("main", segs)


def test_workflow_stops_when_abort_requested(tmp_path, monkeypatch) -> None:
    repo = TMRepository(str(tmp_path))
    _seed_pending(repo)

    llm = MagicMock()
    llm.reflection_enabled = False
    llm.stage_model_name.return_value = "mock"
    strategy = WorkflowReflectionStrategy(repo, llm, context_window=0)

    calls = {"n": 0}

    def fake_draft(*_a, **_k):
        calls["n"] += 1
        if calls["n"] == 1:
            request_abort()
        return MagicMock(
            content=f"T{calls['n']}",
            model="mock",
            usage={"prompt_tokens": 1, "completion_tokens": 1},
        )

    monkeypatch.setattr(
        "lilt.core.translation.workflow_strategy.run_draft",
        fake_draft,
    )
    monkeypatch.setattr(
        "lilt.core.translation.workflow_strategy.preflight_translation_budget",
        lambda *a, **k: None,
    )

    with pytest.raises(KeyboardInterrupt):
        for _event in strategy.run_iter("main"):
            pass

    assert calls["n"] == 1


def test_sequential_stops_when_abort_requested(tmp_path, monkeypatch) -> None:
    repo = TMRepository(str(tmp_path))
    _seed_pending(repo)

    llm = MagicMock()
    llm.reflection_enabled = False
    llm.stage_model_name.return_value = "mock"
    strategy = SequentialReflectionStrategy(repo, llm, context_window=0)

    calls = {"n": 0}

    def fake_iter(_source: str, context: object = None):
        calls["n"] += 1
        if calls["n"] == 1:
            request_abort()
        yield {"type": "result", "text": f"T{calls['n']}", "meta": {}}

    llm.translate_segment_iter.side_effect = fake_iter
    monkeypatch.setattr(
        "lilt.core.translation.sequential_strategy.preflight_translation_budget",
        lambda *a, **k: None,
    )
    monkeypatch.setattr(
        "lilt.core.translation.sequential_strategy.SegmentTranslationValidator.normalize_translation",
        lambda _src, text: text,
    )

    with pytest.raises(KeyboardInterrupt):
        for _event in strategy.run_iter("main"):
            pass

    assert calls["n"] == 1
