"""Sequence-based segment identity resolution for upstream source changes."""

from __future__ import annotations

from dataclasses import dataclass
from difflib import SequenceMatcher

from lilt.models.segment import SegmentStatus, StoredSegment
from lilt.models.segment_policy import SegmentPolicy
from lilt.parser.ast_parser import SegmentBlock


@dataclass
class IdentityCarryOver:
    """Maps a new block to a prior segment whose translation should be carried over."""

    new_block_id: str
    source_segment: StoredSegment
    similarity: float


class IdentityResolver:
    """Matches lightly edited paragraphs to prior segments using sequence alignment."""

    def __init__(self, similarity_threshold: float = 0.85) -> None:
        self.similarity_threshold = similarity_threshold

    def _best_carryover(
        self,
        new_block: SegmentBlock,
        candidates: list[StoredSegment],
        assigned_old_ids: set[str],
    ) -> IdentityCarryOver | None:
        best: IdentityCarryOver | None = None
        for old_seg in candidates:
            if old_seg.id in assigned_old_ids or not old_seg.translation:
                continue
            ratio = SequenceMatcher(
                None, old_seg.source_text, new_block.masked_text
            ).ratio()
            if ratio >= self.similarity_threshold and (
                best is None or ratio > best.similarity
            ):
                best = IdentityCarryOver(
                    new_block_id=new_block.id,
                    source_segment=old_seg,
                    similarity=ratio,
                )
        return best

    def resolve_carryovers(
        self,
        ordered_existing: list[StoredSegment],
        new_blocks: list[SegmentBlock],
    ) -> dict[str, IdentityCarryOver]:
        """Match lightly edited paragraphs to prior segments.

        Returns a mapping from new block id -> prior segment to carry translation from.
        """
        active_existing = [
            s for s in ordered_existing if s.status != SegmentStatus.DEPRECATED
        ]
        deprecated_existing = [
            s for s in ordered_existing if s.status == SegmentStatus.DEPRECATED
        ]
        old_hashes = [s.source_hash for s in active_existing]
        new_hashes = [b.source_hash for b in new_blocks]

        matcher = SequenceMatcher(None, old_hashes, new_hashes)
        carryovers: dict[str, IdentityCarryOver] = {}
        assigned_old_ids: set[str] = set()

        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag not in ("replace", "insert"):
                continue
            old_slice = active_existing[i1:i2]
            new_slice = new_blocks[j1:j2]

            if tag == "replace":
                for new_block in new_slice:
                    if new_block.id in carryovers:
                        continue
                    carryover = self._best_carryover(
                        new_block, old_slice, assigned_old_ids
                    )
                    if carryover is not None:
                        carryovers[new_block.id] = carryover
                        assigned_old_ids.add(carryover.source_segment.id)
            else:
                for new_block in new_slice:
                    if new_block.id in carryovers:
                        continue
                    carryover = self._best_carryover(
                        new_block, deprecated_existing, assigned_old_ids
                    )
                    if carryover is not None:
                        carryovers[new_block.id] = carryover
                        assigned_old_ids.add(carryover.source_segment.id)

        return carryovers

    @staticmethod
    def apply_carryover(new_seg: StoredSegment, carryover: IdentityCarryOver) -> None:
        """Copy translation state from a matched prior segment onto a new segment."""
        source = carryover.source_segment
        new_seg.translation = source.translation
        new_seg.draft = source.draft
        new_seg.critique = source.critique
        new_seg.refined = source.refined
        new_seg.reflection_meta = source.reflection_meta
        new_seg.history = list(source.history)

        if source.status in SegmentPolicy.HUMAN_PROTECTED_STATUSES:
            new_seg.status = SegmentStatus.CONFLICT
        elif source.status in SegmentPolicy.LLM_ARTIFACT_STATUSES:
            new_seg.status = SegmentStatus.GENERATED
            new_seg.translation = ""
            new_seg.draft = None
            new_seg.critique = None
            new_seg.refined = None
            new_seg.reflection_meta = None
        else:
            new_seg.status = source.status
