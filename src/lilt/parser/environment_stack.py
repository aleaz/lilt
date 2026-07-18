"""Environment and semantic-alias pairing with opaque fallback."""

from typing import Any


class EnvironmentStack:
    """Tracks open environments/aliases; masks unmatched spans as opaque."""

    def __init__(self) -> None:
        self._open_spans: list[tuple[str, int]] = []

    def open_alias(self, alias: str, start_pos: int) -> None:
        """Record the start position of a semantic alias begin macro."""
        self._open_spans.append((alias, start_pos))

    def close_alias(
        self,
        target_env: str,
        end_pos: int,
        aliases: dict[str, dict[str, str]],
        mask: Any,
    ) -> bool:
        """Close a matching open alias span; return True when paired."""
        for i in range(len(self._open_spans) - 1, -1, -1):
            alias, start_pos = self._open_spans[i]
            open_env = aliases.get(alias, {}).get("env")
            if open_env == target_env:
                mask.add_opaque(start_pos, end_pos, "ENV")
                del self._open_spans[i]
                return True
        return False

    def close_unmatched_as_opaque(self, mask: Any, text_len: int) -> None:
        """Mask any still-open alias spans through end of document."""
        for _, start_pos in self._open_spans:
            mask.add_opaque(start_pos, text_len, "ENV")
        self._open_spans.clear()

    def __len__(self) -> int:
        """Return the number of open alias spans."""
        return len(self._open_spans)
