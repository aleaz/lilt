"""High-level service for sync, translation, build, and review."""

import os
from collections.abc import Iterable

from lilt.core.build import Builder, BuildResult
from lilt.core.review_policy import ReviewPolicy
from lilt.core.sync import sync_file as core_sync_file
from lilt.core.translation.strategy_factory import create_reflection_strategy
from lilt.exceptions import (
    BuildError,
    ConfigurationError,
)
from lilt.llm.factory import ProviderFactory
from lilt.models.segment import SegmentStatus, StoredSegment
from lilt.models.segment_policy import SegmentPolicy
from lilt.models.segment_transition import SegmentTransitionPolicy
from lilt.models.status_resolver import StatusResolver
from lilt.models.sync_result import SyncResult
from lilt.models.translation_mode import TranslationMode
from lilt.models.translation_stage import TranslationStage
from lilt.parser.ast_parser import LatexParser
from lilt.parser.dependency_resolver import DependencyResolver
from lilt.services.pdf_compile import PdfCompileService
from lilt.services.workspace_context import WorkspaceContext
from lilt.tm.namespace import derive_namespace, find_namespace_collisions
from lilt.tm.segment_lookup import resolve_unique_segment
from lilt.validation.validators import SegmentTranslationValidator


class SyncOrchestrator:
    """Orchestrates LaTeX dependency sync into the Translation Memory."""

    def __init__(self, ctx: WorkspaceContext):
        self.ctx = ctx

    def sync_file(self, input_file: str) -> list[SyncResult]:
        """Parse ``input_file`` and its ``.tex`` dependencies into TM namespaces."""
        abs_input = self.ctx.resolve_under_workspace(input_file)
        if not os.path.exists(abs_input):
            raise FileNotFoundError(f"File '{input_file}' not found.")
        if os.path.isdir(abs_input):
            raise ValueError(f"'{input_file}' is a directory.")
        if not abs_input.lower().endswith(".tex"):
            raise ValueError(f"'{input_file}' is not a LaTeX file (.tex).")

        resolver = DependencyResolver(self.ctx.workspace_dir)
        dependent_files = resolver.resolve_from(abs_input)

        if not dependent_files:
            dependent_files = [abs_input]
        dependent_files = [p for p in dependent_files if p.lower().endswith(".tex")]
        if not dependent_files:
            dependent_files = [abs_input]

        config = self.ctx.preconditions.load_config()
        parser = LatexParser(parser_config=config.parser)
        similarity_threshold = config.parser.identity.similarity_threshold
        results: list[SyncResult] = []

        for file_path in dependent_files:
            try:
                collisions = find_namespace_collisions(
                    self.ctx.workspace_dir, file_path
                )
                if collisions:
                    other = collisions[0]
                    raise ConfigurationError(
                        f"Namespace collision: '{file_path}' and '{other}' both map to "
                        f"TM namespace '{derive_namespace(self.ctx.workspace_dir, file_path)}'. "
                        "Rename one of the files so directory separators encoded as '__' "
                        "cannot collide with a flat filename."
                    )
                namespace = derive_namespace(self.ctx.workspace_dir, file_path)
                with self.ctx.repo.namespace_session(namespace):
                    result = core_sync_file(
                        file_path,
                        self.ctx.repo,
                        namespace,
                        parser,
                        similarity_threshold=similarity_threshold,
                    )
                results.append(result)
            except Exception as exc:
                if not results:
                    raise
                done = ", ".join(r.namespace for r in results)
                raise ConfigurationError(
                    f"Partial sync: already updated namespaces: [{done}]. "
                    f"Original error: {exc}"
                ) from exc

        return results


class TranslationOrchestrator:
    """Runs the LLM translation pipeline for a TM namespace."""

    def __init__(self, ctx: WorkspaceContext):
        self.ctx = ctx

    def run_translation(
        self,
        namespace: str,
        force: bool = False,
        segment_id: str | None = None,
        status_filter: str | None = None,
        stage: TranslationStage | None = None,
        translation_mode: TranslationMode | None = None,
    ) -> Iterable[tuple[int, int, str, str, bool]]:
        """Translate eligible segments and yield progress tuples."""
        config = self.ctx.preconditions.load_config()
        self.ctx.preconditions.require_namespace(namespace)
        llm_config = config.to_llm_factory_dict(workspace_dir=self.ctx.workspace_dir)
        llm = ProviderFactory.create(llm_config)
        mode = translation_mode or TranslationMode.from_llm_config(llm_config)
        strategy = create_reflection_strategy(
            mode,
            self.ctx.repo,
            llm,
            config.llm.context_window,
            self.ctx.telemetry,
            draft_empty_retries=config.llm.draft_empty_retries,
        )

        total = 0
        current = 0
        yielded_done = False
        resolved_status = None
        if status_filter:
            resolved_status = StatusResolver.resolve(status_filter).value

        stage_value = stage.value if stage is not None else None
        with self.ctx.repo.namespace_session(namespace):
            for event in strategy.run_iter(
                namespace, force, segment_id, resolved_status, stage_value
            ):
                event_type = event.get("type")
                if event_type == "start":
                    total = event.get("total", 0)
                    current = 0
                    stage_name = event.get("stage", "Initializing").capitalize()
                    yield 0, total, "start", f"Starting {stage_name}", False
                elif event_type == "sub_status":
                    seg_id = event.get("segment_id", "")
                    status_msg = event.get("status_msg", "")
                    yield current, total, seg_id, status_msg, False
                elif event_type == "progress":
                    current += 1
                    seg_id = event.get("segment_id", "")
                    status = event.get("status", "")
                    elapsed = event.get("elapsed", 0.0)
                    status_msg = f"{status} ({elapsed:.2f}s)"
                    error_detail = event.get("error")
                    if error_detail:
                        status_msg = f"{status_msg}: {error_detail}"
                    yield current, total, seg_id, status_msg, True
                elif event_type == "done":
                    yielded_done = True
                    yield current, total, "done", "Done", False

        if not yielded_done:
            msg = self._idle_translation_message(namespace, total, force, stage)
            yield current, total, "done", msg, False

    def _idle_translation_message(
        self,
        namespace: str,
        total: int,
        force: bool,
        stage: TranslationStage | None = None,
    ) -> str:
        if total > 0:
            return "Done"
        segments = self.ctx.repo.load_namespace(namespace)
        active = [s for s in segments.values() if s.status != SegmentStatus.DEPRECATED]
        if not active:
            return "Done (no translatable segments; run sync on a .tex file first, or this fixture is parser-roundtrip only)"
        stage_value = stage.value if stage is not None else None
        if stage_value in ("critique", "refine"):
            needed = "drafted" if stage_value == "critique" else "critiqued"
            return (
                f"Done (idle: --stage {stage_value} needs {needed} segments; "
                "use --stage draft [--force] then resume critique|refine)"
            )
        mid_pipeline = [
            s
            for s in active
            if s.status in (SegmentStatus.DRAFTED, SegmentStatus.CRITIQUED)
            and not SegmentPolicy.is_immutable(s)
        ]
        if mid_pipeline:
            # Sequential without --force skips drafted/critiqued; point at
            # workflow stage resume (or --force sequential) instead of
            # "already translated".
            return (
                "Done (idle: segments in drafted/critiqued; "
                "resume with workflow --stage critique|refine, "
                "or re-run sequential with --force)"
            )
        eligible = [
            s
            for s in active
            if SegmentPolicy.is_eligible_for_workflow_stage(s, "draft", force)
        ]
        if not eligible:
            return "Done (already translated)"
        return "Done"


class BuildOrchestrator:
    """Reconstructs translated ``.tex`` output from the Translation Memory."""

    def __init__(self, ctx: WorkspaceContext):
        self.ctx = ctx

    def run_build(
        self,
        namespace: str,
        input_file: str,
        output_file: str,
        *,
        allow_partial: bool = False,
    ) -> BuildResult:
        """Build a translated document from TM into ``output_file``."""
        config = self.ctx.preconditions.load_config()
        self.ctx.preconditions.require_namespace(namespace)

        abs_input = self.ctx.resolve_under_workspace(input_file)
        abs_output = self.ctx.resolve_under_workspace(output_file)

        if not os.path.exists(abs_input):
            raise FileNotFoundError(f"File '{input_file}' not found.")

        parser = LatexParser(parser_config=config.parser)
        injections = config.project.injections
        builder = Builder(self.ctx.repo, parser, injections)

        try:
            return builder.build_file(
                abs_input, abs_output, namespace, allow_partial=allow_partial
            )
        except Exception as e:
            raise BuildError(f"Failed to build document: {e}") from e


class ReviewManager:
    """Human review queue and editor-submit helpers."""

    def __init__(self, ctx: WorkspaceContext):
        self.ctx = ctx

    def get_segments_to_review(self, namespace: str) -> list[StoredSegment]:
        """Return segments eligible for interactive review."""
        config = self.ctx.preconditions.load_config()
        policy = ReviewPolicy.from_config(config.review_dict())
        self.ctx.preconditions.require_namespace(namespace)
        segments = self.ctx.repo.load_namespace(namespace)
        return [s for s in segments.values() if policy.is_reviewable(s)]

    def get_segment(self, namespace: str, segment_id: str) -> StoredSegment:
        """Load a segment by unique ID or unambiguous prefix."""
        segments = self.ctx.repo.load_namespace(namespace)
        return resolve_unique_segment(segments, segment_id, namespace)

    def update_segment_translation(
        self,
        namespace: str,
        segment_id: str,
        new_translation: str,
        new_status: SegmentStatus,
    ) -> None:
        """Persist a human translation and status transition.

        Translation text must pass ``SegmentTranslationValidator`` (placeholder
        multiset / syntax) before write, matching ``submit_human_translation``.
        """
        with self.ctx.repo.namespace_session(namespace):
            segments = self.ctx.repo.load_namespace(namespace)
            seg = resolve_unique_segment(segments, segment_id, namespace)
            SegmentTransitionPolicy.validate_human_authoring(seg.status, new_status)
            new_translation = SegmentTranslationValidator.normalize_translation(
                seg.source_text, new_translation
            )
            if seg.translation and seg.translation != new_translation:
                seg.archive_current_translation()
            seg.translation = new_translation
            seg.status = new_status
            self.ctx.repo.save_namespace(namespace, list(segments.values()))

    def submit_human_translation(
        self,
        namespace: str,
        segment_id: str,
        new_translation: str,
        new_status: SegmentStatus = SegmentStatus.APPROVED,
    ) -> None:
        """Validate and save a human edit, defaulting to approved status."""
        seg = self.get_segment(namespace, segment_id)
        self.update_segment_translation(namespace, seg.id, new_translation, new_status)


class PipelineService:
    """Application composition root for sync, translate, build, and review."""

    def __init__(
        self, workspace_dir: str, workspace_ctx: WorkspaceContext | None = None
    ):
        self.ctx = workspace_ctx or WorkspaceContext.from_workspace(workspace_dir)
        self.workspace_dir = self.ctx.workspace_dir
        self.lilt_dir = self.ctx.lilt_dir
        self.config_path = self.ctx.config_path
        self.tm_dir = self.ctx.tm_dir
        self.repo = self.ctx.repo

        self._sync = SyncOrchestrator(self.ctx)
        self._trans = TranslationOrchestrator(self.ctx)
        self._build = BuildOrchestrator(self.ctx)
        self._pdf = PdfCompileService(self.ctx)
        self._review = ReviewManager(self.ctx)

    def sync_file(self, input_file: str) -> list[SyncResult]:
        """Parse ``input_file`` and dependencies into TM namespaces."""
        return self._sync.sync_file(input_file)

    def run_translation(
        self,
        namespace: str,
        force: bool = False,
        segment_id: str | None = None,
        status_filter: str | None = None,
        stage: TranslationStage | None = None,
        translation_mode: TranslationMode | None = None,
    ) -> Iterable[tuple[int, int, str, str, bool]]:
        """Translate eligible segments and yield progress tuples."""
        return self._trans.run_translation(
            namespace,
            force=force,
            segment_id=segment_id,
            status_filter=status_filter,
            stage=stage,
            translation_mode=translation_mode,
        )

    def run_build(
        self,
        namespace: str,
        input_file: str,
        output_file: str,
        *,
        allow_partial: bool = False,
    ) -> BuildResult:
        """Build a translated document from TM into ``output_file``."""
        return self._build.run_build(
            namespace,
            input_file,
            output_file,
            allow_partial=allow_partial,
        )

    def compile_pdf(self, main_file: str, output_dir: str) -> None:
        """Compile ``main_file`` with pdflatex/bib tools (service-only helper)."""
        return self._pdf.compile_pdf(main_file, output_dir)

    def get_segments_to_review(self, namespace: str) -> list[StoredSegment]:
        """Return segments eligible for interactive review."""
        return self._review.get_segments_to_review(namespace)

    def get_segment(self, namespace: str, segment_id: str) -> StoredSegment:
        """Load a single segment by id or unique prefix."""
        return self._review.get_segment(namespace, segment_id)

    def update_segment_translation(
        self,
        namespace: str,
        segment_id: str,
        new_translation: str,
        new_status: SegmentStatus = SegmentStatus.REVIEWED,
    ) -> None:
        """Persist an edited translation with the given status."""
        return self._review.update_segment_translation(
            namespace, segment_id, new_translation, new_status
        )

    def submit_human_translation(
        self,
        namespace: str,
        segment_id: str,
        new_translation: str,
        new_status: SegmentStatus = SegmentStatus.APPROVED,
    ) -> None:
        """Validate and store a human translation."""
        return self._review.submit_human_translation(
            namespace, segment_id, new_translation, new_status
        )
