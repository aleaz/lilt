"""Pack bidirectional neighbor segments into a context XML block under a token budget."""

from __future__ import annotations

from collections.abc import Callable


class ContextPacker:
    """Select neighbors with backward-first alternation until the token budget is spent."""

    @staticmethod
    def pack(
        *,
        backward: list[str],
        forward: list[str],
        neighbor_budget: int,
        count_tokens: Callable[[str], int],
    ) -> tuple[str, int, bool]:
        """Pack neighbors into an XML context block.

        Returns:
            ``(context_block_xml, neighbors_token_count, truncated)``.
            Empty string when nothing fits or there are no candidates.
        """
        if neighbor_budget <= 0 or (not backward and not forward):
            requested = len(backward) + len(forward)
            truncated = requested > 0 and neighbor_budget <= 0
            return "", 0, truncated

        b_idx = len(backward) - 1
        f_idx = 0
        selected_backward: list[str] = []
        selected_forward: list[str] = []
        current_tokens = 0

        while b_idx >= 0 or f_idx < len(forward):
            added = False
            if b_idx >= 0:
                seg = backward[b_idx]
                tokens = count_tokens(seg)
                if current_tokens + tokens <= neighbor_budget:
                    selected_backward.insert(0, seg)
                    current_tokens += tokens
                    b_idx -= 1
                    added = True
                else:
                    b_idx = -1

            if f_idx < len(forward):
                seg = forward[f_idx]
                tokens = count_tokens(seg)
                if current_tokens + tokens <= neighbor_budget:
                    selected_forward.append(seg)
                    current_tokens += tokens
                    f_idx += 1
                    added = True
                else:
                    f_idx = len(forward)

            if not added:
                break

        requested_total = len(backward) + len(forward)
        injected_total = len(selected_backward) + len(selected_forward)
        truncated = injected_total < requested_total

        if not selected_backward and not selected_forward:
            return "", 0, truncated

        parts = ["<context>"]
        if selected_backward:
            parts.append("<previous_segments>")
            parts.append("\n".join(selected_backward))
            parts.append("</previous_segments>")

        parts.append("<target_segment_position/>")

        if selected_forward:
            parts.append("<next_segments>")
            parts.append("\n".join(selected_forward))
            parts.append("</next_segments>")

        parts.append("</context>")
        return "\n".join(parts), current_tokens, truncated
