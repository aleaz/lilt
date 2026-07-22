"""Empty TM after init prints sync guidance (R-01-F2 / SM-20)."""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from lilt.cli.main import app

pytestmark = pytest.mark.release

runner = CliRunner(env={"COLUMNS": "200"})


def test_tm_status_empty_namespace_guidance(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    lilt = tmp_path / ".lilt"
    lilt.mkdir(parents=True)
    (lilt / "lilt.yaml").write_text(
        "project:\n  source_lang: en\n  target_lang: es\n"
        "llm:\n  base_url: http://127.0.0.1:9\n  model: mock\n",
        encoding="utf-8",
    )
    (lilt / "tm").mkdir(exist_ok=True)
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(app, ["tm", "status"])
    assert result.exit_code == 0
    out = result.output.lower()
    assert "no tm namespaces" in out or "pipeline sync" in out
