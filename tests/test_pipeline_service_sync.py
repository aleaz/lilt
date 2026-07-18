"""Tests for pipeline sync file-type policy."""

import os
import tempfile
from unittest.mock import patch

import pytest
import yaml

from lilt.exceptions import ConfigurationError
from lilt.models.sync_result import SyncResult
from lilt.services.pipeline_service import PipelineService


def _setup_workspace(tmpdir: str) -> PipelineService:
    config_dir = os.path.join(tmpdir, ".lilt")
    os.makedirs(config_dir, exist_ok=True)
    with open(os.path.join(config_dir, "lilt.yaml"), "w", encoding="utf-8") as f:
        yaml.dump(
            {
                "project": {"source_lang": "en", "target_lang": "es"},
                "llm": {"provider": "openai", "model": "gpt-4o"},
            },
            f,
        )
    return PipelineService(tmpdir)


def test_sync_file_skips_sty_dependencies():
    with tempfile.TemporaryDirectory() as tmpdir:
        with open(os.path.join(tmpdir, "main.tex"), "w", encoding="utf-8") as f:
            f.write(
                r"""\documentclass{article}
\usepackage{mypkg}
\begin{document}
Hello from the paper body.
\end{document}
"""
            )
        with open(os.path.join(tmpdir, "mypkg.sty"), "w", encoding="utf-8") as f:
            f.write(r"\newcommand{\pkglabel}{Package boilerplate}")

        service = _setup_workspace(tmpdir)
        results = service.sync_file("main.tex")

        synced_namespaces = {result.namespace for result in results}
        assert synced_namespaces == {"main"}

        tm_dir = os.path.join(tmpdir, ".lilt", "tm")
        tm_files = {name for name in os.listdir(tm_dir) if name.endswith(".jsonl")}
        assert "mypkg.jsonl" not in tm_files
        assert "main.jsonl" in tm_files


def test_sync_partial_failure_reports_completed_namespaces():
    with tempfile.TemporaryDirectory() as tmpdir:
        main_tex = os.path.join(tmpdir, "main.tex")
        chap_tex = os.path.join(tmpdir, "chap.tex")
        with open(main_tex, "w", encoding="utf-8") as f:
            f.write("\\begin{document}\nBody.\n\\end{document}\n")
        with open(chap_tex, "w", encoding="utf-8") as f:
            f.write("Chapter body.\n")

        service = _setup_workspace(tmpdir)
        calls = {"n": 0}

        def _fake_sync(file_path, repo, namespace, parser, similarity_threshold=0.85):
            calls["n"] += 1
            if calls["n"] >= 2:
                raise ValueError("simulated parse failure")
            return SyncResult(namespace=namespace, new_segments=1)

        with (
            patch(
                "lilt.services.pipeline_service.DependencyResolver.resolve_from",
                return_value=[main_tex, chap_tex],
            ),
            patch(
                "lilt.services.pipeline_service.core_sync_file", side_effect=_fake_sync
            ),
            pytest.raises(ConfigurationError, match="Partial sync") as excinfo,
        ):
            service.sync_file("main.tex")
        assert "already updated namespaces" in str(excinfo.value)
        assert "main" in str(excinfo.value)
