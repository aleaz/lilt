"""LaTeX document reconstruction by merging TM translations with parsed segments."""

import logging
import os
import re
from dataclasses import dataclass, field

from lilt.exceptions import BuildError
from lilt.models.segment import SegmentStatus
from lilt.models.segment_policy import SegmentPolicy
from lilt.parser.ast_parser import LatexParser
from lilt.parser.placeholder_contract import PLACEHOLDER_RE
from lilt.tm.repository import TMRepository
from lilt.validation.validators import BuildValidator

logger = logging.getLogger(__name__)

_NON_BUILDABLE_STATUSES = frozenset(
    {
        SegmentStatus.CONFLICT,
        SegmentStatus.ERROR,
        SegmentStatus.GENERATED,
        SegmentStatus.DRAFTED,
        SegmentStatus.CRITIQUED,
    }
)


@dataclass
class BuildSkip:
    """A translatable segment omitted from the build output."""

    segment_id: str
    status: str
    reason: str


@dataclass
class BuildResult:
    """Outcome of a document build."""

    output_path: str
    skipped: list[BuildSkip] = field(default_factory=list)

    @property
    def complete(self) -> bool:
        """True when every translatable segment used a buildable translation."""
        return not self.skipped


class Builder:
    """Reconstructs the translated LaTeX project by merging TM segments and the AST."""

    def __init__(
        self, tm: TMRepository, parser: LatexParser, injections: list[str] | None = None
    ):
        self.tm = tm
        self.parser = parser
        self.injections = injections or []

    def build_file(
        self,
        input_filepath: str,
        output_filepath: str,
        namespace: str,
        *,
        allow_partial: bool = False,
    ) -> BuildResult:
        """Builds a single translated LaTeX file and saves it to output_filepath."""
        logger.info(f"Building {output_filepath} from {input_filepath}")

        segments = self.parser.parse_file(input_filepath)
        tm_segments = self.tm.load_namespace(namespace)

        placeholder_pattern = PLACEHOLDER_RE
        skipped: list[BuildSkip] = []
        output_chunks = []
        for block in segments:
            if not self._block_is_translatable(block):
                output_chunks.append(block.raw_text)
                continue

            seg_id = block.id
            db_seg = tm_segments.get(seg_id)
            block_hash = getattr(block, "source_hash", None)
            use_translation = False
            final_text = block.raw_text

            if db_seg is not None:
                if (
                    db_seg.status in SegmentPolicy.BUILDABLE_STATUSES
                    and db_seg.translation
                    and block_hash is not None
                    and block_hash != db_seg.source_hash
                ):
                    raise BuildError(
                        f"Segment '{seg_id}' source changed since last sync. "
                        "Run 'lilt pipeline sync' before building."
                    )
                if (
                    db_seg.status in SegmentPolicy.BUILDABLE_STATUSES
                    and db_seg.translation
                ):
                    use_translation = True
                elif db_seg.status in _NON_BUILDABLE_STATUSES or not db_seg.translation:
                    reason = (
                        f"status={db_seg.status.value}"
                        if db_seg.status in _NON_BUILDABLE_STATUSES
                        else "missing translation"
                    )
                    skipped.append(
                        BuildSkip(
                            segment_id=seg_id,
                            status=db_seg.status.value,
                            reason=reason,
                        )
                    )
            else:
                skipped.append(
                    BuildSkip(
                        segment_id=seg_id,
                        status="missing",
                        reason="segment not in translation memory",
                    )
                )

            if use_translation and db_seg is not None:
                if not db_seg.placeholders and re.search(
                    r"<[a-z_]+ id=\"\d+\"/>", db_seg.source_text
                ):
                    raise BuildError(
                        f"Segment '{seg_id}' has no placeholder mapping in the TM. "
                        "Run 'lilt pipeline sync' to repair the Translation Memory before building."
                    )

                fresh_mapping: dict[str, str] = {}
                engine = getattr(block, "engine", None)
                if engine is not None and hasattr(engine, "mapping"):
                    fresh_mapping = dict(engine.mapping)

                BuildValidator.validate_placeholder_mapping(
                    seg_id,
                    db_seg.placeholders,
                    fresh_mapping,
                )

                final_text = db_seg.translation
                for pid, raw_latex in db_seg.placeholders.items():
                    pattern = re.compile(re.escape(pid), re.IGNORECASE)
                    if not pattern.search(final_text):
                        raise ValueError(
                            f"Missing placeholder '{pid}' in translation for segment '{seg_id}'."
                        )

                    def _restore_placeholder(
                        _: re.Match[str], r: str = raw_latex
                    ) -> str:
                        return r

                    final_text = pattern.sub(_restore_placeholder, final_text)

                remaining = placeholder_pattern.findall(final_text)
                if remaining:
                    raise ValueError(
                        f"Unresolved placeholders in translation for segment "
                        f"'{seg_id}': {remaining}"
                    )

                m_leading = re.match(r"^(\s*)", block.raw_text)
                leading_ws = m_leading.group(1) if m_leading else ""

                m_trailing = re.search(r"(\s*)$", block.raw_text)
                trailing_ws = m_trailing.group(1) if m_trailing else ""

                final_text = leading_ws + final_text.strip() + trailing_ws
                output_chunks.append(final_text)
                continue

            output_chunks.append(final_text)

        if skipped and not allow_partial:
            summary = ", ".join(
                f"{item.segment_id[:8]}({item.reason})" for item in skipped[:5]
            )
            extra = f" (+{len(skipped) - 5} more)" if len(skipped) > 5 else ""
            raise BuildError(
                f"Build blocked: {len(skipped)} translatable segment(s) lack a "
                f"buildable translation ({summary}{extra}). "
                "Re-translate or resolve conflicts, or pass --allow-partial."
            )

        if skipped:
            logger.warning(
                "Partial build: %s segment(s) fell back to source text: %s",
                len(skipped),
                ", ".join(item.segment_id[:8] for item in skipped),
            )

        final_document = "".join(output_chunks)

        if self.injections:
            # Look for \documentclass to inject packages right after it
            match = re.search(
                r"\\documentclass(?:\[[^\]]*\])?\{[^\}]+\}", final_document
            )
            if match:
                insert_pos = match.end()
                injection_str = (
                    "\n% --- LILT Auto-Injections ---\n"
                    + "\n".join(self.injections)
                    + "\n% ----------------------------\n"
                )
                final_document = (
                    final_document[:insert_pos]
                    + injection_str
                    + final_document[insert_pos:]
                )
            else:
                logger.warning("Could not find \\documentclass to inject preambles.")

        os.makedirs(os.path.dirname(output_filepath) or ".", exist_ok=True)
        with open(output_filepath, "w", encoding="utf-8") as f:
            f.write(final_document)

        logger.info(f"Built {output_filepath} successfully.")
        return BuildResult(output_path=output_filepath, skipped=skipped)

    @staticmethod
    def _block_is_translatable(block: object) -> bool:
        is_translatable = getattr(block, "is_translatable", None)
        if callable(is_translatable):
            return bool(is_translatable())
        return False
