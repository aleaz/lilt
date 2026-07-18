"""Workspace path sandbox boundary tests."""

from lilt.utils.path_utils import path_is_under_workspace


def test_path_is_under_workspace_rejects_sibling_prefix():
    workspace = "/tmp/proj"
    assert path_is_under_workspace("/tmp/proj", workspace)
    assert path_is_under_workspace("/tmp/proj/chapters/a.tex", workspace)
    assert not path_is_under_workspace("/tmp/proj_evil/x.tex", workspace)
    assert not path_is_under_workspace("/tmp/proj_evil", workspace)
