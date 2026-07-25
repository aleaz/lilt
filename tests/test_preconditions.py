"""Tests for workspace preconditions."""

import os
import tempfile

import pytest

from lilt.exceptions import (
    NamespaceEmptyError,
    NamespaceNotFoundError,
    ProjectNotInitializedError,
)
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


def test_require_namespace_empty_file_raises_empty_error():
    with tempfile.TemporaryDirectory() as tmpdir:
        lilt_dir = os.path.join(tmpdir, ".lilt")
        tm_dir = os.path.join(lilt_dir, "tm")
        os.makedirs(tm_dir)
        config_path = os.path.join(lilt_dir, "lilt.yaml")
        with open(config_path, "w", encoding="utf-8") as f:
            f.write("project:\n  source_lang: English\n")

        repo = TMRepository(tm_dir)
        repo.save_namespace("fig__trap", [])
        pre = WorkspacePreconditions(tmpdir, config_path, tm_dir, repo)
        with pytest.raises(NamespaceEmptyError) as exc_info:
            pre.require_namespace("fig__trap")
        assert exc_info.value.namespace == "fig__trap"
        assert "no segments" in str(exc_info.value).lower()
