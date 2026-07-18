"""TM namespace derivation from LaTeX file paths."""

import os

from lilt.utils.path_utils import path_is_under_workspace


def derive_namespace(workspace_dir: str, file_path: str) -> str:
    """Derive a stable TM namespace from a LaTeX file path relative to the workspace.

    Root-level files keep the basename (e.g. ``main.tex`` -> ``main``).
    Nested files encode directory separators as ``__`` (e.g.
    ``chapters/intro.tex`` -> ``chapters__intro``).
    """
    abs_workspace = os.path.realpath(workspace_dir)
    abs_file = os.path.realpath(
        file_path
        if os.path.isabs(file_path)
        else os.path.join(workspace_dir, file_path)
    )
    if path_is_under_workspace(abs_file, abs_workspace):
        rel = os.path.relpath(abs_file, abs_workspace)
    else:
        rel = os.path.basename(abs_file)

    rel_no_ext = os.path.splitext(rel)[0]
    return rel_no_ext.replace(os.sep, "__")


def find_namespace_collisions(workspace_dir: str, file_path: str) -> list[str]:
    """Return other ``.tex`` paths under the workspace that share ``file_path``'s namespace.

    Encoding uses ``__`` for directory separators, so e.g. ``chapters/intro.tex`` and
    ``chapters__intro.tex`` collide. Callers should fail loud rather than merge TM.
    """
    abs_workspace = os.path.realpath(workspace_dir)
    abs_file = os.path.realpath(
        file_path
        if os.path.isabs(file_path)
        else os.path.join(workspace_dir, file_path)
    )
    if not path_is_under_workspace(abs_file, abs_workspace):
        return []

    target_ns = derive_namespace(workspace_dir, abs_file)
    collisions: list[str] = []
    for root, dirs, files in os.walk(abs_workspace):
        dirs[:] = [d for d in dirs if d != ".lilt"]
        for name in files:
            if not name.lower().endswith(".tex"):
                continue
            candidate = os.path.join(root, name)
            if os.path.realpath(candidate) == abs_file:
                continue
            if derive_namespace(workspace_dir, candidate) == target_ns:
                collisions.append(candidate)
    return collisions
