"""Cooperative translation abort (SIGINT / SIGTERM)."""

from __future__ import annotations

import threading

_abort = threading.Event()


def request_abort() -> None:
    """Request stop after the current segment boundary."""
    _abort.set()


def clear_abort() -> None:
    """Clear abort before a new translate run."""
    _abort.clear()


def is_abort_requested() -> bool:
    """Return True if translate abort has been requested."""
    return _abort.is_set()


def check_abort() -> None:
    """Raise KeyboardInterrupt when abort was requested."""
    if _abort.is_set():
        raise KeyboardInterrupt
