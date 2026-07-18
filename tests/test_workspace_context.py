import os
import tempfile

import pytest

from lilt.exceptions import WorkspacePathError
from lilt.services.workspace_context import WorkspaceContext


def test_from_workspace_paths():
    with tempfile.TemporaryDirectory() as tmpdir:
        ctx = WorkspaceContext.from_workspace(tmpdir)
        abs_tmp = os.path.abspath(tmpdir)
        assert ctx.workspace_dir == abs_tmp
        assert ctx.lilt_dir == os.path.join(abs_tmp, ".lilt")
        assert ctx.config_path == os.path.join(abs_tmp, ".lilt", "lilt.yaml")
        assert ctx.tm_dir == os.path.join(abs_tmp, ".lilt", "tm")
        assert ctx.repo.base_dir == ctx.tm_dir


def test_telemetry_lazy_singleton():
    with tempfile.TemporaryDirectory() as tmpdir:
        ctx = WorkspaceContext.from_workspace(tmpdir)
        first = ctx.telemetry
        second = ctx.telemetry
        assert first is second
        assert ctx.telemetry_db_path == first.db_path


def test_resolve_under_workspace_rejects_sibling_prefix():
    with tempfile.TemporaryDirectory() as parent:
        workspace = os.path.join(parent, "proj")
        sibling = os.path.join(parent, "proj_evil")
        os.makedirs(workspace)
        os.makedirs(sibling)
        evil_tex = os.path.join(sibling, "x.tex")
        with open(evil_tex, "w", encoding="utf-8") as f:
            f.write("% evil\n")

        ctx = WorkspaceContext.from_workspace(workspace)
        with pytest.raises(WorkspacePathError):
            ctx.resolve_under_workspace(evil_tex)


def test_resolve_under_workspace_accepts_path_under_workspace():
    with tempfile.TemporaryDirectory() as workspace:
        tex = os.path.join(workspace, "main.tex")
        with open(tex, "w", encoding="utf-8") as f:
            f.write("% ok\n")
        ctx = WorkspaceContext.from_workspace(workspace)
        assert ctx.resolve_under_workspace(tex) == os.path.abspath(tex)
