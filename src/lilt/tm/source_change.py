"""Apply source-text changes to existing TM segments during sync."""

from datetime import UTC, datetime

from lilt.models.segment import SegmentHistoryEntry, SegmentStatus, StoredSegment
from lilt.models.segment_policy import SegmentPolicy
from lilt.validation.validators import SegmentTranslationValidator, ValidationError


class SourceChangePolicy:
    """Applies source-text change rules to existing segments during TM sync."""

    @staticmethod
    def apply(
        existing: StoredSegment,
        new_masked_text: str,
        new_hash: str,
        new_placeholders: dict[str, str],
    ) -> bool:
        """Update segment fields when parsed source text changes.

        Returns True if the segment was newly marked as CONFLICT.
        """
        if existing.status == SegmentStatus.DEPRECATED:
            prior_source = existing.source_text
            existing.source_hash = new_hash
            existing.placeholders = new_placeholders
            existing.source_text = new_masked_text
            if (
                prior_source == new_masked_text
                and existing.history
                and existing.translation
            ):
                try:
                    SegmentTranslationValidator.validate(
                        new_masked_text, existing.translation
                    )
                    existing.status = existing.history[-1].status
                except ValidationError:
                    existing.clear_machine_artifacts()
                    existing.status = SegmentStatus.GENERATED
            else:
                existing.clear_machine_artifacts()
                existing.status = SegmentStatus.GENERATED
            return False

        existing.source_hash = new_hash
        existing.placeholders = new_placeholders

        if existing.source_text == new_masked_text:
            return False

        if (
            existing.translation
            and existing.status in SegmentPolicy.HUMAN_PROTECTED_STATUSES
        ):
            if existing.status != SegmentStatus.CONFLICT:
                existing.history.append(
                    SegmentHistoryEntry(
                        translation=existing.translation,
                        status=existing.status,
                        timestamp=datetime.now(UTC),
                    )
                )
            existing.source_text = new_masked_text
            existing.status = SegmentStatus.CONFLICT
            return True

        if existing.status in SegmentPolicy.LLM_ARTIFACT_STATUSES:
            existing.source_text = new_masked_text
            existing.status = SegmentStatus.GENERATED
            existing.clear_machine_artifacts()
            return False

        if existing.status == SegmentStatus.CONFLICT:
            existing.source_text = new_masked_text
            return False

        if existing.status in (SegmentStatus.GENERATED, SegmentStatus.ERROR):
            existing.source_text = new_masked_text
            existing.clear_machine_artifacts()
            existing.status = SegmentStatus.GENERATED
            return False

        existing.source_text = new_masked_text
        return False
