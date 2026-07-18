"""Synchronize parsed LaTeX blocks with Translation Memory state."""

import logging
from datetime import UTC, datetime

from lilt.models.segment import SegmentHistoryEntry, SegmentStatus, StoredSegment
from lilt.models.sync_result import SyncResult
from lilt.parser.ast_parser import LatexParser, SegmentBlock
from lilt.tm.identity_resolver import IdentityResolver
from lilt.tm.repository import TMRepository, deduplicate_ordered_segments
from lilt.tm.source_change import SourceChangePolicy

logger = logging.getLogger(__name__)


def sync_parsed_blocks(
    namespace: str,
    blocks: list[SegmentBlock],
    tm: TMRepository,
    similarity_threshold: float = 0.85,
) -> SyncResult:
    """Synchronizes AST parser blocks with the TM."""
    # Single load under one file lock; session lock must be held by the caller.
    load_report = tm.load_namespace_report(namespace)
    existing_segments = load_report.segments
    ordered_existing = deduplicate_ordered_segments(load_report.ordered_segments)
    active_segments: list[StoredSegment] = []
    new_conflicts = 0
    new_segments = 0
    updated_segments = 0

    translatable_blocks = [b for b in blocks if b.is_translatable()]
    resolver = IdentityResolver(similarity_threshold)
    carryovers = resolver.resolve_carryovers(ordered_existing, translatable_blocks)

    for block in translatable_blocks:
        seg_id = block.id

        if seg_id in existing_segments:
            existing = existing_segments[seg_id]
            before_text = existing.source_text
            before_status = existing.status
            if SourceChangePolicy.apply(
                existing,
                block.masked_text,
                block.source_hash,
                dict(block.engine.mapping),
            ):
                new_conflicts += 1
            if before_text != existing.source_text or before_status != existing.status:
                updated_segments += 1
            active_segments.append(existing)
        else:
            new_seg = StoredSegment(
                id=seg_id,
                source_hash=block.source_hash,
                source_text=block.masked_text,
                status=SegmentStatus.GENERATED,
                translation="",
                placeholders=dict(block.engine.mapping),
            )
            if seg_id in carryovers:
                IdentityResolver.apply_carryover(new_seg, carryovers[seg_id])
                if new_seg.status == SegmentStatus.CONFLICT:
                    new_conflicts += 1
            active_segments.append(new_seg)
            new_segments += 1

    active_ids = {s.id for s in active_segments}
    deprecated_marked = 0
    for seg_id, seg in existing_segments.items():
        if seg_id not in active_ids:
            if seg.status != SegmentStatus.DEPRECATED:
                deprecated_marked += 1
                if seg.translation and seg.status not in (
                    SegmentStatus.GENERATED,
                    SegmentStatus.DEPRECATED,
                ):
                    seg.history.append(
                        SegmentHistoryEntry(
                            translation=seg.translation,
                            status=seg.status,
                            timestamp=datetime.now(UTC),
                        )
                    )
            seg.status = SegmentStatus.DEPRECATED
            active_segments.append(seg)

    tm.save_namespace(namespace, active_segments)
    return SyncResult(
        namespace=namespace,
        active_segments=active_segments,
        new_segments=new_segments,
        updated_segments=updated_segments,
        new_conflicts=new_conflicts,
        deprecated_marked=deprecated_marked,
    )


def sync_file(
    input_filepath: str,
    tm: TMRepository,
    namespace: str,
    parser: LatexParser,
    similarity_threshold: float = 0.85,
) -> SyncResult:
    """Synchronizes a LaTeX file's AST structure with the translation memory."""
    logger.info(f"Syncing {input_filepath} to TM namespace {namespace}")
    segments = parser.parse_file(input_filepath)
    logger.info(f"Parsed {len(segments)} blocks from file.")

    result = sync_parsed_blocks(
        namespace, segments, tm, similarity_threshold=similarity_threshold
    )
    logger.info(
        f"Sync complete. {result.total_active} active segments. "
        f"New: {result.new_segments}, updated: {result.updated_segments}, "
        f"conflicts: {result.new_conflicts}, deprecated: {result.deprecated_marked}."
    )
    return result
