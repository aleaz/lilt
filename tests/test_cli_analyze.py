"""Tests for `lilt project configure --dry-run` (static analysis)."""

import pytest
from typer.testing import CliRunner

from lilt.cli.main import app
from lilt.parser.analyzer import ProjectAnalyzer

runner = CliRunner()


@pytest.fixture
def tex_project(tmp_path):
    """A minimal LaTeX project with one file containing custom macros."""
    tex = tmp_path / "main.tex"
    tex.write_text(
        r"""
\documentclass{article}
\begin{document}
\customMacro{argument one}
\anotherCmd{foo}{bar}
\lstinline|some code|
\begin{custEnv}
Some text here.
\end{custEnv}
\end{document}
""",
        encoding="utf-8",
    )
    return tmp_path


def test_analyze_discovers_unknown_macros(tex_project):
    """Analyze should report unknown macros in the source."""
    result = runner.invoke(
        app, ["-C", str(tex_project), "project", "configure", "--dry-run", "."]
    )
    assert result.exit_code == 0, result.output
    # customMacro is not a standard LaTeX macro
    assert "customMacro" in result.output or "anotherCmd" in result.output


def test_analyze_reports_file_count(tex_project):
    """Header panel should mention the number of files scanned."""
    result = runner.invoke(
        app, ["-C", str(tex_project), "project", "configure", "--dry-run", "."]
    )
    assert result.exit_code == 0
    assert "Files Scanned" in result.output
    assert "1" in result.output  # one .tex file


def test_analyze_shows_verbatim_usage(tex_project):
    """Lstinline usage should appear in the verbatim table."""
    result = runner.invoke(
        app, ["-C", str(tex_project), "project", "configure", "--dry-run", "."]
    )
    assert result.exit_code == 0
    assert "lstinline" in result.output


def test_analyze_gaps_flag(tex_project):
    """--gaps flag should show a gaps section."""
    result = runner.invoke(
        app,
        ["-C", str(tex_project), "project", "configure", "--dry-run", ".", "--gaps"],
    )
    assert result.exit_code == 0
    # Either a gap table or the no-gaps message
    assert "Syntax Gap" in result.output or "No syntax gaps" in result.output


def test_analyze_no_unknown_macros(tmp_path):
    """When all macros are standard, report a clean confirmation."""
    tex = tmp_path / "simple.tex"
    tex.write_text(
        r"\documentclass{article}\begin{document}Hello world.\end{document}",
        encoding="utf-8",
    )
    result = runner.invoke(
        app, ["-C", str(tmp_path), "project", "configure", "--dry-run", "."]
    )
    assert result.exit_code == 0
    assert "No unknown macros found" in result.output


def test_analyze_invalid_path(tmp_path):
    """Analyze should exit with error code 1 for a non-existent path."""
    result = runner.invoke(
        app, ["-C", str(tmp_path), "project", "configure", "--dry-run", "nonexistent/"]
    )
    assert result.exit_code == 1
    assert "does not exist" in " ".join(result.output.split())


def test_analyze_dry_run_does_not_modify_config(tex_project):
    """Analyze must never create or modify lilt.yaml."""
    config_path = tex_project / ".lilt" / "lilt.yaml"
    assert not config_path.exists()

    runner.invoke(
        app, ["-C", str(tex_project), "project", "configure", "--dry-run", "."]
    )

    assert not config_path.exists(), "analyze must not create lilt.yaml"


def test_analyzer_argument_inference(tmp_path):
    tex = tmp_path / "main.tex"
    # \myCustomCmd has an optional argument [opt] and a mandatory one {mand}
    # \nestedMacro is inside an environment argument
    tex.write_text(
        r"""
\documentclass{article}
\begin{document}
\myCustomCmd[optional]{mandatory}
\begin{tabular}{\nestedMacro}
\end{tabular}
\end{document}
""",
        encoding="utf-8",
    )

    analyzer = ProjectAnalyzer(config_path=str(tmp_path / "lilt.yaml"))
    report = analyzer.analyze_directory(str(tmp_path))

    # \myCustomCmd should be inferred to have 1 mandatory argument, NOT 2
    assert report.macro_args_inferred.get("myCustomCmd") == 1
    # \nestedMacro should be discovered even though it is inside an environment argument
    assert "nestedMacro" in report.unknown_macros


def test_analyzer_ignores_control_symbols(tmp_path):
    tex = tmp_path / "main.tex"
    tex.write_text(
        r"""
\documentclass{article}
\begin{document}
\@ \def\foo{bar} \{ \1
\end{document}
""",
        encoding="utf-8",
    )
    analyzer = ProjectAnalyzer(config_path=str(tmp_path / "lilt.yaml"))
    report = analyzer.analyze_directory(str(tmp_path))
    assert "@" not in report.unknown_macros
    assert "def" not in report.unknown_macros
    assert "{" not in report.unknown_macros
    assert "1" not in report.unknown_macros


def test_analyzer_caps_inferred_args(tmp_path):
    tex = tmp_path / "main.tex"
    tex.write_text(
        r"""
\documentclass{article}
\begin{document}
\myMacro{a}{b}{c}{d}{e}{f}
\end{document}
""",
        encoding="utf-8",
    )
    analyzer = ProjectAnalyzer(config_path=str(tmp_path / "lilt.yaml"))
    report = analyzer.analyze_directory(str(tmp_path))
    assert (
        report.unknown_macros_with_args.get("myMacro", 0)
        <= ProjectAnalyzer.MAX_INFERRED_ARGS
    )


def test_analyzer_skips_primitives(tmp_path):
    tex = tmp_path / "main.tex"
    tex.write_text(
        r"""
\documentclass{article}
\begin{document}
\SetMathAlphabet{a}{b}{c}{d}{e}{f}
\DeclareMathAlphabet{foo}{bar}{baz}{qux}{quux}
\end{document}
""",
        encoding="utf-8",
    )
    analyzer = ProjectAnalyzer(config_path=str(tmp_path / "lilt.yaml"))
    report = analyzer.analyze_directory(str(tmp_path))
    assert "SetMathAlphabet" not in report.unknown_macros
    assert "DeclareMathAlphabet" not in report.unknown_macros


def test_analyzer_infers_args_from_newcommand_definition(tmp_path):
    tex = tmp_path / "main.tex"
    tex.write_text(
        r"""
\documentclass{article}
\newcommand{\fileref}[2]{#1:#2}
\begin{document}
\fileref{kernel/trap.c}
\end{document}
""",
        encoding="utf-8",
    )
    analyzer = ProjectAnalyzer(config_path=str(tmp_path / "lilt.yaml"))
    report = analyzer.analyze_directory(str(tmp_path))
    assert report.macro_args_inferred.get("fileref") == 2
    assert report.unknown_macros_with_args.get("fileref") == 2
