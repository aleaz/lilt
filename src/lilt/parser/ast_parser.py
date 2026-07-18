"""AST-based LaTeX parser that splits documents into translatable segments."""

import functools
import hashlib
import os
import re
from typing import TYPE_CHECKING, Any

from pylatexenc.latexwalker import (
    LatexCharsNode,
    LatexCommentNode,
    LatexEnvironmentNode,
    LatexGroupNode,
    LatexMacroNode,
    LatexMathNode,
    LatexWalker,
    get_default_latex_context_db,
)
from pylatexenc.macrospec import MacroSpec, MacroStandardArgsParser, VerbatimArgsParser

from lilt.exceptions import ConfigurationError
from lilt.parser.environment_stack import EnvironmentStack
from lilt.parser.linguistic import has_linguistic_content
from lilt.parser.mask_policy import apply_macro_policy
from lilt.parser.placeholder_engine import PlaceholderEngine
from lilt.utils.config_loader import load_lilt_config
from lilt.utils.file_utils import read_text_file_resilient

if TYPE_CHECKING:
    from lilt.models.config import ParserConfig


class OpacityMask:
    """Manages character ranges in a string that should be masked (opaque)."""

    def __init__(self) -> None:
        self.ranges: list[tuple[int, int, str]] = []

    def add_opaque(self, start: int, end: int, rtype: str) -> None:
        """Registers a new opaque range from `start` to `end` with type `rtype`."""
        self.ranges.append((start, end, rtype))

    def punch_hole(self, hole_start: int, hole_end: int) -> None:
        """Punches a transparent hole inside an existing opaque range."""
        new_ranges = []
        for r_start, r_end, rtype in self.ranges:
            if hole_end <= r_start or hole_start >= r_end:
                # No overlap
                new_ranges.append((r_start, r_end, rtype))
            else:
                # Overlap exists. Split or truncate.
                if r_start < hole_start:
                    new_ranges.append((r_start, hole_start, rtype))
                if r_end > hole_end:
                    new_ranges.append((hole_end, r_end, rtype))
        self.ranges = new_ranges

    def get_ranges(self, text: str) -> list[tuple[int, int, str, str]]:
        """Returns a sorted list of non-overlapping opaque ranges."""
        self.ranges.sort(key=lambda x: (x[0], -(x[1] - x[0])))

        filtered = []
        last_end = -1
        for r_start, r_end, rtype in self.ranges:
            if r_start >= last_end:
                filtered.append((r_start, r_end - r_start, rtype, text[r_start:r_end]))
                last_end = r_end
        return filtered


class SegmentBlock:
    """Represents a discrete segment of text to be translated, along with its masked version."""

    def __init__(self, raw_text: str, masked_text: str, engine: PlaceholderEngine):
        self.raw_text = raw_text
        self.masked_text = masked_text
        self.engine = engine

    def is_translatable(self) -> bool:
        """Determines if the block contains translatable linguistic content."""
        return has_linguistic_content(self.masked_text)

    @functools.cached_property
    def source_hash(self) -> str:
        """Computes the full 64-character SHA-256 hash of the normalized source text."""
        normalized = " ".join(self.raw_text.split())
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

    @functools.cached_property
    def id(self) -> str:
        """Computes a stable 12-character identifier derived from the source hash."""
        return self.source_hash[:12]


class LstInlineArgsParser:
    r"""Custom parser for `\lstinline` macro arguments in pylatexenc."""

    def parse_args(self, w: Any, pos: int, parsing_state: Any = None) -> Any:
        r"""Parses the arbitrary delimiter character of `\lstinline`."""
        tok = w.s[pos : pos + 1]
        if tok == "{":
            return MacroStandardArgsParser("{").parse_args(w, pos, parsing_state)
        else:
            return VerbatimArgsParser(verbatim_arg_type="verb-macro").parse_args(
                w, pos, parsing_state
            )


class LatexParser:
    """Core parser that traverses the LaTeX AST and divides it into translatable segment blocks."""

    REF_MACROS = frozenset({"ref", "cref", "Cref", "autoref", "pageref", "eqref"})
    CITE_MACROS = frozenset({"cite", "citet", "citep", "citeyear"})
    FORMAT_MACROS = frozenset({"textcolor", "href"})
    LITERAL_END_CMD_RE = re.compile(r"\\end\{[a-zA-Z*@]+\}")

    def __init__(
        self,
        config_path: str = "lilt.yaml",
        parser_config: "ParserConfig | None" = None,
    ) -> None:
        self._boundary_regex = re.compile(r"\n\s*\n")
        self.max_segment_chars: int | None = None
        self.db = get_default_latex_context_db()
        self.db.add_context_category(
            "lilt_verbatim",
            macros=[
                MacroSpec(
                    "lstinline",
                    args_parser=LstInlineArgsParser(),
                ),
                MacroSpec(
                    "verb",
                    args_parser=VerbatimArgsParser(verbatim_arg_type="verb-macro"),
                ),
            ],
        )

        self.custom_macros: set[str] = set()
        self.opaque_environments = {
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

        self.protected_terms_regex: list[re.Pattern[str]] = []
        self.environment_aliases: dict[str, dict[str, str]] = {}

        # Semantic Macro Categories
        self.block_transparent_macros = {
            "section",
            "chapter",
            "subsection",
            "subsubsection",
            "paragraph",
            "title",
            "author",
            "date",
            "thanks",
            "item",
            "part",
            "subparagraph",
            "caption",  # when used outside figure
            "abstract",
        }
        self.inline_transparent_macros = {
            "textbf",
            "textit",
            "emph",
            "underline",
            "hl",
            "textsc",
            "textsf",
            "texttt",
        }
        self.segment_split_macros = frozenset({"AND", "noindent"})

        if parser_config is not None:
            self._apply_parser_config(parser_config)
        elif os.path.exists(config_path):
            self._apply_parser_config(load_lilt_config(config_path).parser)

    def _apply_parser_config(self, parser_conf: "ParserConfig") -> None:
        custom_macro_specs = []
        for macro in parser_conf.custom_macros:
            if "name" in macro:
                self.custom_macros.add(macro["name"])
                args_count = macro.get("args", 0)
                args_parser = "{" * args_count if args_count > 0 else ""
                custom_macro_specs.append(
                    MacroSpec(macro["name"], args_parser=args_parser)
                )

        if custom_macro_specs:
            self.db.add_context_category("lilt_custom", macros=custom_macro_specs)

        if parser_conf.opaque_environments:
            self.opaque_environments.update(parser_conf.opaque_environments)
        if parser_conf.block_transparent_macros:
            self.block_transparent_macros.update(parser_conf.block_transparent_macros)
        if parser_conf.inline_transparent_macros:
            self.inline_transparent_macros.update(parser_conf.inline_transparent_macros)
        if parser_conf.environment_aliases:
            self.environment_aliases.update(parser_conf.environment_aliases)
        for term in parser_conf.protected_terms:
            self.protected_terms_regex.append(re.compile(rf"\b{re.escape(term)}\b"))
        self.max_segment_chars = parser_conf.max_segment_chars

    def _traverse_ast(
        self,
        nodelist: list,
        text: str,
        mask: OpacityMask,
        boundaries: list[int],
        env_stack: EnvironmentStack | None = None,
    ) -> None:
        if env_stack is None:
            env_stack = EnvironmentStack()
        for node in nodelist:
            if node is not None:
                self._traverse_node(node, text, mask, boundaries, env_stack)

    def _find_env_end_start(
        self, node: LatexEnvironmentNode, env_name: str, text: str
    ) -> int | None:
        for child in reversed(node.nodelist or []):
            if (
                isinstance(child, LatexMacroNode)
                and child.macroname == "end"
                and child.nodeargd
                and child.nodeargd.argnlist
            ):
                arg = child.nodeargd.argnlist[0]
                if arg is None:
                    continue
                if isinstance(arg, LatexGroupNode) and arg.nodelist:
                    env_text = "".join(
                        n.chars for n in arg.nodelist if isinstance(n, LatexCharsNode)
                    )
                elif isinstance(arg, LatexCharsNode):
                    env_text = arg.chars
                else:
                    env_text = text[arg.pos : arg.pos + arg.len]
                if env_text.strip() == env_name:
                    return int(child.pos)

        return self._find_env_end_in_text(text, node.pos, env_name)

    def _find_env_end_in_text(
        self, text: str, start_pos: int, target_env: str
    ) -> int | None:
        r"""Find the start position of \end{target_env} outside verbatim/comments.

        Token-based scan avoids matching decoy \\end{...} strings inside \\verb,
        comments, or verbatim environments.
        """
        walker = LatexWalker(text, latex_context=self.db)
        pos = start_pos
        in_verbatim_env: str | None = None
        verb_envs = {"lstlisting", "verbatim", "minted", "alltt"}

        while pos < len(text):
            try:
                tok = walker.get_token(pos)
                if tok is None:
                    break

                if tok.tok == "comment":
                    pos = tok.pos + tok.len
                    continue

                if tok.tok == "macro" and tok.arg in ("verb", "lstinline"):
                    delim_pos = tok.pos + tok.len
                    if delim_pos < len(text):
                        delim = text[delim_pos]
                        close = text.find(delim, delim_pos + 1)
                        if close != -1:
                            pos = close + 1
                            continue

                if tok.tok == "begin_environment" and tok.arg in verb_envs:
                    if not in_verbatim_env:
                        in_verbatim_env = tok.arg
                elif tok.tok == "end_environment" and tok.arg == in_verbatim_env:
                    in_verbatim_env = None

                if (
                    in_verbatim_env is None
                    and tok.tok == "end_environment"
                    and tok.arg == target_env
                ):
                    return int(tok.pos)

                pos = tok.pos + tok.len
            except Exception:
                # Avoid O(N^2) fallback by jumping to the next possible LaTeX token
                next_slash = text.find("\\", pos + 1)
                next_percent = text.find("%", pos + 1)
                candidates = [p for p in (next_slash, next_percent) if p != -1]
                if not candidates:
                    break
                pos = min(candidates)
        return None

    def _mask_literal_ends_in_range(
        self, text: str, mask: OpacityMask, start: int, end: int
    ) -> None:
        r"""Mask literal \end{...} tokens in a raw text span (AST gaps)."""
        if start >= end:
            return
        for match in self.LITERAL_END_CMD_RE.finditer(text[start:end]):
            m_start = start + match.start()
            m_end = start + match.end()
            mask.add_opaque(m_start, m_end, "MACRO")

    def _mask_ast_gaps(
        self,
        node_list: list,
        text: str,
        mask: OpacityMask,
        *,
        span_start: int | None = None,
        span_end: int | None = None,
    ) -> None:
        r"""Mask literal \end{...} in gaps between sibling AST nodes."""
        nodes = [n for n in node_list if n is not None]
        if not nodes:
            return
        first = nodes[0]
        last = nodes[-1]
        gap_start = span_start if span_start is not None else first.pos
        gap_end = first.pos
        self._mask_literal_ends_in_range(text, mask, gap_start, gap_end)
        for i in range(len(nodes) - 1):
            left = nodes[i]
            right = nodes[i + 1]
            self._mask_literal_ends_in_range(text, mask, left.pos + left.len, right.pos)
        tail_start = last.pos + last.len
        tail_end = span_end if span_end is not None else tail_start
        self._mask_literal_ends_in_range(text, mask, tail_start, tail_end)

    def _mask_transparent_environment(
        self,
        node: LatexEnvironmentNode,
        text: str,
        mask: OpacityMask,
        boundaries: list,
        env_stack: EnvironmentStack,
    ) -> None:
        env_name = node.environmentname
        end_start = self._find_env_end_start(node, env_name, text)
        if end_start is None:
            mask.add_opaque(node.pos, node.pos + node.len, "ENV")
            return

        begin_len = node.nodelist[0].pos - node.pos if node.nodelist else node.len
        mask.add_opaque(node.pos, node.pos + begin_len, "BEGIN_ENV")
        body_start = node.pos + begin_len
        if node.nodelist:
            self._traverse_ast(node.nodelist, text, mask, boundaries, env_stack)
            self._mask_ast_gaps(
                node.nodelist, text, mask, span_start=body_start, span_end=end_start
            )
        else:
            self._mask_literal_ends_in_range(text, mask, body_start, end_start)
        mask.add_opaque(end_start, node.pos + node.len, "END_ENV")

    def _visit_math_node(
        self, node: LatexMathNode, text: str, mask: OpacityMask
    ) -> None:
        mask.add_opaque(node.pos, node.pos + node.len, "MATH")

    def _visit_comment_node(
        self, node: LatexCommentNode, text: str, mask: OpacityMask
    ) -> None:
        mask.add_opaque(node.pos, node.pos + node.len, "COMMENT")

    def _visit_environment_node(
        self,
        node: LatexEnvironmentNode,
        text: str,
        mask: OpacityMask,
        boundaries: list[int],
        env_stack: EnvironmentStack,
    ) -> None:
        env_name = node.environmentname
        env_spec = self.db.get_environment_spec(env_name)
        is_math = getattr(env_spec, "is_math_mode", False) if env_spec else False
        is_verbatim = (
            isinstance(getattr(env_spec, "args_parser", None), VerbatimArgsParser)
            if env_spec
            else False
        )

        if env_name in self.opaque_environments or is_math or is_verbatim:
            mask.add_opaque(node.pos, node.pos + node.len, "ENV")
        else:
            self._mask_transparent_environment(node, text, mask, boundaries, env_stack)

    def _visit_macro_node(
        self,
        node: LatexMacroNode,
        text: str,
        mask: OpacityMask,
        boundaries: list[int],
        env_stack: EnvironmentStack,
    ) -> None:
        mac = node.macroname
        if mac in self.environment_aliases:
            alias_spec = self.environment_aliases[mac]
            alias_type = alias_spec.get("type")
            target_env = alias_spec.get("env")

            if alias_type == "begin":
                env_stack.open_alias(mac, node.pos)
            elif alias_type == "end":
                env_stack.close_alias(
                    target_env or "",
                    node.pos + node.len,
                    self.environment_aliases,
                    mask,
                )

        elif mac in self.block_transparent_macros:
            boundaries.append(node.pos)
            if mac == "item":
                mask.add_opaque(node.pos, node.pos + node.len, "MACRO")
            elif node.nodeargd and node.nodeargd.argnlist:
                for arg in node.nodeargd.argnlist:
                    if arg:
                        self._traverse_node(arg, text, mask, boundaries, env_stack)
        elif mac in self.segment_split_macros:
            boundaries.append(node.pos)
            if node.nodeargd and node.nodeargd.argnlist:
                for arg in node.nodeargd.argnlist:
                    if arg:
                        self._traverse_node(arg, text, mask, boundaries, env_stack)
        elif mac in self.inline_transparent_macros:
            if node.nodeargd and node.nodeargd.argnlist:
                for arg in node.nodeargd.argnlist:
                    if arg:
                        self._traverse_node(arg, text, mask, boundaries, env_stack)
        elif mac in self.REF_MACROS:
            mask.add_opaque(node.pos, node.pos + node.len, "REF")
        elif mac in self.CITE_MACROS:
            mask.add_opaque(node.pos, node.pos + node.len, "CITE")
        elif mac in self.FORMAT_MACROS:
            apply_macro_policy(
                mac, node, text, mask, boundaries, env_stack, self._traverse_node
            )
        elif mac == "includegraphics":
            mask.add_opaque(node.pos, node.pos + node.len, "MACRO")
            self._punch_hole_for_altext(node, text, mask)
        else:
            mask.add_opaque(node.pos, node.pos + node.len, "MACRO")

    def _visit_group_node(
        self,
        node: LatexGroupNode,
        text: str,
        mask: OpacityMask,
        boundaries: list[int],
        env_stack: EnvironmentStack,
    ) -> None:
        open_delim = node.delimiters[0]
        close_delim = node.delimiters[1]

        if open_delim and node.pos < len(text) and text[node.pos] == open_delim:
            mask.add_opaque(node.pos, node.pos + len(open_delim), "GROUP_START")

        if node.nodelist:
            self._traverse_ast(node.nodelist, text, mask, boundaries, env_stack)
            self._mask_ast_gaps(node.nodelist, text, mask)

        if close_delim and node.pos + node.len >= len(close_delim):
            actual_close_start = node.pos + node.len - len(close_delim)
            actual_close = text[actual_close_start : node.pos + node.len]
            if actual_close == close_delim:
                mask.add_opaque(actual_close_start, node.pos + node.len, "GROUP_END")

    def _visit_chars_node(
        self, node: LatexCharsNode, text: str, mask: OpacityMask, boundaries: list[int]
    ) -> None:
        for pattern in self.protected_terms_regex:
            for match in pattern.finditer(node.chars):
                mask.add_opaque(
                    node.pos + match.start(), node.pos + match.end(), "TERM"
                )

        for match in self.LITERAL_END_CMD_RE.finditer(node.chars):
            mask.add_opaque(node.pos + match.start(), node.pos + match.end(), "MACRO")

        for match in self._boundary_regex.finditer(node.chars):
            boundaries.append(node.pos + match.start() + len(match.group()))

    def _traverse_node(
        self,
        node: Any,
        text: str,
        mask: OpacityMask,
        boundaries: list[int],
        env_stack: EnvironmentStack,
    ) -> None:
        if isinstance(node, LatexMathNode):
            self._visit_math_node(node, text, mask)
        elif isinstance(node, LatexCommentNode):
            self._visit_comment_node(node, text, mask)
        elif isinstance(node, LatexEnvironmentNode):
            self._visit_environment_node(node, text, mask, boundaries, env_stack)
        elif isinstance(node, LatexMacroNode):
            self._visit_macro_node(node, text, mask, boundaries, env_stack)
        elif isinstance(node, LatexGroupNode):
            self._visit_group_node(node, text, mask, boundaries, env_stack)
        elif isinstance(node, LatexCharsNode):
            self._visit_chars_node(node, text, mask, boundaries)

    def _punch_hole_for_altext(
        self, node: LatexMacroNode, text: str, mask: OpacityMask
    ) -> None:
        """Finds `alt={...}` in optional args and punches a hole."""
        if node.nodeargd and node.nodeargd.argnlist and len(node.nodeargd.argnlist) > 0:
            opt_arg = node.nodeargd.argnlist[0]
            if opt_arg and hasattr(opt_arg, "nodelist") and opt_arg.nodelist:
                nodelist = opt_arg.nodelist
                for i, subnode in enumerate(nodelist):
                    if (
                        isinstance(subnode, LatexCharsNode)
                        and re.search(r"alt\s*=\s*$", subnode.chars)
                        and i + 1 < len(nodelist)
                        and isinstance(nodelist[i + 1], LatexGroupNode)
                    ):
                        group_node = nodelist[i + 1]
                        mask.punch_hole(
                            group_node.pos + 1, group_node.pos + group_node.len - 1
                        )

    @staticmethod
    def _filter_boundaries_inside_opaque(
        boundaries: list[int],
        opaque_ranges: list[tuple[int, int, str, str]],
        text_len: int,
    ) -> list[int]:
        """Drop boundaries strictly inside an opaque range; keep 0 and text_len."""
        spans = [
            (start, start + length) for start, length, _rtype, _raw in opaque_ranges
        ]
        spans.sort()
        kept: list[int] = []
        for boundary in boundaries:
            if boundary == 0 or boundary == text_len:
                kept.append(boundary)
                continue
            inside = any(
                span_start < boundary < span_end for span_start, span_end in spans
            )
            if not inside:
                kept.append(boundary)
        return sorted(set(kept))

    def parse_text(self, text: str) -> list[SegmentBlock]:
        """Parses a raw LaTeX string and returns a list of translatable SegmentBlocks."""
        walker = LatexWalker(text, latex_context=self.db, tolerant_parsing=True)
        try:
            nodes, _, _ = walker.get_latex_nodes()
        except Exception as e:
            raise ValueError(f"Failed to parse LaTeX file: {e}") from e

        mask = OpacityMask()
        boundaries: list[int] = [0, len(text)]
        env_stack = EnvironmentStack()

        self._traverse_ast(nodes, text, mask, boundaries, env_stack)
        env_stack.close_unmatched_as_opaque(mask, len(text))

        opaque_ranges = mask.get_ranges(text)

        # Sort and deduplicate boundaries; never split an opaque range in half.
        boundaries = sorted(set(boundaries))
        boundaries = self._filter_boundaries_inside_opaque(
            boundaries, opaque_ranges, len(text)
        )

        segments = []
        for i in range(len(boundaries) - 1):
            start = boundaries[i]
            end = boundaries[i + 1]
            raw_text = text[start:end]
            if self.max_segment_chars and len(raw_text) > self.max_segment_chars:
                raise ConfigurationError(
                    f"Segment exceeds parser.max_segment_chars ({self.max_segment_chars})."
                )

            engine = PlaceholderEngine()
            if not raw_text.strip():
                masked_text = raw_text
            else:
                masked_text = engine.mask_ranges(
                    raw_text, opaque_ranges, offset_start=start
                )

            block = SegmentBlock(raw_text, masked_text, engine)
            segments.append(block)

        return segments

    def parse_file(
        self, filepath: str, strict_roundtrip: bool = True
    ) -> list[SegmentBlock]:
        """Reads a LaTeX file and parses it into SegmentBlocks."""
        text = read_text_file_resilient(filepath)
        segments = self.parse_text(text)
        if strict_roundtrip:
            from lilt.parser.roundtrip import (  # noqa: PLC0415
                verify_lossless_roundtrip,
            )

            verify_lossless_roundtrip(text, segments)
        return segments
