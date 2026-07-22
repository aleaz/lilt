"""F-10: translate idle with remaining conflicts exits non-zero."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from lilt.cli.main import app
from lilt.models.segment import SegmentStatus
from tests.release.conftest import make_seg, runner, save_segments

pytestmark = pytest.mark.release


def test_translate_idle_with_conflicts_exits_nonzero(workspace: Path) -> None:
    save_segments(
        workspace,
        "main",
        [
            make_seg(
                "c11111111111",
                SegmentStatus.CONFLICT,
                source="Broken segment.",
                translation="",
            ),
            make_seg(
                "r22222222222",
                SegmentStatus.REFINED,
                source="Done segment.",
                translation="Listo.",
            ),
        ],
    )

    mock_strategy = MagicMock()
    # No eligible work: strategy yields nothing; service emits idle done.
    mock_strategy.run_iter.return_value = iter([])

    with patch(
        "lilt.services.pipeline_service.create_reflection_strategy",
        return_value=mock_strategy,
    ):
        result = runner.invoke(app, ["pipeline", "translate", "main", "--all"])

    assert result.exit_code == 1
    assert "conflict/error" in result.output.lower() or "conflict" in result.output
    assert "--allow-partial" in result.output or "tm list" in result.output
