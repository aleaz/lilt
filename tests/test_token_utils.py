"""Tests for offline-safe token counting."""

from unittest.mock import MagicMock

import tiktoken

import lilt.utils.token_utils as token_utils


def test_count_tokens_uses_bundled_encoding_when_model_lookup_fails(monkeypatch):
    """count_tokens must not require network when encoding_for_model fails."""
    token_utils._encoder = None
    fallback = MagicMock()
    fallback.encode.return_value = [1, 2, 3]
    monkeypatch.setattr(
        tiktoken,
        "encoding_for_model",
        MagicMock(side_effect=OSError("network unavailable")),
    )
    monkeypatch.setattr(tiktoken, "get_encoding", MagicMock(return_value=fallback))
    count = token_utils.count_tokens("hello world")
    assert count == 3


def test_count_tokens_returns_positive_for_non_empty_text():
    token_utils._encoder = None
    count = token_utils.count_tokens("The quick brown fox")
    assert count > 0
