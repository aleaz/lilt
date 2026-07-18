"""TM namespace derivation from LaTeX file paths."""

import os


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
    if abs_file.startswith(abs_workspace + os.sep) or abs_file == abs_workspace:
        rel = os.path.relpath(abs_file, abs_workspace)
    else:
        rel = os.path.basename(abs_file)

    rel_no_ext = os.path.splitext(rel)[0]
    return rel_no_ext.replace(os.sep, "__")
