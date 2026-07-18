from lilt.core.translation.progress_events import (
    progress_error,
    progress_pass,
    progress_validation_fail,
)


def test_progress_pass_without_stage():
    event = progress_pass("seg-1", 1.5)
    assert event == {
        "type": "progress",
        "segment_id": "seg-1",
        "status": "PASS",
        "elapsed": 1.5,
    }


def test_progress_pass_with_stage():
    event = progress_pass("seg-1", 0.5, stage="draft")
    assert event["status"] == "PASS (DRAFT)"


def test_progress_validation_fail():
    event = progress_validation_fail("seg-1", 0.2, "bad placeholders")
    assert event["status"] == "FAIL (Validation)"
    assert event["error"] == "bad placeholders"


def test_progress_error_kinds():
    llm_event = progress_error("seg-1", 0.2, "timeout", kind="llm")
    pipeline_event = progress_error("seg-1", 0.2, "boom", kind="pipeline")
    assert llm_event["status"] == "FAIL (LLM Error)"
    assert pipeline_event["status"] == "FAIL (Error)"
