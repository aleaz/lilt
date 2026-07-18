import sqlite3
import uuid
from datetime import UTC, datetime

import pytest

from lilt.telemetry.models import InferenceRecord, TokenUsage
from lilt.telemetry.service import TelemetryService


@pytest.fixture
def telemetry_service(tmp_path):
    db_path = tmp_path / "telemetry.db"
    return TelemetryService(db_path=db_path)


def test_record_inference(telemetry_service):
    record = InferenceRecord(
        id=str(uuid.uuid4()),
        segment_id="seg-123",
        namespace="ns",
        provider="openai",
        model="gpt-4o",
        stage="draft",
        prompt_version="draft_v1",
        started_at=datetime.now(UTC),
        finished_at=datetime.now(UTC),
        duration_ms=1000,
        ttft_ms=200,
        usage=TokenUsage(
            prompt_tokens=100,
            completion_tokens=50,
            cached_tokens=0,
            source="provider_reported",
        ),
        finish_reason="stop",
    )

    telemetry_service.record_inference(record)

    with sqlite3.connect(telemetry_service.db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT segment_id, provider, stage FROM inference_records WHERE id = ?",
            (record.id,),
        )
        row = cursor.fetchone()
        assert row is not None
        assert row == ("seg-123", "openai", "draft")
