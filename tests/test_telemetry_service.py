from datetime import UTC, datetime
from pathlib import Path
from typing import Literal
from unittest.mock import MagicMock

import pytest

from lilt.exceptions import TelemetryCorruptionError
from lilt.llm.provider import LLMResponse
from lilt.telemetry.models import InferenceRecord, TokenUsage
from lilt.telemetry.service import TelemetryService

Stage = Literal["draft", "critique", "refine", "sequential"]


def _record(
    segment_id: str,
    namespace: str,
    stage: Stage,
    *,
    prompt_tokens: int = 10,
    completion_tokens: int = 5,
    duration_ms: int = 100,
) -> InferenceRecord:
    started = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)
    finished = datetime(2026, 1, 1, 12, 0, 1, tzinfo=UTC)
    return InferenceRecord(
        id=f"{segment_id}-{stage}",
        segment_id=segment_id,
        namespace=namespace,
        provider="MockProvider",
        model="mock",
        stage=stage,
        prompt_version="draft:abc",
        started_at=started,
        finished_at=finished,
        duration_ms=duration_ms,
        ttft_ms=10,
        usage=TokenUsage(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            cached_tokens=0,
        ),
        usage_source="api",
        finish_reason="stop",
        is_heuristic_simple=False,
    )


def test_get_workflow_summary(tmp_path: Path):
    db_path = tmp_path / "telemetry.db"
    service = TelemetryService(db_path)

    service.record_inference(_record("seg1", "intro", "draft"))
    service.record_inference(
        _record("seg1", "intro", "critique", prompt_tokens=20, completion_tokens=8)
    )
    service.record_inference(
        _record("seg1", "intro", "refine", prompt_tokens=15, completion_tokens=12)
    )

    rows = service.get_workflow_summary("intro")
    assert len(rows) == 1
    row = rows[0]
    assert row["segment_id"] == "seg1"
    assert row["namespace"] == "intro"
    assert row["critique_executed"] == 1
    assert row["refine_executed"] == 1
    assert row["total_tokens_consumed"] == 70
    assert row["total_duration_ms"] == 300

    assert service.get_workflow_summary("missing") == []


def test_get_global_summary_and_stage_breakdown(tmp_path: Path):
    db_path = tmp_path / "telemetry.db"
    service = TelemetryService(db_path)

    service.record_inference(_record("seg1", "intro", "draft"))
    service.record_inference(_record("seg2", "intro", "critique"))

    summary = service.get_global_summary("intro")
    assert summary is not None
    assert summary["total_requests"] == 2
    assert summary["total_prompt_tokens"] == 20
    assert summary["total_completion_tokens"] == 10

    breakdown = service.get_stage_breakdown("intro")
    stages = {row["stage"] for row in breakdown}
    assert stages == {"draft", "critique"}

    assert service.get_global_summary() is not None
    assert len(service.get_stage_breakdown()) == 2


def test_get_global_summary_missing_db(tmp_path: Path):
    service = TelemetryService(tmp_path / "missing.db")
    assert service.get_global_summary() is None
    assert service.get_stage_breakdown() == []
    assert service.get_workflow_summary() == []


def test_corrupt_db_raises_on_summary_and_stage(tmp_path: Path):
    db_path = tmp_path / "telemetry.db"
    service = TelemetryService(db_path)
    service.record_inference(_record("seg1", "intro", "draft"))
    db_path.write_bytes(b"not a sqlite database")
    for suffix in ("-wal", "-shm"):
        side = Path(str(db_path) + suffix)
        if side.exists():
            side.unlink()

    with pytest.raises(TelemetryCorruptionError, match="unreadable"):
        service.get_global_summary()
    with pytest.raises(TelemetryCorruptionError, match="unreadable"):
        service.get_stage_breakdown()
    with pytest.raises(TelemetryCorruptionError, match="unreadable"):
        service.get_workflow_summary()


def test_record_inference_from_llm_bypass(tmp_path: Path):
    db_path = tmp_path / "telemetry.db"
    service = TelemetryService(db_path)
    llm = MagicMock()
    llm.__class__.__name__ = "MockProvider"
    llm.get_prompt_version.return_value = "draft:abc"

    res = LLMResponse(text="hola", bypass=True, duration_ms=50)
    service.record_inference_from_llm(llm, "intro", "seg1", "draft", res, "mock-model")

    rows = service.get_workflow_summary("intro")
    assert len(rows) == 1
    summary = service.get_global_summary("intro")
    assert summary is not None
    assert summary["total_requests"] == 1


def test_record_inference_idempotent_db_init(tmp_path: Path):
    db_path = tmp_path / "nested" / "telemetry.db"
    TelemetryService(db_path)
    TelemetryService(db_path)
    assert db_path.exists()
