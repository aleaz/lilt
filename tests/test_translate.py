from unittest.mock import MagicMock, patch

import pytest

from lilt.core.translation import create_reflection_strategy
from lilt.llm.base_provider import BaseLLMProvider
from lilt.llm.output_gate import EmptyLLMOutputError
from lilt.llm.provider import LLMResponse
from lilt.llm.reflection_pass import REFINE_MAX_VALIDATION_RETRIES
from lilt.models.segment import SegmentStatus, StageArtifact, StoredSegment
from lilt.models.translation_mode import TranslationMode
from lilt.validation.validators import ValidationError

_VALIDATOR = (
    "lilt.validation.validators.SegmentTranslationValidator.normalize_translation"
)


def _identity_normalize(_source: str, translated: str) -> str:
    return translated


@pytest.fixture
def mock_tm(tmp_path):
    tm = MagicMock()
    tm.base_dir = tmp_path
    return tm


@pytest.fixture
def mock_llm():
    llm = MagicMock()
    llm.model = "test-model"
    llm.draft_model = "test-model"
    llm.critique_model = "test-model"
    llm.refine_model = "test-model"
    llm.generate_draft.return_value = LLMResponse(text="Hola draft")
    llm.generate_critique.return_value = LLMResponse(
        text='{"requires_refine": false, "issues": []}'
    )
    llm.generate_refine.return_value = LLMResponse(text="Hola refined")
    llm.get_prompt_version.return_value = "draft:test0000"
    llm.stage_model_name.return_value = "test-model"
    return llm


def test_reflection_strategy_empty_namespace(mock_tm, mock_llm):
    mock_tm.load_namespace.return_value = {}
    strategy = create_reflection_strategy(
        TranslationMode.WORKFLOW,
        mock_tm,
        mock_llm,
        3,
        MagicMock(),
    )

    events = list(strategy.run_iter("test_ns"))
    assert len(events) == 0


def test_reflection_strategy_workflow_success(mock_tm, mock_llm):
    seg1 = StoredSegment(
        id="1",
        source_hash="a",
        source_text="Hello",
        status=SegmentStatus.GENERATED,
        translation="",
    )
    mock_tm.load_namespace.return_value = {"1": seg1}

    strategy = create_reflection_strategy(
        TranslationMode.WORKFLOW,
        mock_tm,
        mock_llm,
        3,
        MagicMock(),
    )

    with (
        patch(_VALIDATOR, side_effect=_identity_normalize),
    ):
        list(strategy.run_iter("test_ns"))

        # 4 events per stage (start, sub_status, progress, done) * 3 stages = 12 events
        # Wait, if a stage is skipped (e.g. 0 to_process), it yields `start` and returns without `done`.
        # Let's just check the segment's final state.

        assert seg1.status == SegmentStatus.REFINED
        assert (
            seg1.translation == "Hola draft"
        )  # Short-circuited due to 'required_changes: none'
        assert seg1.draft is not None
        assert seg1.draft.content == "Hola draft"
        assert seg1.critique is not None
        assert seg1.critique.content == '{"requires_refine": false, "issues": []}'
        assert seg1.refined is not None
        assert seg1.refined.content == "Hola draft"

        mock_llm.generate_draft.assert_called_once_with(
            "Hello", {"backward": [], "forward": []}
        )
        mock_llm.generate_critique.assert_called_once_with(
            "Hola draft", "Hello", {"backward": [], "forward": []}
        )
        # generate_refine is NOT called because of short-circuit
        mock_llm.generate_refine.assert_not_called()
        mock_tm.save_namespace.assert_called()


def test_workflow_empty_critique_bypasses_refine(mock_tm, mock_llm):
    seg1 = StoredSegment(
        id="title-seg",
        source_hash="a",
        source_text="\\title{Attention Is All You Need}",
        status=SegmentStatus.GENERATED,
        translation="",
    )
    mock_tm.load_namespace.return_value = {"title-seg": seg1}
    mock_llm.generate_critique.return_value = LLMResponse(text="")

    strategy = create_reflection_strategy(
        TranslationMode.WORKFLOW,
        mock_tm,
        mock_llm,
        3,
        MagicMock(),
    )

    with (
        patch(_VALIDATOR, side_effect=_identity_normalize),
    ):
        list(strategy.run_iter("test_ns"))

    assert seg1.status == SegmentStatus.REFINED
    assert seg1.translation == "Hola draft"
    assert seg1.critique is not None
    assert seg1.critique.content == '{"requires_refine": false, "issues": []}'
    mock_llm.generate_refine.assert_not_called()


def test_workflow_empty_draft_sets_actionable_hint(mock_tm, mock_llm):
    seg1 = StoredSegment(
        id="author-seg",
        source_hash="a",
        source_text="\\author{Complex Author Block}",
        status=SegmentStatus.GENERATED,
        translation="",
    )
    mock_tm.load_namespace.return_value = {"author-seg": seg1}

    strategy = create_reflection_strategy(
        TranslationMode.WORKFLOW,
        mock_tm,
        mock_llm,
        3,
        MagicMock(),
    )

    with patch(
        "lilt.core.translation.workflow_strategy.run_draft",
        side_effect=EmptyLLMOutputError("draft"),
    ) as mock_draft:
        events = list(strategy.run_iter("test_ns"))

    # Fast-fail: an empty draft is not retried by default (draft_empty_retries=1),
    # so a single generation is attempted instead of amplifying latency.
    assert mock_draft.call_count == 1
    assert seg1.status == SegmentStatus.ERROR
    assert seg1.error_meta is not None
    assert "Hint:" in seg1.error_meta.message
    assert "EmptyLLMOutputError" in seg1.error_meta.error_type
    failure = next(e for e in events if e.get("status") == "FAIL (LLM Error)")
    assert failure is not None


def test_workflow_resume_skips_refined_segment(mock_tm, mock_llm):
    """VAL-TM-002: partial progress resumes without re-translating refined segments."""
    refined = StoredSegment(
        id="done-1",
        source_hash="a",
        source_text="Already done",
        status=SegmentStatus.REFINED,
        translation="Ya traducido",
    )
    pending = StoredSegment(
        id="pending-1",
        source_hash="b",
        source_text="Still pending",
        status=SegmentStatus.GENERATED,
        translation="",
    )
    mock_tm.load_namespace.return_value = {
        "done-1": refined,
        "pending-1": pending,
    }

    strategy = create_reflection_strategy(
        TranslationMode.WORKFLOW,
        mock_tm,
        mock_llm,
        3,
        MagicMock(),
    )

    with patch(_VALIDATOR, side_effect=_identity_normalize):
        list(strategy.run_iter("test_ns", force=False))

    mock_llm.generate_draft.assert_called_once()
    assert refined.translation == "Ya traducido"
    assert pending.status == SegmentStatus.REFINED


def test_reflection_strategy_workflow_refine(mock_tm, mock_llm):
    seg1 = StoredSegment(
        id="1",
        source_hash="a",
        source_text="Hello",
        status=SegmentStatus.GENERATED,
        translation="",
    )
    mock_tm.load_namespace.return_value = {"1": seg1}

    # Force critique to require changes
    mock_llm.generate_critique.return_value = LLMResponse(
        text='{"requires_refine": true, "issues": [{"category": "other", "description": "Use refined text"}]}'
    )

    strategy = create_reflection_strategy(
        TranslationMode.WORKFLOW,
        mock_tm,
        mock_llm,
        3,
        MagicMock(),
    )

    with (
        patch(_VALIDATOR, side_effect=_identity_normalize),
    ):
        list(strategy.run_iter("test_ns"))

        assert seg1.status == SegmentStatus.REFINED
        assert seg1.translation == "Hola refined"
        assert seg1.refined is not None
        assert seg1.refined.content == "Hola refined"

        mock_llm.generate_refine.assert_called_once_with(
            "Hola draft",
            '{"requires_refine": true, "issues": [{"category": "other", "description": "Use refined text"}]}',
            "Hello",
            {"backward": [], "forward": []},
        )


def test_reflection_strategy_validation_failure(mock_tm, mock_llm):
    seg1 = StoredSegment(
        id="1",
        source_hash="a",
        source_text="Hello",
        status=SegmentStatus.GENERATED,
        translation="",
    )
    mock_tm.load_namespace.return_value = {"1": seg1}

    mock_llm.generate_critique.return_value = LLMResponse(
        text='{"requires_refine": true, "issues": [{"category": "other", "description": "fix it"}]}'
    )

    strategy = create_reflection_strategy(
        TranslationMode.WORKFLOW,
        mock_tm,
        mock_llm,
        3,
        MagicMock(),
    )

    def fail_all_translations(_source: str, _translated: str) -> str:
        raise ValidationError("Missing placeholder")

    with patch(_VALIDATOR, side_effect=fail_all_translations):
        events = list(strategy.run_iter("test_ns"))

        # The validation happens in the REFINE stage.
        # Find the failure event
        failure_event = next(
            e for e in events if e.get("status") == "FAIL (Validation)"
        )
        assert failure_event is not None
        assert seg1.status == SegmentStatus.CONFLICT
        assert seg1.translation == "Hola refined"


def test_reflection_strategy_with_context(mock_tm, mock_llm):
    seg1 = StoredSegment(
        id="1",
        source_hash="a",
        source_text="Context sentence.",
        status=SegmentStatus.REVIEWED,
        translation="Oración de contexto.",
        draft=StageArtifact(content="Oración de draft.", model="m"),
        refined=StageArtifact(content="Oración de contexto.", model="m"),
    )
    seg2 = StoredSegment(
        id="2",
        source_hash="b",
        source_text="Target sentence.",
        status=SegmentStatus.GENERATED,
        translation="",
    )
    mock_tm.load_namespace.return_value = {"1": seg1, "2": seg2}

    strategy = create_reflection_strategy(
        TranslationMode.WORKFLOW,
        mock_tm,
        mock_llm,
        1,
        MagicMock(),
    )

    with (
        patch(_VALIDATOR, side_effect=_identity_normalize),
        patch.object(
            mock_llm,
            "generate_critique",
            return_value=LLMResponse(
                text='{"requires_refine": true, "issues": [{"category": "other", "description": "fix it"}]}'
            ),
        ),
    ):
        list(strategy.run_iter("test_ns"))

        # In draft phase, it uses the previous refined for context
        mock_llm.generate_draft.assert_called_once_with(
            "Target sentence.", {"backward": ["Oración de contexto."], "forward": []}
        )
        # In refine phase, it uses the previous refined text
        mock_llm.generate_refine.assert_called_once_with(
            "Hola draft",
            '{"requires_refine": true, "issues": [{"category": "other", "description": "fix it"}]}',
            "Target sentence.",
            {"backward": ["Oración de contexto."], "forward": []},
        )


def test_workflow_force_skips_locked_segment(mock_tm, mock_llm):
    locked = StoredSegment(
        id="locked-1",
        source_hash="a",
        source_text="Locked text",
        status=SegmentStatus.LOCKED,
        translation="Texto bloqueado",
    )
    mock_tm.load_namespace.return_value = {"locked-1": locked}

    strategy = create_reflection_strategy(
        TranslationMode.WORKFLOW,
        mock_tm,
        mock_llm,
        3,
        MagicMock(),
    )

    with (
        patch(_VALIDATOR, side_effect=_identity_normalize),
    ):
        events = list(strategy.run_iter("test_ns", force=True))

    mock_llm.generate_draft.assert_not_called()
    assert locked.status == SegmentStatus.LOCKED
    assert locked.translation == "Texto bloqueado"
    progress_events = [e for e in events if e.get("type") == "progress"]
    assert progress_events == []


def test_workflow_force_skips_deprecated_segment(mock_tm, mock_llm):
    deprecated = StoredSegment(
        id="dep-1",
        source_hash="a",
        source_text="Old text",
        status=SegmentStatus.DEPRECATED,
        translation="Vieja traduccion",
    )
    mock_tm.load_namespace.return_value = {"dep-1": deprecated}

    strategy = create_reflection_strategy(
        TranslationMode.WORKFLOW,
        mock_tm,
        mock_llm,
        3,
        MagicMock(),
    )

    list(strategy.run_iter("test_ns", force=True))

    mock_llm.generate_draft.assert_not_called()
    assert deprecated.status == SegmentStatus.DEPRECATED


def test_workflow_force_reprocesses_approved_segment(mock_tm, mock_llm):
    approved = StoredSegment(
        id="approved-1",
        source_hash="a",
        source_text="Approved text",
        status=SegmentStatus.APPROVED,
        translation="Texto aprobado",
    )
    mock_tm.load_namespace.return_value = {"approved-1": approved}

    strategy = create_reflection_strategy(
        TranslationMode.WORKFLOW,
        mock_tm,
        mock_llm,
        3,
        MagicMock(),
    )

    with (
        patch(_VALIDATOR, side_effect=_identity_normalize),
    ):
        list(strategy.run_iter("test_ns", force=True))

    mock_llm.generate_draft.assert_called_once()
    assert approved.status == SegmentStatus.REFINED


def test_reflection_strategy_dynamic_context(mock_tm, mock_llm):
    seg1 = StoredSegment(
        id="1",
        source_hash="a",
        source_text="Context sentence.",
        status=SegmentStatus.REVIEWED,
        translation="Oración de contexto.",
        draft=StageArtifact(content="Oración de draft.", model="m"),
        refined=StageArtifact(content="Oración de contexto.", model="m"),
    )
    seg2 = StoredSegment(
        id="2",
        source_hash="b",
        source_text="Target sentence.",
        status=SegmentStatus.GENERATED,
        translation="",
    )
    mock_tm.load_namespace.return_value = {"1": seg1, "2": seg2}

    # Use dict to configure dynamic context windows
    strategy = create_reflection_strategy(
        TranslationMode.WORKFLOW,
        mock_tm,
        mock_llm,
        {"draft": 1, "critique": 0, "refine": 1},
        MagicMock(),
    )

    with (
        patch(_VALIDATOR, side_effect=_identity_normalize),
        patch.object(
            mock_llm,
            "generate_critique",
            return_value=LLMResponse(
                text='{"requires_refine": true, "issues": [{"category": "other", "description": "fix it"}]}'
            ),
        ),
    ):
        list(strategy.run_iter("test_ns"))

        # Draft uses the previous refined for context (window = 1)
        mock_llm.generate_draft.assert_called_once_with(
            "Target sentence.", {"backward": ["Oración de contexto."], "forward": []}
        )

        # Critique uses NO context (window = 0)
        mock_llm.generate_critique.assert_called_once_with(
            "Hola draft",
            "Target sentence.",
            {"backward": [], "forward": []},  # Context is intentionally empty
        )

        # Refine uses the previous refined text (window = 1)
        mock_llm.generate_refine.assert_called_once_with(
            "Hola draft",
            '{"requires_refine": true, "issues": [{"category": "other", "description": "fix it"}]}',
            "Target sentence.",
            {"backward": ["Oración de contexto."], "forward": []},
        )


class _RetryFakeLLM(BaseLLMProvider):
    """LLM that fails refine validation once, then succeeds."""

    def __init__(self) -> None:
        self.draft_model = "fake-draft"
        self.critique_model = "fake-critique"
        self.refine_model = "fake-refine"
        self.model = "fake"
        self.refine_attempts = 0

    @property
    def reflection_enabled(self) -> bool:
        return True

    def generate_draft(self, text: str, context=None) -> LLMResponse:
        return LLMResponse(text="Hola draft")

    def generate_critique(
        self, draft_text: str, source_text: str, context=None
    ) -> LLMResponse:
        return LLMResponse(
            text='{"requires_refine": true, "issues": [{"category": "other", "description": "fix"}]}'
        )

    def generate_refine(
        self, draft_text: str, critique_text: str, source_text: str, context=None
    ) -> LLMResponse:
        self.refine_attempts += 1
        if self.refine_attempts == 1:
            return LLMResponse(text="bad translation")
        return LLMResponse(text="Hola refined")

    def get_prompt_version(self, stage: str) -> str:
        return f"{stage}:fake0000"


def _normalize_side_effect(source: str, translated: str) -> str:
    if translated == "bad translation":
        raise ValidationError("Missing placeholder")
    return translated


class _SequentialSuccessLLM(_RetryFakeLLM):
    """LLM that accepts draft without refine for sequential pipeline test."""

    def generate_critique(
        self, draft_text: str, source_text: str, context=None
    ) -> LLMResponse:
        return LLMResponse(text='{"requires_refine": false, "issues": []}')


def test_reflection_strategy_sequential_success(mock_tm):
    seg1 = StoredSegment(
        id="1",
        source_hash="a",
        source_text="Hello",
        status=SegmentStatus.GENERATED,
        translation="",
    )
    mock_tm.load_namespace.return_value = {"1": seg1}
    fake_llm = _SequentialSuccessLLM()

    strategy = create_reflection_strategy(
        TranslationMode.SEQUENTIAL,
        mock_tm,
        fake_llm,
        3,
        MagicMock(),
    )

    with patch(_VALIDATOR, side_effect=_identity_normalize):
        events = list(strategy.run_iter("test_ns"))

    assert seg1.status == SegmentStatus.REFINED
    assert seg1.translation == "Hola draft"
    assert any(e.get("type") == "progress" for e in events)


@pytest.mark.parametrize("mode", [TranslationMode.WORKFLOW, TranslationMode.SEQUENTIAL])
def test_refine_validation_retries_are_consistent_across_modes(mock_tm, mode):
    seg1 = StoredSegment(
        id="1",
        source_hash="a",
        source_text="Hello",
        status=SegmentStatus.GENERATED,
        translation="",
    )
    mock_tm.load_namespace.return_value = {"1": seg1}
    fake_llm = _RetryFakeLLM()

    strategy = create_reflection_strategy(
        mode,
        mock_tm,
        fake_llm,
        3,
        MagicMock(),
    )

    validator_target = _VALIDATOR

    with patch(validator_target, side_effect=_normalize_side_effect):
        list(strategy.run_iter("test_ns"))

    assert seg1.status == SegmentStatus.REFINED
    assert seg1.translation == "Hola refined"
    assert fake_llm.refine_attempts == 2
    assert REFINE_MAX_VALIDATION_RETRIES >= 2


def test_workflow_refine_force_skips_generated_without_artifacts(mock_tm, mock_llm):
    seg1 = StoredSegment(
        id="1",
        source_hash="a",
        source_text="Hello",
        status=SegmentStatus.GENERATED,
        translation="",
    )
    mock_tm.load_namespace.return_value = {"1": seg1}

    strategy = create_reflection_strategy(
        TranslationMode.WORKFLOW,
        mock_tm,
        mock_llm,
        3,
        MagicMock(),
    )

    events = list(strategy.run_iter("test_ns", force=True, stage="refine"))

    start_events = [e for e in events if e.get("type") == "start"]
    assert len(start_events) == 1
    assert start_events[0]["total"] == 0
    assert seg1.status == SegmentStatus.GENERATED
    mock_llm.generate_refine.assert_not_called()


def test_workflow_critique_garbage_marks_conflict_without_refine(mock_tm, mock_llm):
    seg1 = StoredSegment(
        id="1",
        source_hash="a",
        source_text="Hello",
        status=SegmentStatus.DRAFTED,
        translation="Hola draft",
        draft=StageArtifact(content="Hola draft", model="m"),
    )
    mock_tm.load_namespace.return_value = {"1": seg1}
    mock_llm.generate_critique.return_value = LLMResponse(text="prose without json")

    strategy = create_reflection_strategy(
        TranslationMode.WORKFLOW,
        mock_tm,
        mock_llm,
        3,
        MagicMock(),
    )

    list(strategy.run_iter("test_ns", stage="critique"))

    assert seg1.status == SegmentStatus.CONFLICT
    mock_llm.generate_refine.assert_not_called()
