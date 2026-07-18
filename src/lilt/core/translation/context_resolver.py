"""Context window resolution for translation stages."""

from lilt.models.segment import SegmentStatus, StoredSegment


class ContextResolver:
    """Resolves dynamic context for segments based on the current translation phase."""

    def __init__(self, context_window: int | dict):
        if isinstance(context_window, dict):
            self.context_config = {
                "draft": context_window.get("draft", 3),
                "critique": context_window.get("critique", 3),
                "refine": context_window.get("refine", 3),
            }
        else:
            self.context_config = {
                "draft": context_window,
                "critique": context_window,
                "refine": context_window,
            }

    @staticmethod
    def _neighbor_content(segment: StoredSegment) -> str | None:
        if segment.status == SegmentStatus.DEPRECATED:
            return None
        if segment.translation:
            return segment.translation
        if segment.refined and segment.refined.content:
            return segment.refined.content
        if segment.draft and segment.draft.content:
            return segment.draft.content
        return None

    def _collect_backward(
        self,
        segment: StoredSegment,
        active_segments: list[StoredSegment],
        segment_to_idx: dict[str, int],
        window: int,
    ) -> list[str]:
        context: list[str] = []
        idx = segment_to_idx[segment.id]
        for prev_seg in reversed(active_segments[:idx]):
            content = self._neighbor_content(prev_seg)
            if content:
                context.insert(0, content)
            if len(context) >= window:
                break
        return context

    def _collect_forward(
        self,
        segment: StoredSegment,
        active_segments: list[StoredSegment],
        segment_to_idx: dict[str, int],
        window: int,
    ) -> list[str]:
        forward_context: list[str] = []
        idx = segment_to_idx[segment.id]
        for next_seg in active_segments[idx + 1 :]:
            content = self._neighbor_content(next_seg)
            if content:
                forward_context.append(content)
            if len(forward_context) >= window:
                break
        return forward_context

    def resolve_for_draft(
        self,
        segment: StoredSegment,
        active_segments: list[StoredSegment],
        segment_to_idx: dict[str, int],
    ) -> dict[str, list[str]]:
        """Prioritize previous drafts/refined text for stylistic consistency."""
        window = self.context_config["draft"]
        if window <= 0:
            return {"backward": [], "forward": []}
        return {
            "backward": self._collect_backward(
                segment, active_segments, segment_to_idx, window
            ),
            "forward": [],
        }

    def resolve_for_critique(
        self,
        segment: StoredSegment,
        active_segments: list[StoredSegment],
        segment_to_idx: dict[str, int],
    ) -> dict[str, list[str]]:
        """Use bidirectional context to evaluate draft consistency."""
        window = self.context_config["critique"]
        if window <= 0:
            return {"backward": [], "forward": []}
        return {
            "backward": self._collect_backward(
                segment, active_segments, segment_to_idx, window
            ),
            "forward": self._collect_forward(
                segment, active_segments, segment_to_idx, window
            ),
        }

    def resolve_for_refine(
        self,
        segment: StoredSegment,
        active_segments: list[StoredSegment],
        segment_to_idx: dict[str, int],
    ) -> dict[str, list[str]]:
        """Prioritize refined neighbors, falling back to draft or translation."""
        window = self.context_config["refine"]
        if window <= 0:
            return {"backward": [], "forward": []}
        return {
            "backward": self._collect_backward(
                segment, active_segments, segment_to_idx, window
            ),
            "forward": self._collect_forward(
                segment, active_segments, segment_to_idx, window
            ),
        }
