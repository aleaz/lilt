"""Entry point for running LILT as ``python -m lilt.cli``."""

from lilt.cli.main import app

if __name__ == "__main__":
    app(prog_name="lilt")
