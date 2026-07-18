"""Workspace path sandbox boundary tests."""

import os
import tempfile

import pytest

from lilt.services.preconditions import WorkspacePreconditions
from lilt.tm.repository import TMRepository
from lilt.utils.path_utils import path_is_under_workspace


def test_path_is_under_workspace_rejects_sibling_prefix():
    workspace = "/tmp/proj"
    assert path_is_under_workspace("/tmp/proj", workspace)
    assert path_is_under_workspace("/tmp/proj/chapters/a.tex", workspace)
    assert not path_is_under_workspace("/tmp/proj_evil/x.tex", workspace)
    assert not path_is_under_workspace("/tmp/proj_evil", workspace)


def test_require_path_exists_rejects_sibling_prefix_workspace():
    with tempfile.TemporaryDirectory() as parent:
        workspace = os.path.join(parent, "proj")
        sibling = os.path.join(parent, "proj_evil")
        os.makedirs(workspace)
        os.makedirs(sibling)
        evil_tex = os.path.join(sibling, "x.tex")
        with open(evil_tex, "w", encoding="utf-8") as f:
            f.write("% evil\n")

        tm_dir = os.path.join(workspace, ".lilt", "tm")
        os.makedirs(tm_dir)
        pre = WorkspacePreconditions(
            workspace,
            os.path.join(workspace, ".lilt", "lilt.yaml"),
            tm_dir,
            TMRepository(tm_dir),
        )
        with pytest.raises(ValueError, match="Security Error"):
            pre.require_path_exists(evil_tex)


def test_require_path_exists_accepts_path_under_workspace():
    with tempfile.TemporaryDirectory() as workspace:
        tex = os.path.join(workspace, "main.tex")
        with open(tex, "w", encoding="utf-8") as f:
            f.write("% ok\n")
        tm_dir = os.path.join(workspace, ".lilt", "tm")
        os.makedirs(tm_dir)
        pre = WorkspacePreconditions(
            workspace,
            os.path.join(workspace, ".lilt", "lilt.yaml"),
            tm_dir,
            TMRepository(tm_dir),
        )
        assert pre.require_path_exists(tex) == os.path.abspath(tex)
