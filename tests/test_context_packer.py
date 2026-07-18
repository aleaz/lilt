"""Unit tests for ContextPacker neighbor packing."""

from lilt.llm.context_packer import ContextPacker
from lilt.utils.token_utils import count_tokens


def test_packer_fits_one_neighbor_truncates_second() -> None:
    # backward is chronological [distant, recent]; packing prefers recent first.
    distant = "alpha " * 20
    recent = "beta " * 20
    recent_tokens = count_tokens(recent)
    budget = recent_tokens + 1  # distant cannot fit after recent

    block, used, truncated = ContextPacker.pack(
        backward=[distant, recent],
        forward=[],
        neighbor_budget=budget,
        count_tokens=count_tokens,
    )

    assert truncated is True
    assert "beta" in block
    assert "alpha" not in block
    assert used <= budget


def test_packer_empty_when_budget_zero() -> None:
    block, used, truncated = ContextPacker.pack(
        backward=["hello world"],
        forward=[],
        neighbor_budget=0,
        count_tokens=count_tokens,
    )
    assert block == ""
    assert used == 0
    assert truncated is True
