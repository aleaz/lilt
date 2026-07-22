#!/usr/bin/env python3
"""Fail if tm status Count diverges from tm list cardinality (RG-01 / QG-STAT).

Usage:
  uv run python scripts/release/check-status-consistency.py --workspace PATH
  # or run against a temporary fixture (default)
"""

from __future__ import annotations

import argparse
import os
import re
import sys
import tempfile
from pathlib import Path

import yaml
from typer.testing import CliRunner

from lilt.cli.main import app
from lilt.models.segment import SegmentStatus, StoredSegment
from lilt.tm.repository import TMRepository

runner = CliRunner(env={"COLUMNS": "200"})


def _write_fixture(root: Path) -> None:
    lilt = root / ".lilt"
    lilt.mkdir(parents=True)
    (lilt / "lilt.yaml").write_text(
        yaml.dump({"project": {"source_lang": "en", "target_lang": "es"}}),
        encoding="utf-8",
    )
    tm = lilt / "tm"
    tm.mkdir()
    repo = TMRepository(base_dir=str(tm))
    segs = [
        StoredSegment(
            id=f"r{i:010d}xx",
            source_hash=f"r{i:010d}xx",
            source_text=f"Refined source {i} with tokens.",
            translation=f"Traduccion {i}.",
            status=SegmentStatus.REFINED,
        )
        for i in range(3)
    ]
    segs.append(
        StoredSegment(
            id="c0000000001",
            source_hash="c0000000001",
            source_text="Conflict source.",
            translation="",
            status=SegmentStatus.CONFLICT,
        )
    )
    repo.save_namespace("main", segs)


def _parse_count(output: str, status: str) -> int:
    match = re.search(rf"(?m)^[^\n]*?{re.escape(status)}\s+(\d+)\s+", output)
    if not match:
        raise SystemExit(f"status row '{status}' missing:\n{output}")
    return int(match.group(1))


def _list_count(output: str) -> int:
    match = re.search(r"Total matching segments:\s*(\d+)", output)
    if not match:
        raise SystemExit(f"list footer missing:\n{output}")
    return int(match.group(1))


def check_workspace(workspace: Path) -> None:
    """Assert tm status Count matches tm list for refined."""
    original = os.getcwd()
    os.chdir(workspace)
    try:
        status = runner.invoke(app, ["tm", "status", "main"])
        if status.exit_code != 0:
            raise SystemExit(f"tm status failed:\n{status.output}")
        listed = runner.invoke(app, ["tm", "list", "main", "--status", "refined"])
        if listed.exit_code != 0:
            raise SystemExit(f"tm list failed:\n{listed.output}")
        status_n = _parse_count(status.output, "refined")
        list_n = _list_count(listed.output)
        if status_n != list_n:
            raise SystemExit(
                f"RG-01 FAIL: status refined Count={status_n} != list={list_n}"
            )
        if status_n == 0 and "refined" in status.output:
            # Extra guard: tokens present with zero count is the classic bug shape
            row = re.search(r"(?m)^[^\n]*?refined\s+0\s+.*([1-9][\d,]*)", status.output)
            if row:
                raise SystemExit(
                    "RG-01 FAIL: refined Count=0 but Tokens column is non-zero"
                )
        print(f"OK: refined status Count={status_n} matches list={list_n}")
    finally:
        os.chdir(original)


def main() -> None:
    """CLI entry: fixture workspace or --workspace path."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--workspace",
        type=Path,
        help="Existing LILT workspace (must contain namespace main)",
    )
    args = parser.parse_args()
    if args.workspace:
        check_workspace(args.workspace.resolve())
        return
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _write_fixture(root)
        check_workspace(root)


if __name__ == "__main__":
    main()
    sys.exit(0)
