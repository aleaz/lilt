"""Domain models for segments, critique results, and translation workflow state."""

from .critique import CritiqueResult, TranslationIssue
from .segment import (
    ErrorMeta,
    FileFormat,
    ReflectionMeta,
    SegmentBase,
    SegmentHistoryEntry,
    SegmentStatus,
    StageArtifact,
    StoredSegment,
)
from .segment_policy import SegmentPolicy
from .status_resolver import StatusResolver
from .sync_result import SyncResult
from .translation_mode import TranslationMode
from .translation_stage import TranslationStage

__all__ = [
    "CritiqueResult",
    "ErrorMeta",
    "FileFormat",
    "ReflectionMeta",
    "SegmentPolicy",
    "SegmentStatus",
    "SegmentBase",
    "SegmentHistoryEntry",
    "StageArtifact",
    "StatusResolver",
    "StoredSegment",
    "SyncResult",
    "TranslationIssue",
    "TranslationMode",
    "TranslationStage",
]
