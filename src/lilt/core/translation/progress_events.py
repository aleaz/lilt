"""Progress event builders for translation strategy iterators."""

from typing import Any, Literal, NotRequired, TypedDict


class StartEvent(TypedDict):
    """Batch start event."""

    type: Literal["start"]
    total: int
    stage: NotRequired[str]


class SubStatusEvent(TypedDict):
    """Per-segment sub-status while a stage is in progress."""

    type: Literal["sub_status"]
    segment_id: str
    status_msg: str


class ProgressEvent(TypedDict):
    """Per-segment progress outcome (pass / validation fail / error)."""

    type: Literal["progress"]
    segment_id: str
    status: str
    elapsed: float
    error: NotRequired[str]


class DoneEvent(TypedDict):
    """Batch completion event."""

    type: Literal["done"]


def progress_pass(
    segment_id: str,
    elapsed: float,
    *,
    stage: str | None = None,
) -> dict[str, Any]:
    """Build a success progress event."""
    status = f"PASS ({stage.upper()})" if stage else "PASS"
    event: ProgressEvent = {
        "type": "progress",
        "segment_id": segment_id,
        "status": status,
        "elapsed": elapsed,
    }
    return dict(event)


def progress_validation_fail(
    segment_id: str,
    elapsed: float,
    error: str,
) -> dict[str, Any]:
    """Build a validation failure progress event."""
    event: ProgressEvent = {
        "type": "progress",
        "segment_id": segment_id,
        "status": "FAIL (Validation)",
        "elapsed": elapsed,
        "error": error,
    }
    return dict(event)


def progress_error(
    segment_id: str,
    elapsed: float,
    error: str,
    *,
    kind: Literal["llm", "pipeline"] = "pipeline",
) -> dict[str, Any]:
    """Build an infrastructure or pipeline failure progress event."""
    status = "FAIL (LLM Error)" if kind == "llm" else "FAIL (Error)"
    event: ProgressEvent = {
        "type": "progress",
        "segment_id": segment_id,
        "status": status,
        "elapsed": elapsed,
        "error": error,
    }
    return dict(event)
