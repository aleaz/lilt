"""Path sandbox helpers for workspace-relative operations."""

import os


def path_is_under_workspace(real_path: str, real_workspace: str) -> bool:
    """Return True if ``real_path`` is the workspace or a descendant of it.

    Uses an explicit separator boundary so sibling prefixes such as
    ``/tmp/proj_evil`` are not treated as under ``/tmp/proj``.
    """
    if real_path == real_workspace:
        return True
    return real_path.startswith(real_workspace + os.sep)
