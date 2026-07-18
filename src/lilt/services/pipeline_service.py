"""High-level service for sync, translation, build, and PDF compilation."""

import os
import shutil
import subprocess
import typing
from collections.abc import Callable, Iterable

from lilt.core.build import Builder, BuildResult
from lilt.core.review_policy import ReviewPolicy
from lilt.core.sync import sync_file as core_sync_file
from lilt.core.translation import TranslatorPipeline
from lilt.exceptions import (
    BuildError,
    TranslationValidationError,
)
from lilt.llm.factory import ProviderFactory
from lilt.models.config import LiltConfig
from lilt.models.segment import SegmentStatus, StoredSegment
from lilt.models.segment_policy import SegmentPolicy
from lilt.models.segment_transition import SegmentTransitionPolicy
from lilt.models.status_resolver import StatusResolver
from lilt.models.sync_result import SyncResult
from lilt.models.translation_mode import TranslationMode
from lilt.models.translation_stage import TranslationStage
from lilt.parser.ast_parser import LatexParser
from lilt.parser.dependency_resolver import DependencyResolver
from lilt.services.workspace_context import WorkspaceContext
from lilt.tm.segment_lookup import resolve_unique_segment
from lilt.utils.namespace import derive_namespace
from lilt.validation.validators import (
    SegmentTranslationValidator,
    ValidationError,
)


class SyncOrchestrator:
    """Orchestrates LaTeX dependency sync into the Translation Memory."""

    def __init__(self, ctx: WorkspaceContext):
        self.ctx = ctx

    def sync_file(self, input_file: str) -> list[SyncResult]:
        """Parse ``input_file`` and its ``.tex`` dependencies into TM namespaces."""
        abs_input = self.ctx._resolve_and_verify_path(  # type: ignore
            input_file
        )
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
        pipeline = self._build_translator_pipeline(config, translation_mode)

        total = 0
        current = 0
        yielded_done = False
        resolved_status = None
        if status_filter:
            resolved_status = StatusResolver.resolve(status_filter).value

        with self.ctx.repo.namespace_session(namespace):
            for event in pipeline.run_translation_iter(
                namespace, force, segment_id, resolved_status, stage
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
            msg = self._idle_translation_message(namespace, total, force)
            yield current, total, "done", msg, False

    def _idle_translation_message(self, namespace: str, total: int, force: bool) -> str:
        if total > 0:
            return "Done"
        segments = self.ctx.repo.load_namespace(namespace)
        active = [s for s in segments.values() if s.status != SegmentStatus.DEPRECATED]
        if not active:
            return "Done (no translatable segments; run sync on a .tex file first, or this fixture is parser-roundtrip only)"
        eligible = [
            s
            for s in active
            if SegmentPolicy.is_eligible_for_workflow_stage(s, "draft", force)
        ]
        if not eligible:
            return "Done (already translated)"
        return "Done"

    def _build_translator_pipeline(
        self,
        config: LiltConfig,
        translation_mode: TranslationMode | None = None,
    ) -> TranslatorPipeline:
        llm_config = config.to_llm_factory_dict(workspace_dir=self.ctx.workspace_dir)
        llm = ProviderFactory.create(llm_config)
        context_window = config.llm.context_window
        mode = translation_mode or TranslationMode.from_llm_config(llm_config)
        return TranslatorPipeline(
            self.ctx.repo,
            llm,
            context_window,
            translation_mode=mode,
            telemetry=self.ctx.telemetry,
            draft_empty_retries=config.llm.draft_empty_retries,
        )


class BuildOrchestrator:
    """Reconstructs translated ``.tex`` output and optional PDF compilation."""

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

        abs_input = self.ctx._resolve_and_verify_path(  # type: ignore
            input_file
        )
        abs_output = self.ctx._resolve_and_verify_path(  # type: ignore
            output_file
        )

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

    def compile_pdf(self, main_file: str, output_dir: str) -> None:
        """Compile ``main_file`` with pdflatex/bib tools (service-only helper)."""
        abs_output_dir = self.ctx._resolve_and_verify_path(  # type: ignore
            output_dir
        )
        abs_main = self.ctx._resolve_and_verify_path(  # type: ignore
            main_file
        )
        env = self._build_latex_env()
        base_name = os.path.splitext(os.path.basename(abs_main))[0]

        def run_pdflatex() -> str:
            return self._run_pdflatex(abs_output_dir, abs_main, env)

        output = run_pdflatex()
        if self._detect_and_run_bibliography(abs_output_dir, base_name, env):
            output = run_pdflatex()
        self._rerun_until_stable(output, run_pdflatex)

    def _build_latex_env(self) -> dict[str, str]:
        env = os.environ.copy()
        sep = os.pathsep
        workspace = os.path.abspath(self.ctx.workspace_dir)
        for tex_bin in ("/Library/TeX/texbin",):
            if os.path.isdir(tex_bin):
                path = env.get("PATH", "")
                if tex_bin not in path.split(sep):
                    env["PATH"] = f"{tex_bin}{sep}{path}"
        for var in ("TEXINPUTS", "BIBINPUTS", "BSTINPUTS"):
            existing = env.get(var, "")
            env[var] = f".{sep}{workspace}{sep}{existing}{sep}"
        return env

    def _resolve_tex_tool(self, name: str, env: dict[str, str]) -> str:
        path = env.get("PATH", os.environ.get("PATH", ""))
        found = shutil.which(name, path=path)
        return found if found else name

    def _run_pdflatex(
        self, abs_output_dir: str, abs_main: str, env: dict[str, str]
    ) -> str:
        pdflatex = self._resolve_tex_tool("pdflatex", env)
        try:
            res = subprocess.run(
                [pdflatex, "-interaction=nonstopmode", os.path.basename(abs_main)],
                cwd=abs_output_dir,
                env=env,
                check=True,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            return res.stdout
        except subprocess.CalledProcessError as e:
            raise BuildError(f"pdflatex failed:\n{e.output}") from e
        except FileNotFoundError as exc:
            raise BuildError(
                "pdflatex not found. Please install TeX Live or MiKTeX."
            ) from exc

    def _run_bib_tool(
        self, tool: str, base_name: str, abs_output_dir: str, env: dict[str, str]
    ) -> None:
        resolved = self._resolve_tex_tool(tool, env)
        try:
            subprocess.run(
                [resolved, base_name],
                cwd=abs_output_dir,
                env=env,
                check=True,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
        except subprocess.CalledProcessError as e:
            raise BuildError(f"{tool} failed:\n{e.output}") from e
        except FileNotFoundError as exc:
            raise BuildError(f"{tool} not found.") from exc

    def _detect_and_run_bibliography(
        self, abs_output_dir: str, base_name: str, env: dict[str, str]
    ) -> bool:
        aux_file = os.path.join(abs_output_dir, f"{base_name}.aux")
        bcf_file = os.path.join(abs_output_dir, f"{base_name}.bcf")
        if os.path.exists(bcf_file):
            self._run_bib_tool("biber", base_name, abs_output_dir, env)
            return True
        if os.path.exists(aux_file):
            with open(aux_file, encoding="utf-8", errors="ignore") as f:
                content = f.read()
                if "\\bibdata" in content or "\\bibstyle" in content:
                    self._run_bib_tool("bibtex", base_name, abs_output_dir, env)
                    return True
        return False

    def _rerun_until_stable(
        self, output: str, run_pdflatex: Callable[[], str], max_reruns: int = 2
    ) -> str:
        reruns = 0
        stability_markers = (
            "Rerun to get cross-references right",
            "Rerun to get citations correct",
            "Rerun to get pages right",
            "Rerun to get index right",
        )
        while reruns < max_reruns and any(
            marker in output for marker in stability_markers
        ):
            output = run_pdflatex()
            reruns += 1
        return output


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
        """Persist a human translation and status transition."""
        with self.ctx.repo.namespace_session(namespace):
            segments = self.ctx.repo.load_namespace(namespace)
            seg = resolve_unique_segment(segments, segment_id, namespace)
            SegmentTransitionPolicy.validate_human_authoring(seg.status, new_status)
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
        try:
            normalized = SegmentTranslationValidator.normalize_translation(
                seg.source_text, new_translation
            )
        except ValidationError as exc:
            raise TranslationValidationError(str(exc)) from exc
        self.update_segment_translation(namespace, seg.id, normalized, new_status)


# The WorkspaceContext lacks _resolve_and_verify_path, let's inject it via PipelineService wrapper.
# Wait, let's just implement PipelineService as the Facade.


class PipelineService:
    """Facade over sync, translate, build, and review orchestrators."""

    def __init__(
        self, workspace_dir: str, workspace_ctx: WorkspaceContext | None = None
    ):
        self.ctx = workspace_ctx or WorkspaceContext.from_workspace(workspace_dir)
        self.workspace_dir = self.ctx.workspace_dir
        self.lilt_dir = self.ctx.lilt_dir
        self.config_path = self.ctx.config_path
        self.tm_dir = self.ctx.tm_dir
        self.repo = self.ctx.repo

        # We hack the method onto ctx for the orchestrators
        self.ctx._resolve_and_verify_path = self._resolve_and_verify_path  # type: ignore

        self._sync = SyncOrchestrator(self.ctx)
        self._trans = TranslationOrchestrator(self.ctx)
        self._build = BuildOrchestrator(self.ctx)
        self._review = ReviewManager(self.ctx)

    def _resolve_and_verify_path(self, input_path: str) -> str:
        abs_path = os.path.abspath(
            input_path
            if os.path.isabs(input_path)
            else os.path.join(self.workspace_dir, input_path)
        )
        real_path = os.path.realpath(abs_path)
        real_workspace = os.path.realpath(self.workspace_dir)
        if not real_path.startswith(real_workspace):
            raise ValueError(
                f"Security Error: Path '{input_path}' attempts to traverse outside the workspace sandbox."
            )
        return abs_path

    # Facade methods
    def sync_file(self, *args: typing.Any, **kwargs: typing.Any) -> list[SyncResult]:
        """Delegate to SyncOrchestrator."""
        return self._sync.sync_file(*args, **kwargs)

    def run_translation(
        self, *args: typing.Any, **kwargs: typing.Any
    ) -> typing.Iterable[tuple[int, int, str, str, bool]]:
        """Delegate to TranslationOrchestrator."""
        return self._trans.run_translation(*args, **kwargs)

    def run_build(self, *args: typing.Any, **kwargs: typing.Any) -> BuildResult:
        """Delegate to BuildOrchestrator."""
        return self._build.run_build(*args, **kwargs)

    def compile_pdf(self, *args: typing.Any, **kwargs: typing.Any) -> None:
        """Delegate PDF compilation to BuildOrchestrator."""
        return self._build.compile_pdf(*args, **kwargs)

    def get_segments_to_review(
        self, *args: typing.Any, **kwargs: typing.Any
    ) -> list[StoredSegment]:
        """Delegate to ReviewManager."""
        return self._review.get_segments_to_review(*args, **kwargs)

    def get_segment(self, *args: typing.Any, **kwargs: typing.Any) -> StoredSegment:
        """Delegate to ReviewManager."""
        return self._review.get_segment(*args, **kwargs)

    def update_segment_translation(
        self, *args: typing.Any, **kwargs: typing.Any
    ) -> None:
        """Delegate to ReviewManager."""
        return self._review.update_segment_translation(*args, **kwargs)

    def submit_human_translation(self, *args: typing.Any, **kwargs: typing.Any) -> None:
        """Delegate to ReviewManager."""
        return self._review.submit_human_translation(*args, **kwargs)

    def _get_config(self) -> LiltConfig:
        return self.ctx.preconditions.load_config()

    def _build_translator_pipeline(
        self,
        config: LiltConfig,
        translation_mode: TranslationMode | None = None,
    ) -> TranslatorPipeline:
        return self._trans._build_translator_pipeline(config, translation_mode)
