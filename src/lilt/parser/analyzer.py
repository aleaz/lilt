"""Static project analyzer for unknown macros, environments, and config gaps."""

import contextlib
import os
import re
import warnings
from collections import Counter

from pylatexenc.latexwalker import (
    LatexCharsNode,
    LatexEnvironmentNode,
    LatexGroupNode,
    LatexMacroNode,
    LatexWalker,
    get_default_latex_context_db,
)

from lilt.utils.file_utils import read_text_file_resilient
from lilt.utils.yaml_loader import load_yaml_config

from .dependency_resolver import DependencyResolver

_SAFE_MACRO_NAME_RE = re.compile(r"^[a-zA-Z]{2,}$")
_NEWCOMMAND_DEF_RE = re.compile(
    r"\\(?:newcommand|renewcommand|providecommand)\*?\{?\\([a-zA-Z]+)\}?"
    r"(?:\[(\d+)\])?",
)
_DEF_MACRO_RE = re.compile(r"\\def\\([a-zA-Z@]+)((?:#\d)+)")


class AnalysisReport:
    """Aggregates metrics and statistics for the LaTeX project analysis."""

    def __init__(self) -> None:
        self.total_files = 0
        self.macros: Counter[str] = Counter()
        self.environments: Counter[str] = Counter()
        self.gaps: list[tuple[str, int, int, str]] = []  # filepath, start, end, text

        # We will populate these during final analysis
        self.unknown_macros: set[str] = set()
        self.unknown_macros_with_args: dict[str, int] = {}
        self.verbatim_usage: Counter = Counter()
        self.macro_args_inferred: dict[str, int] = {}
        self.environment_aliases: dict[str, dict] = {}


class ProjectAnalyzer:
    """Analyzes LaTeX projects to discover unknown macros and environments."""

    VERBATIM_MACROS = {"lstinline", "verb"}
    MAX_INFERRED_ARGS = 2
    UNSAFE_MACROS = frozenset(
        {
            "def",
            "let",
            "edef",
            "gdef",
            "xdef",
            "newcommand",
            "renewcommand",
            "providecommand",
            "makeatletter",
            "makeatother",
            "left",
            "right",
            "bf",
            "em",
            "rm",
            "it",
            "sf",
            "tt",
            "SetMathAlphabet",
            "DeclareMathAlphabet",
        }
    )

    def __init__(self, config_path: str = "lilt.yaml") -> None:
        self.config_path = config_path
        self.user_macros: set[str] = set()
        self.load_config()
        self.db = get_default_latex_context_db()

    def load_config(self) -> None:
        """Load known user macros from the lilt.yaml configuration."""
        if os.path.exists(self.config_path):
            try:
                data = load_yaml_config(self.config_path)
                if data and "parser" in data and "custom_macros" in data["parser"]:
                    for m in data["parser"]["custom_macros"]:
                        if "name" in m:
                            self.user_macros.add(m["name"])
            except Exception as e:
                warnings.warn(
                    f"Failed to load {self.config_path}: {e}",
                    UserWarning,
                    stacklevel=2,
                )

    def analyze_directory(self, path: str) -> AnalysisReport:
        """Analyze a directory or file and return a report of discovered macros/environments."""
        report = AnalysisReport()
        if os.path.isfile(path):
            files = [path]
        else:
            resolver = DependencyResolver(path)
            files = resolver.resolve()

        opaque_environments = {
            "equation",
            "equation*",
            "align",
            "align*",
            "gather",
            "gather*",
            "eqnarray",
            "eqnarray*",
            "cases",
            "lstlisting",
            "tikzpicture",
        }

        alias_pattern = re.compile(
            r"\\(?:newcommand|def|renewcommand|providecommand)\*?\{?\\([a-zA-Z]+)\}?\s*\{?\\(begin|end)\{([a-zA-Z*]+)\}\}?"
        )
        environment_aliases = {}

        for f in files:
            report.total_files += 1
            content = read_text_file_resilient(f)

            for match in alias_pattern.finditer(content):
                alias_macro = match.group(1)
                alias_type = match.group(2)
                target_env = match.group(3)
                if target_env in opaque_environments:
                    environment_aliases[alias_macro] = {
                        "type": alias_type,
                        "env": target_env,
                    }

            if f.endswith(".tex"):
                self._analyze_file(f, report, content)
                self._collect_definition_args(content, report)

        if environment_aliases:
            report.environment_aliases = environment_aliases

        self._cross_reference(report)
        return report

    def _analyze_file(
        self, filepath: str, report: AnalysisReport, content: str | None = None
    ) -> None:
        if content is None:
            content = read_text_file_resilient(filepath)

        nodes = None
        # We use a permissive walker to gather nodes
        walker = LatexWalker(content, latex_context=self.db)
        with contextlib.suppress(Exception):
            nodes, _, _ = walker.get_latex_nodes()

        if nodes is None:
            return

        self._visit_nodes(nodes, content, filepath, report)

    def _visit_nodes(
        self, node_list: list, text: str, filepath: str, report: AnalysisReport
    ) -> None:
        """Recursively visits nodes."""
        if not node_list:
            return

        current_expected_pos = None

        for i, n in enumerate(node_list):
            if n is None:
                continue

            if current_expected_pos is None:
                current_expected_pos = n.pos

            if n.pos > current_expected_pos:
                gap_text = text[current_expected_pos : n.pos]
                if gap_text.strip():
                    report.gaps.append(
                        (filepath, current_expected_pos, n.pos, gap_text)
                    )

            if isinstance(n, LatexMacroNode):
                report.macros[n.macroname] += 1
                if n.macroname in self.VERBATIM_MACROS:
                    report.verbatim_usage[n.macroname] += 1

                # Infer argument count for unknown macros (only count mandatory brace arguments)
                args_count = 0
                j = i + 1
                while j < len(node_list):
                    next_n = node_list[j]
                    if next_n is None:
                        j += 1
                        continue
                    if isinstance(next_n, LatexCharsNode):
                        stripped = next_n.chars.strip()
                        if (
                            not stripped
                            or stripped.startswith("[")
                            and stripped.endswith("]")
                        ):
                            j += 1
                            continue
                        else:
                            break
                    elif isinstance(next_n, LatexGroupNode):
                        if next_n.delimiters and next_n.delimiters[0] == "{":
                            args_count += 1
                            j += 1
                        else:
                            # Optional arguments or other delimiters do not count as mandatory args
                            break
                    else:
                        break

                if args_count > report.macro_args_inferred.get(n.macroname, -1):
                    report.macro_args_inferred[n.macroname] = min(
                        args_count, self.MAX_INFERRED_ARGS
                    )

                if n.nodeargs:
                    self._visit_nodes(n.nodeargs, text, filepath, report)

            elif isinstance(n, LatexEnvironmentNode):
                report.environments[n.environmentname] += 1
                if n.nodeargd and n.nodeargd.argnlist:
                    self._visit_nodes(n.nodeargd.argnlist, text, filepath, report)
                if n.nodelist:
                    self._visit_nodes(n.nodelist, text, filepath, report)

            elif hasattr(n, "nodelist") and n.nodelist:
                self._visit_nodes(n.nodelist, text, filepath, report)

            current_expected_pos = n.pos + n.len

    def _collect_definition_args(self, content: str, report: AnalysisReport) -> None:
        r"""Infer macro arity from \newcommand/\def declarations in source."""
        for match in _NEWCOMMAND_DEF_RE.finditer(content):
            name = match.group(1)
            arg_count = match.group(2)
            if not _SAFE_MACRO_NAME_RE.match(name) or name in self.UNSAFE_MACROS:
                continue
            if arg_count is not None:
                inferred = min(int(arg_count), self.MAX_INFERRED_ARGS)
                current = report.macro_args_inferred.get(name, -1)
                if inferred > current:
                    report.macro_args_inferred[name] = inferred

        for match in _DEF_MACRO_RE.finditer(content):
            name = match.group(1)
            if not _SAFE_MACRO_NAME_RE.match(name) or name in self.UNSAFE_MACROS:
                continue
            inferred = min(match.group(2).count("#"), self.MAX_INFERRED_ARGS)
            current = report.macro_args_inferred.get(name, -1)
            if inferred > current:
                report.macro_args_inferred[name] = inferred

    def _cross_reference(self, report: AnalysisReport) -> None:
        # Default macros known by pylatexenc
        default_macros = set(spec.macroname for spec in self.db.iter_macro_specs())

        for m in report.macros:
            if m in default_macros or m in self.user_macros:
                continue
            if not _SAFE_MACRO_NAME_RE.match(m) or m in self.UNSAFE_MACROS:
                continue
            report.unknown_macros.add(m)
            report.unknown_macros_with_args[m] = min(
                report.macro_args_inferred.get(m, 0), self.MAX_INFERRED_ARGS
            )
