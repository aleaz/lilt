"""Segment status, storage models, and Translation Memory persistence schema."""

from datetime import UTC, datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class SegmentStatus(str, Enum):
    """Enumeration of possible statuses for a translation segment."""

    GENERATED = "generated"
    DRAFTED = "drafted"
    CRITIQUED = "critiqued"
    REFINED = "refined"
    REVIEWED = "reviewed"
    APPROVED = "approved"
    LOCKED = "locked"
    CONFLICT = "conflict"
    ERROR = "error"
    DEPRECATED = "deprecated"


IMMUTABLE_STATUSES = frozenset({SegmentStatus.LOCKED, SegmentStatus.DEPRECATED})


class FileFormat(str, Enum):
    """Enumeration of supported export file formats."""

    CSV = "csv"
    JSON = "json"


class SegmentBase(BaseModel):
    """Common fields shared across Segment models."""

    model_config = ConfigDict(populate_by_name=True)

    source_hash: str = Field(
        ..., description="SHA-256 hash of the normalized source text"
    )
    source_text: str = Field(
        ..., description="The original masked text from the parser"
    )
    status: SegmentStatus = Field(default=SegmentStatus.GENERATED)


class SegmentHistoryEntry(BaseModel):
    """Historical record of a segment translation."""

    translation: str
    status: SegmentStatus
    timestamp: datetime


class StageArtifact(BaseModel):
    """Metadata and content for an intermediate workflow artifact."""

    content: str
    model: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ReflectionMeta(BaseModel):
    """Metadata regarding the reflection/quality process for this translation."""

    used: bool = False
    draft_accepted: bool = False
    critique_feedback: str | None = None


class ErrorMeta(BaseModel):
    """Metadata detailing an infrastructure or system error during generation."""

    error_type: str = Field(..., description="The class name of the exception")
    message: str = Field(..., description="The detailed error message")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="When the error occurred",
    )


class StoredSegment(SegmentBase):
    """Complete segment record stored in the Translation Memory (JSONL)."""

    id: str = Field(..., description="Stable segment identifier")
    translation: str = Field(default="", description="The active translated text")
    draft: StageArtifact | None = Field(
        default=None, description="The drafted translation artifact"
    )
    critique: StageArtifact | None = Field(
        default=None, description="The critique analysis artifact"
    )
    refined: StageArtifact | None = Field(
        default=None, description="The refined translation artifact"
    )
    history: list[SegmentHistoryEntry] = Field(default_factory=list)
    doc_type: str = "segment"
    reflection_meta: ReflectionMeta | None = Field(
        default=None, description="Metadata from the LLM Reflection process"
    )
    error_meta: ErrorMeta | None = Field(
        default=None, description="Detailed error information if status is ERROR"
    )
    placeholders: dict[str, str] = Field(
        default_factory=dict,
        description="Persisted mapping of placeholder tags to original LaTeX commands",
    )

    def archive_current_translation(self) -> None:
        """Append the current translation to history before it is overwritten."""
        if self.translation:
            self.history.append(
                SegmentHistoryEntry(
                    translation=self.translation,
                    status=self.status,
                    timestamp=datetime.now(UTC),
                )
            )

    def clear_machine_artifacts(self) -> None:
        """Clear translation text and LLM workflow artifacts without archiving."""
        self.translation = ""
        self.draft = None
        self.critique = None
        self.refined = None
        self.reflection_meta = None

    def reset_to_generated(self) -> None:
        """Archive the current translation and reset the segment to GENERATED."""
        self.archive_current_translation()
        self.clear_machine_artifacts()
        self.status = SegmentStatus.GENERATED
        self.error_meta = None

    def apply_successful_translation(self, text: str) -> None:
        """Record a successful translation and mark the segment as refined."""
        if self.translation and self.translation != text:
            self.archive_current_translation()
        self.translation = text
        self.status = SegmentStatus.REFINED
        self.error_meta = None
        self.draft = None
        self.critique = None
        self.refined = None

    def mark_validation_conflict(
        self,
        text: str,
        *,
        stage: str | None = None,
        refine_model: str | None = None,
    ) -> None:
        """Mark a segment as conflict after validation failure."""
        self.status = SegmentStatus.CONFLICT
        self.error_meta = None
        if text:
            self.translation = text
            if stage == "refine" and refine_model:
                self.refined = StageArtifact(content=text, model=refine_model)
        if self.reflection_meta is not None:
            self.reflection_meta.draft_accepted = False

    def mark_infrastructure_error(self, error: Exception) -> None:
        """Mark a segment as error after an infrastructure or pipeline failure."""
        self.status = SegmentStatus.ERROR
        self.error_meta = ErrorMeta(
            error_type=error.__class__.__name__,
            message=str(error),
        )
