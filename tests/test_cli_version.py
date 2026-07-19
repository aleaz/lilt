"""Tests for root CLI global options."""

from typer.testing import CliRunner

from lilt.cli.main import __version__, app

runner = CliRunner()


def test_version_flag_prints_package_version() -> None:
    """``lilt --version`` reports the installed distribution version."""
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert f"lilt {__version__}" in result.stdout
    assert __version__ != "0.0.0+unknown"
