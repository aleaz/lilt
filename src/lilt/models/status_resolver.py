"""Resolve user-facing status aliases to SegmentStatus enum values."""

from lilt.exceptions import InvalidStatusError
from lilt.models.segment import SegmentStatus

_STATUS_ALIASES: dict[str, SegmentStatus] = {
    "untranslated": SegmentStatus.GENERATED,
    "pending": SegmentStatus.GENERATED,
    "machine_done": SegmentStatus.REFINED,
}


class StatusResolver:
    """Maps CLI and config status strings to canonical SegmentStatus values."""

    @staticmethod
    def resolve(value: str) -> SegmentStatus:
        """Resolve a status string or alias to a SegmentStatus."""
        normalized = value.strip().lower()
        if normalized in _STATUS_ALIASES:
            return _STATUS_ALIASES[normalized]
        try:
            return SegmentStatus(normalized)
        except ValueError as exc:
            valid = ", ".join(s.value for s in SegmentStatus)
            aliases = ", ".join(_STATUS_ALIASES.keys())
            raise InvalidStatusError(value, f"{valid} (aliases: {aliases})") from exc

    @staticmethod
    def matches(segment_status: SegmentStatus, filter_value: str) -> bool:
        """Return True if segment_status matches the filter (alias or enum value)."""
        return segment_status == StatusResolver.resolve(filter_value)

    @staticmethod
    def help_text() -> str:
        """Generate CLI help listing enum values and aliases."""
        enum_values = ", ".join(s.value for s in SegmentStatus)
        aliases = ", ".join(f"{k}={v.value}" for k, v in _STATUS_ALIASES.items())
        return f"{enum_values} (aliases: {aliases})"
