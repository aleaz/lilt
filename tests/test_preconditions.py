"""Tests for workspace preconditions."""

import os
import tempfile

import pytest

from lilt.exceptions import NamespaceNotFoundError, ProjectNotInitializedError
from lilt.services.preconditions import WorkspacePreconditions
from lilt.tm.repository import TMRepository


def test_require_initialized_raises():
    with tempfile.TemporaryDirectory() as tmpdir:
        pre = WorkspacePreconditions(
            tmpdir,
            os.path.join(tmpdir, ".lilt", "lilt.yaml"),
            os.path.join(tmpdir, ".lilt", "tm"),
            TMRepository(os.path.join(tmpdir, ".lilt", "tm")),
        )
        with pytest.raises(ProjectNotInitializedError):
            pre.require_initialized()


def test_require_namespace_missing_file():
    with tempfile.TemporaryDirectory() as tmpdir:
        lilt_dir = os.path.join(tmpdir, ".lilt")
        tm_dir = os.path.join(lilt_dir, "tm")
        os.makedirs(tm_dir)
        config_path = os.path.join(lilt_dir, "lilt.yaml")
        with open(config_path, "w", encoding="utf-8") as f:
            f.write("project:\n  source_lang: English\n")

        pre = WorkspacePreconditions(tmpdir, config_path, tm_dir, TMRepository(tm_dir))
        with pytest.raises(NamespaceNotFoundError):
            pre.require_namespace("missing")
