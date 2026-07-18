"""JSONL-backed Translation Memory repository with sync and import/export."""

import csv
import json
import logging
import os
import shutil
import time
from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import UTC, datetime

from filelock import FileLock, Timeout

from lilt.exceptions import (
    InvalidTransitionError,
    NamespaceBusyError,
    TMConcurrencyError,
    TMCorruptionError,
    TMImportError,
)
from lilt.models.segment import (
    FileFormat,
    SegmentHistoryEntry,
    SegmentStatus,
    StoredSegment,
)
from lilt.models.segment_policy import SegmentPolicy
from lilt.models.segment_transition import SegmentTransitionPolicy
from lilt.validation.validators import SegmentTranslationValidator, ValidationError

logger = logging.getLogger(__name__)


@dataclass
class CorruptLineReport:
    """Details for a JSONL line that could not be parsed."""

    line_number: int
    detail: str


@dataclass
class LoadNamespaceReport:
    """Result of loading a namespace, including skipped corrupt lines."""

    segments: dict[str, StoredSegment] = field(default_factory=dict)
    ordered_segments: list[StoredSegment] = field(default_factory=list)
    corrupt_lines: list[CorruptLineReport] = field(default_factory=list)


def deduplicate_ordered_segments(segments: list[StoredSegment]) -> list[StoredSegment]:
    """Keep the latest version per segment ID, preserving first-seen ID order."""
    last_by_id: dict[str, StoredSegment] = {}
    order: list[str] = []
    for seg in segments:
        if seg.id not in last_by_id:
            order.append(seg.id)
        last_by_id[seg.id] = seg
    return [last_by_id[segment_id] for segment_id in order]


class TMRepository:
    """Manages persistence of Translation Memory to JSONL files."""

    def __init__(self, base_dir: str):
        self.base_dir = base_dir

    def _get_filepath(self, namespace: str) -> str:
        # Prevent path traversal; namespace is a flat encoded relative path
        if ".." in namespace or "/" in namespace or "\\" in namespace:
            raise ValueError(f"Invalid namespace: {namespace!r}")
        safe_name = namespace if namespace.endswith(".jsonl") else f"{namespace}.jsonl"
        return os.path.join(self.base_dir, safe_name)

    def _get_lock_path(self, namespace: str) -> str:
        filepath = self._get_filepath(namespace)
        return f"{filepath}.lock"

    def _get_session_lock_path(self, namespace: str) -> str:
        filepath = self._get_filepath(namespace)
        return f"{filepath}.session.lock"

    @contextmanager
    def namespace_session(self, namespace: str) -> Generator[None]:
        """Acquire an exclusive non-blocking session lock for mutating operations."""
        lock_path = self._get_session_lock_path(namespace)
        lock = FileLock(lock_path, timeout=0)
        try:
            lock.acquire()
        except Timeout as exc:
            raise NamespaceBusyError(namespace) from exc
        try:
            yield
        finally:
            lock.release()

    @contextmanager
    def _with_file_lock(self, namespace: str) -> Generator[None]:
        """Acquire namespace file lock with bounded retries."""
        lock_path = self._get_lock_path(namespace)
        last_exc: Timeout | None = None
        for attempt in range(3):
            try:
                with FileLock(lock_path, timeout=10):
                    yield
                return
            except Timeout as exc:
                last_exc = exc
                time.sleep(0.5 * (2**attempt))
        raise TMConcurrencyError(
            f"Could not acquire TM lock for namespace '{namespace}' after retries."
        ) from last_exc

    def _parse_jsonl_line(
        self,
        line: str,
        *,
        filepath: str,
        line_number: int,
        skip_corrupt: bool = False,
        corrupt_lines: list[CorruptLineReport] | None = None,
    ) -> StoredSegment | None:
        try:
            return StoredSegment.model_validate_json(line)
        except Exception as exc:
            if skip_corrupt:
                if corrupt_lines is not None:
                    corrupt_lines.append(
                        CorruptLineReport(line_number=line_number, detail=str(exc))
                    )
                return None
            raise TMCorruptionError(filepath, line_number, str(exc)) from exc

    def load_namespace_report(
        self, namespace: str, *, skip_corrupt: bool = False
    ) -> LoadNamespaceReport:
        """Load segments preserving order and optionally skipping corrupt lines."""
        report = LoadNamespaceReport()
        if not os.path.exists(self.base_dir):
            return report
        filepath = self._get_filepath(namespace)

        with self._with_file_lock(namespace):
            if not os.path.exists(filepath):
                return report

            with open(filepath, encoding="utf-8") as f:
                for line_number, line in enumerate(f, start=1):
                    line = line.strip()
                    if not line:
                        continue
                    seg = self._parse_jsonl_line(
                        line,
                        filepath=filepath,
                        line_number=line_number,
                        skip_corrupt=skip_corrupt,
                        corrupt_lines=report.corrupt_lines,
                    )
                    if seg is None:
                        continue
                    report.ordered_segments.append(seg)
                    report.segments[seg.id] = seg
        return report

    def list_namespaces(self) -> list[str]:
        """Returns a list of all namespaces in the base directory."""
        if not os.path.exists(self.base_dir):
            return []
        return [f[:-6] for f in os.listdir(self.base_dir) if f.endswith(".jsonl")]

    def load_namespace(
        self, namespace: str, *, skip_corrupt: bool = False
    ) -> dict[str, StoredSegment]:
        """Loads all segments from a JSONL file into a dictionary keyed by segment ID."""
        return self.load_namespace_report(namespace, skip_corrupt=skip_corrupt).segments

    def save_namespace(self, namespace: str, segments: list[StoredSegment]) -> None:
        """Saves a list of StoredSegment to a JSONL file atomically."""
        os.makedirs(self.base_dir, exist_ok=True)
        filepath = self._get_filepath(namespace)
        tmp_filepath = filepath + ".tmp"

        with self._with_file_lock(namespace):
            with open(tmp_filepath, "w", encoding="utf-8") as f:
                f.writelines(
                    seg.model_dump_json(by_alias=True) + "\n" for seg in segments
                )
                f.flush()
                os.fsync(f.fileno())

            os.replace(tmp_filepath, filepath)

    def append_segment(self, namespace: str, segment: StoredSegment) -> None:
        """Appends a single segment update to the JSONL file for O(1) persistence."""
        os.makedirs(self.base_dir, exist_ok=True)
        filepath = self._get_filepath(namespace)

        with (
            self._with_file_lock(namespace),
            open(filepath, "a", encoding="utf-8") as f,
        ):
            f.write(segment.model_dump_json(by_alias=True) + "\n")
            f.flush()
            os.fsync(f.fileno())

    def reset_namespace(
        self, namespace: str, dry_run: bool = False, *, force: bool = False
    ) -> list[StoredSegment]:
        """Resets translated segments back to GENERATED state. Returns affected segments."""
        segments = self.load_namespace(namespace)
        machine_resettable = {
            SegmentStatus.REFINED,
            SegmentStatus.CONFLICT,
            SegmentStatus.ERROR,
            SegmentStatus.DRAFTED,
            SegmentStatus.CRITIQUED,
        }
        human_resettable = {SegmentStatus.REVIEWED, SegmentStatus.APPROVED}
        affected = []
        for seg in segments.values():
            resettable = seg.status in machine_resettable
            if force and seg.status in human_resettable:
                resettable = True
            if not resettable:
                continue
            affected.append(seg)
            if not dry_run:
                seg.reset_to_generated()

        if not dry_run and affected:
            self.save_namespace(namespace, list(segments.values()))

        return affected

    def prune_namespace(
        self, namespace: str, dry_run: bool = False
    ) -> list[StoredSegment]:
        """Removes DEPRECATED segments from the TM permanently. Returns removed segments."""
        segments = self.load_namespace(namespace)
        active_segments = []
        removed = []

        for seg in segments.values():
            if seg.status == SegmentStatus.DEPRECATED:
                removed.append(seg)
            else:
                active_segments.append(seg)

        if not dry_run and removed:
            self.save_namespace(namespace, active_segments)

        return removed

    def repair_namespace(
        self, namespace: str, *, dry_run: bool = False
    ) -> list[CorruptLineReport]:
        """Compact a namespace after skipping corrupt JSONL lines.

        Backs up the original file before rewriting unless ``dry_run`` is True.
        """
        report = self.load_namespace_report(namespace, skip_corrupt=True)
        if not report.corrupt_lines and not report.ordered_segments:
            return report.corrupt_lines

        compacted = deduplicate_ordered_segments(report.ordered_segments)
        if dry_run:
            return report.corrupt_lines

        filepath = self._get_filepath(namespace)
        if os.path.exists(filepath):
            timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S")
            backup_path = f"{filepath}.corrupt-{timestamp}"
            shutil.move(filepath, backup_path)

        self.save_namespace(namespace, compacted)
        return report.corrupt_lines

    def export_data(self, namespace: str, output_path: str, format: FileFormat) -> int:
        """Exports the active TM to a file of the specified format (CSV or JSON)."""
        segments = self.load_namespace(namespace)
        active_segments = [
            seg for seg in segments.values() if seg.status != SegmentStatus.DEPRECATED
        ]

        if format == FileFormat.CSV:
            with open(output_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["ID", "Status", "Source", "Translation"])
                for seg in active_segments:
                    writer.writerow(
                        [seg.id, seg.status.value, seg.source_text, seg.translation]
                    )
            return len(active_segments)

        elif format == FileFormat.JSON:
            data = []
            for seg in active_segments:
                data.append(
                    {
                        "id": seg.id,
                        "status": seg.status.value,
                        "source": seg.source_text,
                        "translation": seg.translation,
                    }
                )
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return len(active_segments)

        else:
            raise ValueError(f"Unsupported export format: {format}")

    def import_data(
        self, namespace: str, input_path: str, format: FileFormat
    ) -> tuple[int, int]:
        """Imports translations from a CSV or JSON file. Returns (updated_count, skipped_count)."""
        segments = self.load_namespace(namespace)

        if format == FileFormat.CSV:
            updated_count, skipped_count = self._import_csv_data(segments, input_path)
        elif format == FileFormat.JSON:
            updated_count, skipped_count = self._import_json_data(segments, input_path)
        else:
            raise ValueError(f"Unsupported import format: {format}")

        if updated_count > 0:
            self.save_namespace(namespace, list(segments.values()))

        return updated_count, skipped_count

    def _apply_import_row(
        self,
        seg_id: str | None,
        new_translation: str,
        new_status: str | None,
        segments: dict[str, StoredSegment],
    ) -> bool:
        """Applies a single row of imported data to the segments dictionary. Returns True if updated."""
        if not seg_id or seg_id not in segments or not new_translation:
            return False

        seg = segments[seg_id]
        if SegmentPolicy.is_immutable(seg):
            return False

        changed = False

        if seg.translation != new_translation:
            try:
                SegmentTransitionPolicy.validate(seg.status, SegmentStatus.REVIEWED)
            except InvalidTransitionError:
                return False
            try:
                SegmentTranslationValidator.validate(seg.source_text, new_translation)
            except ValidationError:
                return False
            if seg.translation:
                seg.history.append(
                    SegmentHistoryEntry(
                        translation=seg.translation,
                        status=seg.status,
                        timestamp=datetime.now(UTC),
                    )
                )
            seg.translation = new_translation
            seg.status = SegmentStatus.REVIEWED
            changed = True
        elif new_status:
            try:
                status_enum = SegmentStatus(new_status.lower())
                if seg.status != status_enum:
                    SegmentTransitionPolicy.validate(seg.status, status_enum)
                    if (
                        seg.translation
                        and status_enum in SegmentPolicy.BUILDABLE_STATUSES
                    ):
                        try:
                            SegmentTranslationValidator.validate(
                                seg.source_text, seg.translation
                            )
                        except ValidationError:
                            return False
                    seg.status = status_enum
                    changed = True
            except ValueError:
                logger.warning(
                    f"Ignored invalid status '{new_status}' for segment {seg_id} during import."
                )
            except InvalidTransitionError:
                return False

        return changed

    def _import_csv_data(
        self, segments: dict[str, StoredSegment], input_path: str
    ) -> tuple[int, int]:
        updated_count = 0
        skipped_count = 0
        with open(input_path, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                seg_id = row.get("id") or row.get("ID")
                new_translation = (
                    row.get("translation") or row.get("Translation") or ""
                ).strip()
                new_status = row.get("status") or row.get("Status")

                if self._apply_import_row(
                    seg_id, new_translation, new_status, segments
                ):
                    updated_count += 1
                else:
                    skipped_count += 1
        return updated_count, skipped_count

    def _import_json_data(
        self, segments: dict[str, StoredSegment], input_path: str
    ) -> tuple[int, int]:
        updated_count = 0
        skipped_count = 0
        try:
            with open(input_path, encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError as exc:
            raise TMImportError(f"Invalid JSON in import file: {exc}") from exc

        if not isinstance(data, list):
            raise ValueError("JSON import format must be a list of segment objects.")

        for row in data:
            seg_id = row.get("id") or row.get("ID")
            new_translation = (
                row.get("translation") or row.get("Translation") or ""
            ).strip()
            new_status = row.get("status") or row.get("Status")

            if self._apply_import_row(seg_id, new_translation, new_status, segments):
                updated_count += 1
            else:
                skipped_count += 1
        return updated_count, skipped_count
