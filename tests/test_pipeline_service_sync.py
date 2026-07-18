"""Tests for pipeline sync file-type policy."""

import os
import tempfile

import yaml

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
