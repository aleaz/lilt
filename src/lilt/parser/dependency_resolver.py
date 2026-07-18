"""Resolve LaTeX file and package dependency graphs for batch operations."""

import logging
import os
import re

from lilt.utils.file_utils import read_text_file_resilient

logger = logging.getLogger(__name__)


class DependencyResolver:
    r"""Resolves the LaTeX project dependency graph by automatically finding the root file.

    (containing \documentclass) and recursively tracking \usepackage, \input, and \include.

    Stateless between calls: each resolution creates its own `visited` set, so the same
    instance can be safely reused and called multiple times without cross-contamination.
    """

    def __init__(self, project_dir: str):
        self.project_dir = os.path.abspath(project_dir)

    def resolve(self) -> list[str]:
        r"""Executes the dependency resolution and returns a list of related .tex files.

        Auto-detects the root file by searching for \\documentclass in the project directory.
        """
        visited: set[str] = set()

        tex_files = []
        for root, dirs, files in os.walk(self.project_dir):
            # Prune hidden directories and the build directory (i18n) in-place so os.walk doesn't traverse them
            dirs[:] = [d for d in dirs if not d.startswith(".") and d != "i18n"]

            for file in files:
                if file.endswith(".tex"):
                    tex_files.append(os.path.join(root, file))

        if not tex_files:
            return []

        roots = []
        for f in tex_files:
            try:
                content = read_text_file_resilient(f)
                if r"\documentclass" in content:
                    roots.append(f)
            except Exception:
                pass

        # Fallback: if no documentclass is found, treat all tex files as independent roots
        if not roots:
            roots = tex_files

        for root in roots:
            self._traverse(root, visited)

        return sorted(list(visited))

    def resolve_from(self, entry_point: str) -> list[str]:
        r"""Resolve all dependencies starting from a specific entry point file.

        Unlike `resolve()`, this method does not auto-detect the root: it starts
        traversal from the given file and follows all \\input/\\include directives.

        Args:
            entry_point: Absolute or relative path to the entry LaTeX file.

        Returns:
            A sorted list of absolute paths to all dependent .tex/.sty/.cls files.
        """
        visited: set[str] = set()
        self._traverse(os.path.abspath(entry_point), visited)
        return sorted(list(visited))

    def _traverse(self, file_path: str, visited: set[str]) -> None:
        """Recursively traverse a LaTeX file and its dependencies.

        Args:
            file_path: Absolute path to the file to traverse.
            visited: The per-call set of already-visited files. Passed explicitly
                     to ensure each resolution call is fully isolated.
        """
        if not os.path.exists(file_path):
            if not file_path.endswith(".tex") and os.path.exists(file_path + ".tex"):
                file_path += ".tex"
            elif not file_path.endswith(".sty") and os.path.exists(file_path + ".sty"):
                file_path += ".sty"
            elif not file_path.endswith(".cls") and os.path.exists(file_path + ".cls"):
                file_path += ".cls"
            else:
                return

        file_path = os.path.abspath(file_path)
        if file_path in visited:
            return

        visited.add(file_path)

        try:
            content = read_text_file_resilient(file_path)
        except Exception:
            return

        # Handle \usepackage{pkg1,pkg2}
        pkg_pattern = re.compile(
            r"\\(?:usepackage|RequirePackage)(?:\[[^\]]*\])?\{([^}]+)\}"
        )
        for match in pkg_pattern.finditer(content):
            pkgs = [p.strip() for p in match.group(1).split(",")]
            for pkg in pkgs:
                pkg_path = os.path.join(self.project_dir, f"{pkg}.sty")
                if os.path.exists(pkg_path):
                    self._traverse(pkg_path, visited)

        # Handle \input{file} or \include{file} or \input file
        input_pattern = re.compile(
            r"\\(?:input|include)\s*\{([^}]+)\}|\\input\s+([^\s%]+)"
        )
        file_dir = os.path.dirname(file_path)
        for match in input_pattern.finditer(content):
            inc_file = match.group(1) or match.group(2)
            if inc_file:
                inc_path = os.path.join(file_dir, inc_file)
                if (
                    not os.path.exists(inc_path)
                    and not inc_path.endswith(".tex")
                    and os.path.exists(inc_path + ".tex")
                ):
                    inc_path += ".tex"

                if os.path.exists(inc_path):
                    self._traverse(inc_path, visited)
                    continue

                inc_path_proj = os.path.join(self.project_dir, inc_file)
                if (
                    not os.path.exists(inc_path_proj)
                    and not inc_path_proj.endswith(".tex")
                    and os.path.exists(inc_path_proj + ".tex")
                ):
                    inc_path_proj += ".tex"

                if os.path.exists(inc_path_proj):
                    self._traverse(inc_path_proj, visited)
                    continue

                if inc_file.startswith("latex.out/"):
                    base_name = inc_file[len("latex.out/") :]
                    latex_out_path = os.path.join(self.project_dir, base_name)
                    if (
                        not os.path.exists(latex_out_path)
                        and not latex_out_path.endswith(".tex")
                        and os.path.exists(latex_out_path + ".tex")
                    ):
                        latex_out_path += ".tex"
                    if os.path.exists(latex_out_path):
                        self._traverse(latex_out_path, visited)
                        continue

                base_inc = os.path.basename(inc_file)
                fallback_path = os.path.join(self.project_dir, base_inc)
                if (
                    not os.path.exists(fallback_path)
                    and not fallback_path.endswith(".tex")
                    and os.path.exists(fallback_path + ".tex")
                ):
                    fallback_path += ".tex"
                if os.path.exists(fallback_path):
                    logger.warning(
                        f"Dependency file '{inc_file}' not found at relative or project root path. "
                        f"Falling back to matching basename in project root: '{fallback_path}'."
                    )
                    self._traverse(fallback_path, visited)
