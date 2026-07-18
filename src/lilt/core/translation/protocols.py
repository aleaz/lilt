"""Protocols for translation execution strategies."""

from collections.abc import Iterable
from typing import Protocol


class ReflectionStrategy(Protocol):
    """Protocol for translation execution strategies."""

    def run_iter(
        self,
        namespace: str,
        force: bool = False,
        segment_id: str | None = None,
        status_filter: str | None = None,
        stage: str | None = None,
    ) -> Iterable[dict]:
        """Execute the translation pipeline iteratively."""
        ...
