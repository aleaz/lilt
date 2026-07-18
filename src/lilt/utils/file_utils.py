"""Resilient text file reading with encoding fallback."""

from pathlib import Path


def read_text_file_resilient(filepath: str | Path) -> str:
    """Attempt to read a file with utf-8.

    If a UnicodeDecodeError occurs, falls back to latin-1 to avoid crashing on legacy encodings.
    """
    try:
        with open(filepath, encoding="utf-8") as f:
            return f.read()
    except UnicodeDecodeError:
        with open(filepath, encoding="latin-1") as f:
            return f.read()
