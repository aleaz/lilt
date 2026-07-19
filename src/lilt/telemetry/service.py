"""SQLite-backed telemetry store for LLM workflow observability."""

import logging
import sqlite3
import uuid
from contextlib import closing
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from lilt.exceptions import TelemetryCorruptionError
from lilt.llm.provider import LLMProvider, LLMResponse
from lilt.telemetry.models import InferenceRecord, TokenUsage

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class TelemetryResult:
    """Outcome of a telemetry persistence attempt."""

    success: bool
    error: str | None = None


class TelemetryService:
    """Handles persistence of telemetry and observability data to a local SQLite database."""

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._init_db()

    def _init_db(self) -> None:
        """Initializes the SQLite database with the necessary tables and views."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        with closing(sqlite3.connect(self.db_path)) as conn, conn:
            cursor = conn.cursor()
            cursor.execute("PRAGMA journal_mode=WAL;")

            # Table for individual LLM requests
            cursor.execute(
                """
                    CREATE TABLE IF NOT EXISTS inference_records (
                        id TEXT PRIMARY KEY,
                        segment_id TEXT,
                        namespace TEXT,
                        provider TEXT,
                        model TEXT,
                        stage TEXT,
                        prompt_version TEXT,
                        started_at TIMESTAMP,
                        finished_at TIMESTAMP,
                        duration_ms INTEGER,
                        ttft_ms INTEGER,
                        prompt_tokens INTEGER,
                        completion_tokens INTEGER,
                        cached_tokens INTEGER,
                        usage_source TEXT,
                        finish_reason TEXT,
                        is_heuristic_simple BOOLEAN,
                        attempt INTEGER DEFAULT 1,
                        retry_reason TEXT,
                        pack_context_ms INTEGER,
                        checkpoint_ms INTEGER,
                        effective_max_tokens INTEGER,
                        reasoning_tokens INTEGER DEFAULT 0
                    )
                """
            )
            self._ensure_columns(
                cursor,
                "inference_records",
                {
                    "attempt": "INTEGER DEFAULT 1",
                    "retry_reason": "TEXT",
                    "pack_context_ms": "INTEGER",
                    "checkpoint_ms": "INTEGER",
                    "effective_max_tokens": "INTEGER",
                    "reasoning_tokens": "INTEGER DEFAULT 0",
                },
            )

            # View for logical stage metrics
            cursor.execute(
                """
                    CREATE VIEW IF NOT EXISTS stage_metrics AS
                    SELECT 
                        segment_id,
                        stage,
                        COUNT(id) as attempts,
                        SUM(duration_ms) as total_duration_ms,
                        SUM(prompt_tokens) as total_prompt_tokens,
                        SUM(completion_tokens) as total_completion_tokens
                    FROM inference_records
                    GROUP BY segment_id, stage
                    """
            )

            # View for end-to-end workflow metrics
            cursor.execute(
                """
                    CREATE VIEW IF NOT EXISTS workflow_metrics AS
                    SELECT 
                        segment_id,
                        namespace,
                        MIN(started_at) as started_at,
                        MAX(finished_at) as finished_at,
                        MAX(CASE WHEN stage = 'critique' THEN 1 ELSE 0 END) as critique_executed,
                        MAX(CASE WHEN stage = 'refine' THEN 1 ELSE 0 END) as refine_executed,
                        SUM(duration_ms) as total_duration_ms,
                        SUM(prompt_tokens + completion_tokens) as total_tokens_consumed
                FROM inference_records
                GROUP BY segment_id, namespace
                """
            )

    @staticmethod
    def _ensure_columns(
        cursor: sqlite3.Cursor, table: str, columns: dict[str, str]
    ) -> None:
        """Add missing columns on existing databases (SQLite migration)."""
        existing = {
            row[1] for row in cursor.execute(f"PRAGMA table_info({table})").fetchall()
        }
        for name, decl in columns.items():
            if name not in existing:
                cursor.execute(f"ALTER TABLE {table} ADD COLUMN {name} {decl}")

    def record_inference(self, record: InferenceRecord) -> TelemetryResult:
        """Saves a single inference record to the database."""
        try:
            with closing(sqlite3.connect(self.db_path)) as conn, conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO inference_records (
                        id, segment_id, namespace, provider, model, stage, prompt_version,
                        started_at, finished_at, duration_ms, ttft_ms,
                        prompt_tokens, completion_tokens, cached_tokens, usage_source, finish_reason,
                        is_heuristic_simple, attempt, retry_reason,
                        pack_context_ms, checkpoint_ms, effective_max_tokens, reasoning_tokens
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        record.id or str(uuid.uuid4()),
                        record.segment_id,
                        record.namespace,
                        record.provider,
                        record.model,
                        record.stage,
                        record.prompt_version,
                        record.started_at.isoformat(),
                        record.finished_at.isoformat(),
                        record.duration_ms,
                        record.ttft_ms,
                        record.usage.prompt_tokens,
                        record.usage.completion_tokens,
                        record.usage.cached_tokens,
                        record.usage.source,
                        record.finish_reason,
                        record.is_heuristic_simple,
                        record.attempt,
                        record.retry_reason,
                        record.pack_context_ms,
                        record.checkpoint_ms,
                        record.effective_max_tokens,
                        record.usage.reasoning_tokens,
                    ),
                )
            return TelemetryResult(success=True)
        except Exception as e:
            logger.error(f"Failed to record inference telemetry: {e}")
            return TelemetryResult(success=False, error=str(e))

    def record_inference_from_llm(
        self,
        llm: LLMProvider,
        namespace: str,
        segment_id: str,
        stage: Literal["draft", "critique", "refine", "sequential"],
        res: LLMResponse,
        model_name: str,
        finish_reason: str = "stop",
    ) -> TelemetryResult:
        """Build and persist a single inference record from an LLM response.

        Prompt-version resolution failures soft-fail like SQLite write errors so
        observability never mutates translation outcomes.
        """
        try:
            is_heuristic = getattr(res, "bypass", False)
            record = InferenceRecord(
                id=str(uuid.uuid4()),
                segment_id=segment_id,
                namespace=namespace,
                provider=llm.__class__.__name__,
                model=model_name,
                stage=stage,
                prompt_version=llm.get_prompt_version(stage),
                started_at=res.started_at,
                finished_at=res.finished_at,
                duration_ms=res.duration_ms,
                ttft_ms=res.ttft_ms,
                usage=TokenUsage(
                    prompt_tokens=res.prompt_tokens,
                    completion_tokens=res.completion_tokens,
                    cached_tokens=res.cached_tokens,
                    reasoning_tokens=getattr(res, "reasoning_tokens", 0) or 0,
                ),
                usage_source="api",
                finish_reason=finish_reason,
                is_heuristic_simple=is_heuristic,
                attempt=getattr(res, "attempt", 1) or 1,
                retry_reason=getattr(res, "retry_reason", None),
                pack_context_ms=getattr(res, "pack_context_ms", None),
                checkpoint_ms=getattr(res, "checkpoint_ms", None),
                effective_max_tokens=getattr(res, "effective_max_tokens", None),
            )
        except Exception as e:
            logger.error(f"Failed to build inference telemetry record: {e}")
            return TelemetryResult(success=False, error=str(e))
        return self.record_inference(record)

    def get_global_summary(self, namespace: str | None = None) -> dict | None:
        """Retrieves global telemetry summary (total requests, tokens, time)."""
        if not self.db_path.exists():
            return None

        try:
            with closing(sqlite3.connect(self.db_path)) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                query = """
                    SELECT 
                        COUNT(id) as total_requests,
                        SUM(prompt_tokens) as total_prompt_tokens,
                        SUM(completion_tokens) as total_completion_tokens,
                        SUM(duration_ms) as total_duration_ms
                    FROM inference_records
                """
                if namespace:
                    query += " WHERE namespace = ?"
                    cursor.execute(query, (namespace,))
                else:
                    cursor.execute(query)
                row = cursor.fetchone()
                if row and row["total_requests"] > 0:
                    return dict(row)
                return None
        except sqlite3.Error as e:
            logger.error(f"Failed to read global summary: {e}")
            raise TelemetryCorruptionError(
                f"Telemetry database is unreadable: {e}"
            ) from e

    def get_stage_breakdown(self, namespace: str | None = None) -> list[dict]:
        """Retrieves telemetry breakdown by LLM pipeline stage."""
        if not self.db_path.exists():
            return []

        try:
            with closing(sqlite3.connect(self.db_path)) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                query = """
                    SELECT 
                        stage,
                        COUNT(id) as reqs,
                        SUM(prompt_tokens) as pt,
                        SUM(completion_tokens) as ct,
                        AVG(duration_ms) as avg_ms
                    FROM inference_records
                """
                if namespace:
                    query += " WHERE namespace = ? GROUP BY stage"
                    cursor.execute(query, (namespace,))
                else:
                    query += " GROUP BY stage"
                    cursor.execute(query)

                return [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            logger.error(f"Failed to read stage breakdown: {e}")
            raise TelemetryCorruptionError(
                f"Telemetry database is unreadable: {e}"
            ) from e

    def get_workflow_summary(self, namespace: str | None = None) -> list[dict]:
        """Retrieves per-segment workflow metrics from the workflow_metrics view."""
        if not self.db_path.exists():
            return []

        try:
            with closing(sqlite3.connect(self.db_path)) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                query = """
                    SELECT
                        segment_id,
                        namespace,
                        started_at,
                        finished_at,
                        critique_executed,
                        refine_executed,
                        total_duration_ms,
                        total_tokens_consumed
                    FROM workflow_metrics
                """
                if namespace:
                    query += " WHERE namespace = ? ORDER BY started_at"
                    cursor.execute(query, (namespace,))
                else:
                    query += " ORDER BY started_at"
                    cursor.execute(query)

                return [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            logger.error(f"Failed to read workflow summary: {e}")
            raise TelemetryCorruptionError(
                f"Telemetry database is unreadable: {e}"
            ) from e
