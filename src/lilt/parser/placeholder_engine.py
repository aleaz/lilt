"""Placeholder masking and unmasking for opaque LaTeX spans sent to the LLM."""

from lilt.parser.placeholder_contract import PLACEHOLDER_RE, reject_zero_length_ranges


class PlaceholderEngine:
    """Engine to replace designated opaque character ranges with unambiguous placeholders.

    It processes text before sending to the LLM, and handles the reverse operation (unmasking).
    """

    def __init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        """Clears all stored placeholder mappings and counters."""
        self.mapping: dict[str, str] = {}
        self.counters: dict[str, int] = {
            "MACRO": 1,
            "MATH": 1,
            "ENV": 1,
            "CITE": 1,
            "REF": 1,
            "BEGIN_ENV": 1,
            "END_ENV": 1,
            "COMMENT": 1,
            "ARG": 1,
            "GROUP_START": 1,
            "GROUP_END": 1,
            "TERM": 1,
            "BLOCK": 1,
        }

    def _generate_id(self, prefix: str) -> str:
        count = self.counters.get(prefix, 1)
        self.counters[prefix] += 1
        return f'<{prefix.lower()} id="{count}"/>'

    def mask_ranges(
        self,
        raw_text: str,
        opaque_ranges: list[tuple[int, int, str, str]],
        offset_start: int,
    ) -> str:
        """Replaces text slices inside raw_text with placeholders.

        Args:
            raw_text: The segment's raw text.
            opaque_ranges: List of (global_start, length, type, raw_string) from the AST flattener.
            offset_start: The global character index where raw_text begins in the source document.

        """
        segment_ranges = []
        offset_end = offset_start + len(raw_text)

        for r_start, r_len, r_type, r_raw in opaque_ranges:
            r_end = r_start + r_len
            # Check if range falls entirely within this segment
            if r_start >= offset_start and r_end <= offset_end:
                local_start = r_start - offset_start
                segment_ranges.append((local_start, r_len, r_type, r_raw))
            elif r_start < offset_end and r_end > offset_start:
                # This should theoretically never happen if chunk boundaries are aligned with the AST
                raise ValueError(
                    f"Opaque range {r_type} ({r_start}-{r_end}) crosses segment boundary ({offset_start}-{offset_end})"
                )

        reject_zero_length_ranges([(r[0], r[1], r[2], r[3]) for r in segment_ranges])

        # Sort ranges by start pos, then by length descending
        segment_ranges.sort(key=lambda x: (x[0], -x[1]))

        # Filter overlapping ranges (keep the outermost/first)
        filtered_ranges = []
        last_end = -1
        for r in segment_ranges:
            local_start, r_len, r_type, r_raw = r
            local_end = local_start + r_len

            if local_start >= last_end:
                # No overlap with the previous outermost range
                filtered_ranges.append(r)
                last_end = local_end
            else:
                # This range overlaps or is inside the previous range.
                # Since the previous range started earlier (or same time but is longer),
                # we just discard this inner/overlapping range to prevent placeholder corruption.
                pass

        # Sort back-to-front for safe replacement
        filtered_ranges.sort(key=lambda x: x[0], reverse=True)

        masked_text = raw_text
        for local_start, r_len, r_type, r_raw in filtered_ranges:
            pid = self._generate_id(r_type)
            self.mapping[pid] = r_raw
            masked_text = (
                masked_text[:local_start] + pid + masked_text[local_start + r_len :]
            )

        return self.compress_blocks(masked_text)

    def compress_blocks(self, text: str) -> str:
        """Compresses contiguous block placeholders to prevent the LLM from generating extra lines."""
        tag_regex = PLACEHOLDER_RE
        matches = list(tag_regex.finditer(text))
        if not matches:
            return text

        groups = []
        current_group = [matches[0]]
        for i in range(1, len(matches)):
            prev = current_group[-1]
            curr = matches[i]
            between = text[prev.end() : curr.start()]
            if between.isspace() or between == "":
                current_group.append(curr)
            else:
                groups.append(current_group)
                current_group = [curr]
        groups.append(current_group)

        compressed_text = ""
        last_end = 0
        for group in groups:
            if len(group) > 1:
                start = group[0].start()
                end = group[-1].end()

                compressed_text += text[last_end:start]
                block_id = self._generate_id("BLOCK")
                original_slice = text[start:end]

                raw_latex = original_slice
                for m in group:
                    pid = m.group()
                    if pid in self.mapping:
                        raw_latex = raw_latex.replace(pid, self.mapping[pid])
                        del self.mapping[pid]

                self.mapping[block_id] = raw_latex
                compressed_text += block_id
                last_end = end

        compressed_text += text[last_end:]
        return compressed_text
