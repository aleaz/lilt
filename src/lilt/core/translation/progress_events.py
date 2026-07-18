"""Progress event builders for translation strategy iterators."""

from typing import Literal


def progress_pass(
    segment_id: str,
    elapsed: float,
    *,
    stage: str | None = None,
) -> dict:
    """Build a success progress event."""
    status = f"PASS ({stage.upper()})" if stage else "PASS"
    return {
        "type": "progress",
        "segment_id": segment_id,
        "status": status,
        "elapsed": elapsed,
    }


def progress_validation_fail(
    segment_id: str,
    elapsed: float,
    error: str,
) -> dict:
    """Build a validation failure progress event."""
    return {
        "type": "progress",
        "segment_id": segment_id,
        "status": "FAIL (Validation)",
        "elapsed": elapsed,
        "error": error,
    }


def progress_error(
    segment_id: str,
    elapsed: float,
    error: str,
    *,
    kind: Literal["llm", "pipeline"] = "pipeline",
) -> dict:
    """Build an infrastructure or pipeline failure progress event."""
    status = "FAIL (LLM Error)" if kind == "llm" else "FAIL (Error)"
    return {
        "type": "progress",
        "segment_id": segment_id,
        "status": status,
        "elapsed": elapsed,
        "error": error,
    }
