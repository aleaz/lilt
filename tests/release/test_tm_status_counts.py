"""RG-01: tm status Count must match segment inventory / tm list."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from lilt.cli.main import app
from lilt.models.segment import SegmentStatus
from lilt.services.tm_service import TMService
from tests.release.conftest import make_seg, runner, save_segments

pytestmark = pytest.mark.release


def _count_from_status_output(output: str, status: str) -> int:
    """Parse Rich table row: status name, then Count column.

    Rich panels prefix rows with box-drawing chars (e.g. │), so do not
    require the status to start the line after only whitespace.
    """
    pattern = rf"(?m)^[^\n]*?{re.escape(status)}\s+(\d+)\s+"
    match = re.search(pattern, output)
    assert match is not None, f"status row '{status}' not found in:\n{output}"
    return int(match.group(1))


def test_get_stats_refined_count_matches_segments(workspace: Path) -> None:
    save_segments(
        workspace,
        "main",
        [
            make_seg("aaa111111111", SegmentStatus.REFINED, reflection_used=True),
            make_seg("bbb222222222", SegmentStatus.REFINED, reflection_used=True),
            make_seg("ccc333333333", SegmentStatus.REFINED),
            make_seg("ddd444444444", SegmentStatus.CONFLICT, translation=""),
            make_seg("eee555555555", SegmentStatus.GENERATED, translation=""),
        ],
    )
    stats = TMService(str(workspace)).get_stats("main")
    assert stats["refined"] == 3
    assert stats["conflict"] == 1
    assert stats["generated"] == 1
    assert stats["total"] == 5
    assert stats["tokens_refined"] > 0
    assert stats["reflection_refined"] == 2  # used and not draft_accepted


def test_tm_status_cli_refined_count_matches_list(workspace: Path) -> None:
    """RG-01 lock: status Count for refined must equal list cardinality."""
    save_segments(
        workspace,
        "main",
        [
            make_seg(
                "r11111111111",
                SegmentStatus.REFINED,
                source="Alpha paragraph with enough tokens.",
                reflection_used=True,
            ),
            make_seg(
                "r22222222222",
                SegmentStatus.REFINED,
                source="Beta paragraph with enough tokens.",
                reflection_used=True,
            ),
            make_seg(
                "r33333333333",
                SegmentStatus.REFINED,
                source="Gamma paragraph with enough tokens.",
            ),
            make_seg(
                "c44444444444",
                SegmentStatus.CONFLICT,
                source="Conflict paragraph.",
                translation="",
            ),
        ],
    )

    status = runner.invoke(app, ["tm", "status", "main"])
    assert status.exit_code == 0, status.output
    refined_count = _count_from_status_output(status.output, "refined")
    conflict_count = _count_from_status_output(status.output, "conflict")

    listed = runner.invoke(app, ["tm", "list", "main", "--status", "refined"])
    assert listed.exit_code == 0, listed.output
    list_match = re.search(r"Total matching segments:\s*(\d+)", listed.output)
    assert list_match is not None, listed.output
    list_n = int(list_match.group(1))

    assert refined_count == 3
    assert refined_count == list_n
    assert conflict_count == 1
    # Tokens column for refined must be non-zero when count is non-zero
    assert re.search(r"(?m)^[^\n]*?refined\s+3\s+.*[1-9]", status.output)
