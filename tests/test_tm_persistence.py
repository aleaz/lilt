"""Tests for TM persistence port behavior."""

import os
import tempfile

import pytest

from lilt.exceptions import TMCorruptionError
from lilt.tm.repository import TMRepository


def test_load_namespace_raises_on_corrupt_line():
    with tempfile.TemporaryDirectory() as tmpdir:
        repo = TMRepository(tmpdir)
        path = os.path.join(tmpdir, "main.jsonl")
        with open(path, "w", encoding="utf-8") as f:
            f.write("{not valid json}\n")
        with pytest.raises(TMCorruptionError):
            repo.load_namespace("main")
