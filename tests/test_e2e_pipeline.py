"""End-to-end pipeline tests: sync -> translate -> build without network."""

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from lilt.cli.main import app
from lilt.llm.base_provider import BaseLLMProvider
from lilt.llm.provider import LLMResponse
from lilt.llm.token_budget import BudgetPlan

runner = CliRunner()


class DeterministicMockLLM(BaseLLMProvider):
    """Provider that translates deterministically for integration tests."""

    def __init__(self) -> None:
        self.draft_model = "mock-draft"
        self.critique_model = "mock-critique"
        self.refine_model = "mock-refine"
        self.model = "mock-base"
        self.model_context_limit = 8192
        self.max_tokens = 1024

    @property
    def reflection_enabled(self) -> bool:
        return True

    def plan_budget(
        self,
        *,
        stage: str,
        source_text: str,
        draft_text: str = "",
        critique_text: str = "",
    ) -> BudgetPlan:
        return BudgetPlan(
            context_limit=self.model_context_limit,
            reserved_output=self.max_tokens,
            fixed_prompt_tokens=max(1, len(source_text) // 4),
            neighbor_budget=6000,
            safety_margin=64,
            chat_template_overhead=0,
            fudge=1.0,
            ok=True,
            infeasible=False,
        )

    def generate_draft(self, text: str, context=None) -> LLMResponse:
        translated = text.replace("Hello", "Hola")
        return LLMResponse(text=translated, duration_ms=1)

    def generate_critique(
        self, draft_text: str, source_text: str, context=None
    ) -> LLMResponse:
        return LLMResponse(
            text='{"requires_refine": false, "issues": []}',
            duration_ms=1,
        )

    def generate_refine(
        self, draft_text: str, critique_text: str, source_text: str, context=None
    ) -> LLMResponse:
        return LLMResponse(text=draft_text, duration_ms=1)

    def get_prompt_version(self, stage: str) -> str:
        return f"{stage}:mock0000"


@pytest.fixture
def mock_llm_factory():
    with patch(
        "lilt.services.pipeline_service.ProviderFactory.create",
        return_value=DeterministicMockLLM(),
    ):
        yield


def test_e2e_sync_translate_build(mock_llm_factory):
    with tempfile.TemporaryDirectory() as tmpdir:
        original_cwd = os.getcwd()
        try:
            os.chdir(tmpdir)
            runner.invoke(app, ["project", "init"])

            tex_path = os.path.join(tmpdir, "test.tex")
            with open(tex_path, "w", encoding="utf-8") as f:
                f.write("\\section{Introduction}\nHello World\n")

            sync_result = runner.invoke(app, ["pipeline", "sync", tex_path])
            assert sync_result.exit_code == 0
            assert "Namespace" in sync_result.output

            translate_result = runner.invoke(app, ["pipeline", "translate", "test"])
            assert translate_result.exit_code == 0
            assert "Translation completed successfully!" in translate_result.output

            out_path = os.path.join(tmpdir, "out.tex")
            build_result = runner.invoke(
                app, ["pipeline", "build", "test", tex_path, out_path]
            )
            assert build_result.exit_code == 0
            assert "Successfully built document at:" in build_result.output

            with open(out_path, encoding="utf-8") as f:
                content = f.read()
            assert "Hola World" in content

        finally:
            os.chdir(original_cwd)


def test_e2e_sync_splits_dense_noindent_paragraphs():
    with tempfile.TemporaryDirectory() as tmpdir:
        original_cwd = os.getcwd()
        try:
            os.chdir(tmpdir)
            runner.invoke(app, ["project", "init"])

            tex_path = os.path.join(tmpdir, "dense.tex")
            with open(tex_path, "w", encoding="utf-8") as f:
                f.write(
                    "\\begin{document}\n"
                    "\\noindent\\emph{First paragraph.}\n"
                    "\\noindent\\emph{Second paragraph.}\n"
                    "\\end{document}\n"
                )

            sync_result = runner.invoke(app, ["pipeline", "sync", tex_path])
            assert sync_result.exit_code == 0

            tm_path = Path(".lilt/tm/dense.jsonl")
            assert tm_path.exists()
            segment_count = len(tm_path.read_text().strip().splitlines())
            assert segment_count == 2

        finally:
            os.chdir(original_cwd)


def test_e2e_build_blocks_on_conflict_segment(mock_llm_factory):
    with tempfile.TemporaryDirectory() as tmpdir:
        original_cwd = os.getcwd()
        try:
            os.chdir(tmpdir)
            runner.invoke(app, ["project", "init"])

            tex_path = os.path.join(tmpdir, "test.tex")
            with open(tex_path, "w", encoding="utf-8") as f:
                f.write("\\section{Introduction}\nHello World\n")

            assert runner.invoke(app, ["pipeline", "sync", tex_path]).exit_code == 0
            assert runner.invoke(app, ["pipeline", "translate", "test"]).exit_code == 0

            tm_path = Path(".lilt/tm/test.jsonl")
            records = [json.loads(line) for line in tm_path.read_text().splitlines()]
            records[0]["status"] = "conflict"
            tm_path.write_text(
                "\n".join(json.dumps(record) for record in records) + "\n"
            )

            out_path = os.path.join(tmpdir, "out.tex")
            build_result = runner.invoke(
                app, ["pipeline", "build", "test", tex_path, out_path]
            )
            assert build_result.exit_code != 0
            assert "Build blocked" in build_result.output

        finally:
            os.chdir(original_cwd)
