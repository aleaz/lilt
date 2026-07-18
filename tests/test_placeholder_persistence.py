import os
import tempfile

from pylatexenc.macrospec import MacroSpec

from lilt.core.build import Builder
from lilt.core.sync import sync_parsed_blocks
from lilt.core.translation import WorkflowReflectionStrategy
from lilt.llm.base_provider import BaseLLMProvider
from lilt.llm.provider import LLMResponse
from lilt.models.segment import SegmentStatus, StageArtifact, StoredSegment
from lilt.parser.ast_parser import LatexParser
from lilt.tm.repository import TMRepository


class MockLLM(BaseLLMProvider):
    def __init__(self, reflection_enabled=True):
        self._reflection_enabled = reflection_enabled
        self.draft_model = "mock-draft"
        self.critique_model = "mock-critique"
        self.refine_model = "mock-refine"
        self.model = "mock-base"

    @property
    def reflection_enabled(self) -> bool:
        return self._reflection_enabled

    def generate_draft(self, text, context=None) -> LLMResponse:
        # Mock translation replacing placeholders exactly
        res_text = text.replace("Hello", "Hola")
        return LLMResponse(text=res_text, duration_ms=10)

    def generate_critique(self, draft_text, source_text, context=None) -> LLMResponse:
        # Mock critique indicating no refinement needed (requires_refine: false)
        return LLMResponse(
            text='{"requires_refine": false, "issues": []}', duration_ms=10
        )

    def generate_refine(
        self, draft_text, critique_text, source_text, context=None
    ) -> LLMResponse:
        return LLMResponse(text=draft_text, duration_ms=10)

    def translate_segment_iter(self, text, context=None):
        yield {"type": "status", "message": "Drafting"}
        yield {
            "type": "result",
            "text": "Hola",
            "meta": {"used": False, "draft_accepted": True},
        }

    def get_prompt_version(self, stage: str) -> str:
        return f"{stage}:mock0000"


def setup_parser_with_lineref(parser: LatexParser):
    parser.custom_macros.add("lineref")
    parser.db.add_context_category(
        "lilt_custom", macros=[MacroSpec("lineref", args_parser="{")]
    )


def test_segment_block_hash_and_id():
    parser = LatexParser()
    setup_parser_with_lineref(parser)
    blocks = parser.parse_text("Hello \\lineref{world} and welcome.")

    # Filter translatable blocks
    translatable = [b for b in blocks if b.is_translatable()]
    assert len(translatable) > 0
    block = translatable[0]

    # source_hash must be full SHA-256 (64 hex characters)
    assert len(block.source_hash) == 64
    # id must be truncated to 12 characters
    assert len(block.id) == 12
    assert block.id == block.source_hash[:12]


def test_placeholder_persistence_on_sync():
    with tempfile.TemporaryDirectory() as tmpdir:
        tm_repo = TMRepository(tmpdir)
        parser = LatexParser()
        setup_parser_with_lineref(parser)
        content = "Hello \\lineref{world} and \\lineref{universe}."

        # Parse and sync
        blocks = parser.parse_text(content)
        namespace = "test_sync"
        active = sync_parsed_blocks(namespace, blocks, tm_repo).active_segments

        assert len(active) > 0
        seg = active[0]

        # Verify placeholders were saved
        assert len(seg.placeholders) > 0
        # Mappings are generated back-to-front
        assert '<macro id="1"/>' in seg.placeholders
        assert '<macro id="2"/>' in seg.placeholders
        assert seg.placeholders['<macro id="1"/>'] == "\\lineref{universe}"
        assert seg.placeholders['<macro id="2"/>'] == "\\lineref{world}"
        assert len(seg.source_hash) == 64


def test_reconstruction_resilient_to_index_shifts():
    with tempfile.TemporaryDirectory() as tmpdir:
        tm_repo = TMRepository(tmpdir)
        parser = LatexParser()
        setup_parser_with_lineref(parser)

        # 1. Original file translation
        original_content = "Hello \\lineref{world}."
        blocks = parser.parse_text(original_content)
        namespace = "resilient_test"

        active = sync_parsed_blocks(namespace, blocks, tm_repo).active_segments
        seg = active[0]

        # Set manual translation and reviewed status
        seg.translation = 'Hola <macro id="1"/>.'
        seg.status = SegmentStatus.REVIEWED
        tm_repo.save_namespace(namespace, [seg])

        # 2. Mutate file content (add a paragraph BEFORE the segment)
        mutated_content = "This is a new paragraph.\n\nHello \\lineref{world}."

        # Write files
        in_path = os.path.join(tmpdir, "input.tex")
        out_path = os.path.join(tmpdir, "output.tex")
        with open(in_path, "w", encoding="utf-8") as f:
            f.write(mutated_content)

        builder = Builder(tm_repo, parser)
        builder.build_file(in_path, out_path, namespace, allow_partial=True)

        with open(out_path, encoding="utf-8") as f:
            result = f.read()

        # The result must correctly unmask the macro \lineref{world}
        assert "This is a new paragraph." in result
        assert "Hola \\lineref{world}." in result


def test_workflow_reflection_meta_populates():
    with tempfile.TemporaryDirectory() as tmpdir:
        tm_repo = TMRepository(tmpdir)
        llm = MockLLM(reflection_enabled=True)
        strategy = WorkflowReflectionStrategy(tm_repo, llm, context_window=0)

        # Sync segment
        parser = LatexParser()
        setup_parser_with_lineref(parser)
        blocks = parser.parse_text("Hello \\lineref{world}.")
        namespace = "reflection_test"
        sync_parsed_blocks(namespace, blocks, tm_repo)

        # Run draft stage
        list(strategy.run_iter(namespace, stage="draft"))
        segments = tm_repo.load_namespace(namespace)
        seg = list(segments.values())[0]
        assert seg.status == SegmentStatus.DRAFTED
        assert seg.reflection_meta is not None
        assert seg.reflection_meta.used is True
        assert seg.reflection_meta.draft_accepted is False

        # Run critique stage
        list(strategy.run_iter(namespace, stage="critique"))
        segments = tm_repo.load_namespace(namespace)
        seg = list(segments.values())[0]
        assert seg.status == SegmentStatus.CRITIQUED
        assert seg.reflection_meta is not None
        assert seg.reflection_meta.critique_feedback is not None
        # Mock critique returned requires_refine=False, so draft should be accepted!
        assert seg.reflection_meta.draft_accepted is True

        # Run refine stage (short-circuits because draft_accepted was True)
        list(strategy.run_iter(namespace, stage="refine"))
        segments = tm_repo.load_namespace(namespace)
        seg = list(segments.values())[0]
        assert seg.status == SegmentStatus.REFINED
        assert seg.reflection_meta is not None
        assert seg.reflection_meta.draft_accepted is True


def test_workflow_skips_reflection_if_disabled():
    with tempfile.TemporaryDirectory() as tmpdir:
        tm_repo = TMRepository(tmpdir)
        llm = MockLLM(reflection_enabled=False)
        strategy = WorkflowReflectionStrategy(tm_repo, llm, context_window=0)

        # Sync segment
        parser = LatexParser()
        setup_parser_with_lineref(parser)
        blocks = parser.parse_text("Hello \\lineref{world}.")
        namespace = "disabled_reflection_test"
        sync_parsed_blocks(namespace, blocks, tm_repo)

        # Run draft stage with reflection disabled
        list(strategy.run_iter(namespace, stage="draft"))
        segments = tm_repo.load_namespace(namespace)
        seg = list(segments.values())[0]

        # Should skip critique and refine, marking directly as REFINED (LLM pipeline complete)
        assert seg.status == SegmentStatus.REFINED
        assert seg.translation == 'Hola <macro id="1"/>.'
        assert seg.reflection_meta is not None
        assert seg.reflection_meta.used is False
        assert seg.reflection_meta.draft_accepted is True

        # Critique and refine runs shouldn't affect it
        events = list(strategy.run_iter(namespace, stage="critique"))
        # Verify it yielded 0 total segments to process for critique
        assert any(e.get("type") == "start" and e.get("total") == 0 for e in events)


def test_workflow_draft_archives_approved_translation_on_force():
    with tempfile.TemporaryDirectory() as tmpdir:
        tm_repo = TMRepository(tmpdir)
        llm = MockLLM(reflection_enabled=True)
        strategy = WorkflowReflectionStrategy(tm_repo, llm, context_window=0)

        namespace = "force_draft_archive"
        human_translation = "Traduccion humana aprobada"
        tm_repo.save_namespace(
            namespace,
            [
                StoredSegment(
                    id="approved-seg-id",
                    source_hash="approved-seg-id",
                    source_text="Hello world.",
                    status=SegmentStatus.APPROVED,
                    translation=human_translation,
                )
            ],
        )

        list(strategy.run_iter(namespace, stage="draft", force=True))

        segments = tm_repo.load_namespace(namespace)
        seg = segments["approved-seg-id"]
        assert seg.status == SegmentStatus.DRAFTED
        assert seg.translation == ""
        assert len(seg.history) == 1
        assert seg.history[0].translation == human_translation
        assert seg.history[0].status == SegmentStatus.APPROVED


def test_workflow_force_critique_skips_approved_with_stale_draft():
    with tempfile.TemporaryDirectory() as tmpdir:
        tm_repo = TMRepository(tmpdir)
        llm = MockLLM(reflection_enabled=True)
        strategy = WorkflowReflectionStrategy(tm_repo, llm, context_window=0)

        namespace = "force_critique_skip"
        tm_repo.save_namespace(
            namespace,
            [
                StoredSegment(
                    id="approved-seg-id",
                    source_hash="approved-seg-id",
                    source_text="Hello world.",
                    status=SegmentStatus.APPROVED,
                    translation="Hola mundo.",
                    draft=StageArtifact(content="stale draft", model="mock"),
                )
            ],
        )

        events = list(strategy.run_iter(namespace, stage="critique", force=True))
        assert any(e.get("type") == "start" and e.get("total") == 0 for e in events)
