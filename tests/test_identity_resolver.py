"""Tests for sequence-based segment identity resolution."""

from unittest.mock import MagicMock

from lilt.models.segment import SegmentStatus, StoredSegment
from lilt.tm.identity_resolver import IdentityResolver


def _block(block_id: str, masked_text: str, source_hash: str):
    block = MagicMock()
    block.id = block_id
    block.masked_text = masked_text
    block.source_hash = source_hash
    block.is_translatable.return_value = True
    block.engine.mapping = {}
    return block


def test_identity_carryover_reviewed_minor_edit():
    old_seg = StoredSegment(
        id="old-id-aaaa",
        source_hash="hash-old",
        source_text="The quick brown fox jumps.",
        status=SegmentStatus.REVIEWED,
        translation="El zorro marrón rápido salta.",
    )
    new_block = _block(
        "new-id-bbbb",
        "The quick brown fox jumps quickly.",
        "hash-new",
    )

    resolver = IdentityResolver(similarity_threshold=0.7)
    carryovers = resolver.resolve_carryovers([old_seg], [new_block])
    assert "new-id-bbbb" in carryovers

    new_seg = StoredSegment(
        id=new_block.id,
        source_hash=new_block.source_hash,
        source_text=new_block.masked_text,
        status=SegmentStatus.GENERATED,
    )
    IdentityResolver.apply_carryover(new_seg, carryovers[new_block.id])
    assert new_seg.status == SegmentStatus.CONFLICT
    assert new_seg.translation == "El zorro marrón rápido salta."


def test_identity_no_carryover_when_dissimilar():
    old_seg = StoredSegment(
        id="old-id",
        source_hash="hash-old",
        source_text="Completely different paragraph A.",
        status=SegmentStatus.REVIEWED,
        translation="Traduccion A.",
    )
    new_block = _block(
        "new-id",
        "Unrelated paragraph B with other meaning.",
        "hash-new",
    )

    resolver = IdentityResolver(similarity_threshold=0.85)
    carryovers = resolver.resolve_carryovers([old_seg], [new_block])
    assert carryovers == {}
