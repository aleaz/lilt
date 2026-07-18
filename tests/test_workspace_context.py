import os
import tempfile

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
