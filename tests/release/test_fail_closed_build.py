"""Fail-closed build honesty (F-11 / RG-M2 fixture lock)."""

from __future__ import annotations

from pathlib import Path

import pytest

from lilt.cli.main import app
from lilt.models.segment import SegmentStatus
from lilt.tm.repository import TMRepository
from tests.release.conftest import runner

pytestmark = pytest.mark.release


def test_fail_closed_build_blocks_unfinished_then_allow_partial(
    workspace: Path,
) -> None:
    tex = workspace / "main.tex"
    tex.write_text("\\section{Intro}\nHello world paragraph.\n", encoding="utf-8")

    sync = runner.invoke(app, ["pipeline", "sync", str(tex)])
    assert sync.exit_code == 0, sync.output

    repo = TMRepository(base_dir=str(workspace / ".lilt" / "tm"))
    segments = repo.load_namespace("main")
    assert segments, "sync should create segments"
    # Leave all generated → fail-closed; then allow-partial.
    out = workspace / "out.tex"
    blocked = runner.invoke(app, ["pipeline", "build", "main", str(tex), str(out)])
    assert blocked.exit_code == 1
    assert "Build blocked" in blocked.output
    assert "--allow-partial" in blocked.output

    # Mark one buildable and one conflict to mirror recovery path.
    items = list(segments.values())
    items[0].status = SegmentStatus.CONFLICT
    if len(items) > 1:
        items[1].status = SegmentStatus.REFINED
        items[1].translation = "Hola."
    repo.save_namespace("main", items)

    blocked2 = runner.invoke(app, ["pipeline", "build", "main", str(tex), str(out)])
    assert blocked2.exit_code == 1
    assert "conflict" in blocked2.output.lower() or "Build blocked" in blocked2.output

    partial = runner.invoke(
        app,
        ["pipeline", "build", "main", str(tex), str(out), "--allow-partial"],
    )
    assert partial.exit_code == 0, partial.output
    assert out.is_file()
