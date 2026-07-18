from unittest.mock import MagicMock, patch

import pytest

from lilt.core.translation import SequentialReflectionStrategy
from lilt.models.segment import SegmentStatus, StoredSegment


@pytest.fixture
def mock_tm():
    return MagicMock()


@pytest.fixture
def mock_llm():
    llm = MagicMock()
    llm.get_prompt_version.return_value = "sequential:mock0000"
    return llm


def test_sequential_strategy_warns_on_stage_flag(mock_tm, mock_llm, caplog):
    mock_tm.load_namespace.return_value = {}
    strategy = SequentialReflectionStrategy(tm=mock_tm, llm=mock_llm)

    list(strategy.run_iter("test_ns", stage="draft"))

    assert any("--stage flag is ignored" in record.message for record in caplog.records)


def test_sequential_strategy_success(mock_tm, mock_llm):
    seg1 = StoredSegment(
        id="1", source_hash="h1", source_text="Hello", status=SegmentStatus.GENERATED
    )
    mock_tm.load_namespace.return_value = {"1": seg1}

    mock_llm.translate_segment_iter.return_value = [
        {"type": "status", "message": "Thinking..."},
        {
            "type": "result",
            "text": "Hola",
            "meta": {"draft": "Hola", "critiques": [], "refinement": "Hola"},
        },
    ]

    strategy = SequentialReflectionStrategy(tm=mock_tm, llm=mock_llm)

    with patch(
        "lilt.core.translation.sequential_strategy.SegmentTranslationValidator.validate"
    ):
        events = list(strategy.run_iter("test_ns", force=True))

    assert len(events) == 4
    assert events[0]["type"] == "start"
    assert events[1]["type"] == "sub_status"
    assert events[2]["type"] == "progress"
    assert events[2]["status"] == "PASS"
    assert events[3]["type"] == "done"

    assert seg1.status == SegmentStatus.REFINED
    assert seg1.translation == "Hola"


def test_sequential_strategy_bypass_records_heuristic_telemetry(mock_tm, mock_llm):
    seg = StoredSegment(
        id="2",
        source_hash="h2",
        source_text=r"\begin{figure}\end{figure}",
        status=SegmentStatus.GENERATED,
    )
    mock_tm.load_namespace.return_value = {"2": seg}
    mock_llm.translate_segment_iter.return_value = [
        {"type": "status", "message": "Bypassing (No linguistic content)"},
        {
            "type": "result",
            "text": seg.source_text,
            "meta": {"used": True, "draft_accepted": True, "bypass": True},
        },
    ]

    telemetry = MagicMock()
    strategy = SequentialReflectionStrategy(
        tm=mock_tm, llm=mock_llm, telemetry=telemetry
    )

    with patch(
        "lilt.core.translation.sequential_strategy.SegmentTranslationValidator.validate"
    ):
        list(strategy.run_iter("test_ns", force=True))

    telemetry.record_inference_from_llm.assert_called_once()
    res = telemetry.record_inference_from_llm.call_args.args[4]
    assert res.bypass is True
