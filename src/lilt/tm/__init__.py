"""Translation Memory persistence, identity resolution, and checkpoints."""

from .checkpoint import TranslationCheckpoint
from .identity_resolver import IdentityCarryOver, IdentityResolver
from .repository import TMRepository, deduplicate_ordered_segments
from .segment_lookup import match_segments_by_prefix, resolve_unique_segment
from .source_change import SourceChangePolicy

__all__ = [
    "IdentityCarryOver",
    "IdentityResolver",
    "SourceChangePolicy",
    "TMRepository",
    "TranslationCheckpoint",
    "deduplicate_ordered_segments",
    "match_segments_by_prefix",
    "resolve_unique_segment",
]
