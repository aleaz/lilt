"""F-09: placeholder mismatch messages include recovery next steps."""

from __future__ import annotations

import pytest

from lilt.parser.placeholder_contract import validate_counts

pytestmark = pytest.mark.release


def test_placeholder_mismatch_includes_next_steps() -> None:
    with pytest.raises(ValueError, match="Placeholder mismatch") as exc_info:
        validate_counts(
            'Hello <inline id="1"/>',
            "Hello",
        )
    msg = str(exc_info.value)
    assert "tm status" in msg
    assert "tm list" in msg
    assert "--allow-partial" in msg
