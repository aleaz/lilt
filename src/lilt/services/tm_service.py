"""Translation Memory CRUD, search, import/export, and statistics."""

import logging
import os

from lilt.exceptions import (
    TMCorruptionError,
    TMImportError,
)
from lilt.models.segment import FileFormat, SegmentStatus, StoredSegment
from lilt.models.segment_transition import SegmentTransitionPolicy
from lilt.models.status_resolver import StatusResolver
from lilt.services.workspace_context import WorkspaceContext
from lilt.telemetry.reflection_cost import estimate_reflection_tokens
from lilt.tm.repository import CorruptLineReport
from lilt.tm.segment_lookup import resolve_unique_segment
from lilt.utils.token_utils import count_tokens

logger = logging.getLogger(__name__)


class TMService:
    """Provides high-level operations to manage the Translation Memory (TM)."""

    def __init__(
        self,
        workspace_dir: str,
        workspace_ctx: WorkspaceContext | None = None,
    ):
        self.ctx = workspace_ctx or WorkspaceContext.from_workspace(workspace_dir)
        self.workspace_dir = self.ctx.workspace_dir
        self.tm_dir = self.ctx.tm_dir
        self.repo = self.ctx.repo

    def _get_namespace_segments(self, namespace: str) -> dict[str, StoredSegment]:
        self.ctx.preconditions.require_namespace(namespace)
        return self.repo.load_namespace(namespace)

    def search_segments(
        self, query: str, source: bool = False, namespace: str | None = None
    ) -> tuple[list[tuple[str, StoredSegment]], list[str]]:
        """Search the TM for a specific text query across namespaces.

        Returns:
            Tuple of (matches, namespaces_skipped_due_to_corruption).
        """
        if not os.path.isdir(self.tm_dir):
            return [], []

        namespaces_to_search = (
            [namespace]
            if namespace
            else [f[:-6] for f in os.listdir(self.tm_dir) if f.endswith(".jsonl")]
        )

        if not namespaces_to_search:
            return [], []

        results: list[tuple[str, StoredSegment]] = []
        corrupt_namespaces: list[str] = []
        query_lower = query.lower()

        for ns in namespaces_to_search:
            try:
                segments = self.repo.load_namespace(ns)
                for seg in segments.values():
                    target_text = seg.source_text if source else (seg.translation or "")
                    if query_lower in target_text.lower():
                        results.append((ns, seg))
            except TMCorruptionError:
                corrupt_namespaces.append(ns)
                continue

        return results, corrupt_namespaces

    def list_segments(
        self,
        namespace: str,
        status: str | None = None,
        search: str | None = None,
    ) -> list[StoredSegment]:
        """List and filter segments within a specific namespace."""
        segments = self._get_namespace_segments(namespace)
        results = []
        for seg in segments.values():
            if status and not StatusResolver.matches(seg.status, status):
                continue
            if search:
                translation = seg.translation or ""
                if (
                    search.lower() not in seg.source_text.lower()
                    and search.lower() not in translation.lower()
                ):
                    continue
            results.append(seg)
        return results

    def update_segment_status(
        self,
        namespace: str,
        segment_id: str,
        new_status: str,
        *,
        force: bool = False,
    ) -> tuple[StoredSegment, str]:
        """Update the translation status of a specific segment."""
        with self.repo.namespace_session(namespace):
            segments = self._get_namespace_segments(namespace)
            seg = resolve_unique_segment(segments, segment_id, namespace)

            status_enum = StatusResolver.resolve(new_status)
            SegmentTransitionPolicy.validate(seg.status, status_enum, force=force)

            old_status = seg.status.value
            if status_enum == SegmentStatus.GENERATED:
                seg.reset_to_generated()
            else:
                seg.status = status_enum
            self.repo.save_namespace(namespace, list(segments.values()))

            return seg, old_status

    def get_stats(self, namespace: str) -> dict[str, int]:
        """Generate translation statistics and progress metrics for a namespace."""
        segments = self._get_namespace_segments(namespace)
        stats = {status.value: 0 for status in SegmentStatus}
        stats["total"] = len(segments)

        reflection_used = 0
        draft_accepted = 0
        reflection_refined = 0
        tokens_total = 0
        tokens_pending = 0

        # Initialize token trackers by status
        for status in SegmentStatus:
            stats[f"tokens_{status.value}"] = 0

        for seg in segments.values():
            stats[seg.status.value] += 1
            if seg.reflection_meta and seg.reflection_meta.used:
                reflection_used += 1
                if seg.reflection_meta.draft_accepted:
                    draft_accepted += 1
                else:
                    reflection_refined += 1

            try:
                tokens = count_tokens(seg.source_text)
                tokens_total += tokens
                stats[f"tokens_{seg.status.value}"] += tokens
                if seg.status == SegmentStatus.GENERATED:
                    tokens_pending += tokens
            except Exception:
                pass

        stats["reflection_used"] = reflection_used
        stats["draft_accepted"] = draft_accepted
        stats["reflection_refined"] = reflection_refined
        stats["tokens_total"] = tokens_total
        stats["tokens_pending"] = tokens_pending
        stats["tokens_reflection_estimate"] = self._estimate_reflection_tokens(
            list(segments.values())
        )
        return stats

    def _estimate_reflection_tokens(self, segments: list[StoredSegment]) -> int:
        try:
            config = self.ctx.preconditions.load_config().model_dump()
        except Exception:
            config = {}
        return estimate_reflection_tokens(segments, config)

    def get_all_stats(self) -> tuple[dict[str, int], list[str]]:
        """Generate consolidated translation statistics across all namespaces.

        Returns:
            Tuple of (aggregated stats, namespaces skipped due to corruption).
        """
        namespaces = self.repo.list_namespaces()
        total_stats = {status.value: 0 for status in SegmentStatus}
        total_stats["total"] = 0
        total_stats["reflection_used"] = 0
        total_stats["draft_accepted"] = 0
        total_stats["reflection_refined"] = 0
        total_stats["tokens_total"] = 0
        total_stats["tokens_pending"] = 0
        corrupt_namespaces: list[str] = []

        for ns in namespaces:
            try:
                ns_stats = self.get_stats(ns)
            except TMCorruptionError:
                corrupt_namespaces.append(ns)
                logger.warning(
                    "Skipping corrupt namespace '%s' in stats; "
                    "run 'lilt tm admin repair %s'.",
                    ns,
                    ns,
                )
                continue
            for k, v in ns_stats.items():
                if k not in total_stats:
                    total_stats[k] = 0
                total_stats[k] += v

        return total_stats, corrupt_namespaces

    def show_segment(self, namespace: str, segment_id: str) -> StoredSegment:
        """Fetch the full details of a segment by its ID prefix."""
        segments = self._get_namespace_segments(namespace)
        return resolve_unique_segment(segments, segment_id, namespace)

    def diff_segment(
        self, namespace: str, segment_id: str, compare_source: bool = False
    ) -> tuple[str, str]:
        """Fetch the strings to compare for a diff.

        Returns:
            Tuple[str, str]: (old_text, new_text)
        """
        seg = self.show_segment(namespace, segment_id)

        if compare_source:
            return seg.source_text, seg.translation

        old_text = ""
        if seg.history:
            old_text = seg.history[-1].translation

        return old_text, seg.translation

    def export_tm(self, namespace: str, filepath: str, fmt: str | None = None) -> int:
        """Export the TM namespace to an external file (CSV/JSON)."""
        self._get_namespace_segments(namespace)

        format_enum = FileFormat.CSV
        if fmt:
            format_enum = FileFormat(fmt.lower())
        elif filepath.endswith(".json"):
            format_enum = FileFormat.JSON

        return self.repo.export_data(namespace, filepath, format_enum)

    def import_tm(
        self, namespace: str, filepath: str, fmt: str | None = None
    ) -> tuple[int, int]:
        """Import translations from an external file (CSV/JSON) into the TM."""
        self._get_namespace_segments(namespace)

        format_enum = FileFormat.CSV
        if fmt:
            format_enum = FileFormat(fmt.lower())
        elif filepath.endswith(".json"):
            format_enum = FileFormat.JSON

        if not os.path.exists(filepath):
            raise TMImportError(f"File '{filepath}' not found.")

        with self.repo.namespace_session(namespace):
            updated, skipped = self.repo.import_data(namespace, filepath, format_enum)
        return updated + skipped, updated

    def prune(self, namespace: str) -> int:
        """Remove all DEPRECATED segments from the namespace permanently."""
        self._get_namespace_segments(namespace)
        with self.repo.namespace_session(namespace):
            removed = self.repo.prune_namespace(namespace, dry_run=False)
        return len(removed)

    def reset(self, namespace: str, *, force: bool = False) -> int:
        """Reset translated segments in the namespace back to GENERATED state."""
        self._get_namespace_segments(namespace)
        with self.repo.namespace_session(namespace):
            affected = self.repo.reset_namespace(namespace, dry_run=False, force=force)
        return len(affected)

    def repair(
        self, namespace: str, *, dry_run: bool = False
    ) -> list[CorruptLineReport]:
        """Repair a namespace by skipping corrupt JSONL lines and compacting.

        Uses file-existence only (not a strict load) so corrupt namespaces remain
        repairable via ``lilt tm admin repair``.
        """
        self.ctx.preconditions.require_namespace_file_exists(namespace)
        with self.repo.namespace_session(namespace):
            return self.repo.repair_namespace(namespace, dry_run=dry_run)

    def list_namespaces(self) -> list[str]:
        """List all translation memory namespaces."""
        return self.repo.list_namespaces()

    def list_all_segments(
        self,
        status: str | None = None,
        search: str | None = None,
    ) -> tuple[list[tuple[str, StoredSegment]], list[str]]:
        """List segments across all namespaces.

        Returns:
            Tuple of (matches, namespaces skipped due to corruption).
        """
        if not os.path.isdir(self.tm_dir):
            return [], []

        namespaces = self.list_namespaces()
        results: list[tuple[str, StoredSegment]] = []
        corrupt_namespaces: list[str] = []
        for ns in namespaces:
            try:
                segments = self.list_segments(ns, status, search)
                for seg in segments:
                    results.append((ns, seg))
            except TMCorruptionError:
                corrupt_namespaces.append(ns)
                logger.warning(
                    "Skipping corrupt namespace '%s' in list; "
                    "run 'lilt tm admin repair %s'.",
                    ns,
                    ns,
                )
                continue
        return results, corrupt_namespaces
