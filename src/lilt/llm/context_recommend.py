"""Recommend model_context_limit capacity from TM sources + StagePolicy windows.

Inverts :func:`~lilt.llm.token_budget.plan_token_budget` to answer what context
limit is needed for bare feasibility vs full neighbor packing (steady-state
product capacity). This is the SSOT for capacity advice; CLI/sync/translate
only surface it.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import ceil
from typing import Literal

from lilt.llm.context_packer import pack_neighbor_context
from lilt.llm.provider import LLMProvider
from lilt.llm.router_provider import RouterLLMProvider
from lilt.llm.token_budget import plan_token_budget
from lilt.models.cost_plane import ReflectionCostPlane, build_reflection_cost_plane
from lilt.models.segment import SegmentStatus, StoredSegment
from lilt.utils.token_utils import count_tokens

NEIGHBOR_EXPANSION = 1.2
_CRITIQUE_PROXY = (
    '{"requires_refine": true, "issues": '
    '[{"category": "accuracy", "description": "placeholder check"}]}'
)
_SEARCH_HI = 262_144

Verdict = Literal["ok", "raise_config", "oversized_vs_need", "bare_infeasible"]


@dataclass(frozen=True)
class StageContextRecommendation:
    """Per-stage context capacity recommendation."""

    stage: str
    min_bare: int
    min_full_neighbors: int
    max_useful: int
    worst_segment_id: str
    neighbor_tokens_needed: int
    bare_infeasible: bool
    neighbors_truncated_under_configured: bool


@dataclass(frozen=True)
class ContextLimitRecommendation:
    """Aggregate recommendation across translation stages."""

    stages: dict[str, StageContextRecommendation]
    configured_limit: int
    recommend_min: int
    recommend_max_useful: int
    verdict: Verdict
    bare_infeasible: bool
    neighbors_truncated_under_configured: bool

    @property
    def worst_segment_ids(self) -> list[str]:
        ids: list[str] = []
        for stage in self.stages.values():
            if stage.worst_segment_id and stage.worst_segment_id not in ids:
                ids.append(stage.worst_segment_id)
        return ids


def _stage_provider(llm: LLMProvider, stage: str) -> LLMProvider:
    if isinstance(llm, RouterLLMProvider):
        return llm.stage_provider(stage)
    return llm


def _cost_plane(llm: LLMProvider) -> ReflectionCostPlane:
    plane = getattr(llm, "cost_plane", None)
    if isinstance(plane, ReflectionCostPlane):
        return plane
    draft = _stage_provider(llm, "draft")
    plane = getattr(draft, "cost_plane", None)
    if isinstance(plane, ReflectionCostPlane):
        return plane
    return build_reflection_cost_plane()


def _active_ordered(segments: list[StoredSegment]) -> list[StoredSegment]:
    return [s for s in segments if s.status != SegmentStatus.DEPRECATED]


def _neighbor_sources(
    ordered: list[StoredSegment],
    index: int,
    *,
    window: int,
    bidirectional: bool,
) -> tuple[list[str], list[str]]:
    if window <= 0:
        return [], []
    backward: list[str] = []
    for prev in reversed(ordered[:index]):
        backward.insert(0, prev.source_text)
        if len(backward) >= window:
            break
    forward: list[str] = []
    if bidirectional:
        for nxt in ordered[index + 1 :]:
            forward.append(nxt.source_text)
            if len(forward) >= window:
                break
    return backward, forward


def _neighbor_tokens_needed(
    backward: list[str], forward: list[str], *, expansion: float
) -> int:
    if not backward and not forward:
        return 0
    _, tokens, _ = pack_neighbor_context(
        backward=backward,
        forward=forward,
        neighbor_budget=10**9,
        count_tokens=count_tokens,
    )
    return ceil(tokens * expansion)


def _smallest_limit(
    *,
    fixed_prompt_tokens: int,
    reserved_output: int,
    fudge: float,
    overhead: int,
    need_neighbors: int,
    search_hi: int = _SEARCH_HI,
) -> int | None:
    """Smallest context_limit with neighbor_budget >= need_neighbors, or None."""

    def ok(limit: int) -> bool:
        # Pass reserved_output as shared max_tokens so reservation matches the
        # already-computed adaptive+reasoning footprint from plan_budget.
        plan = plan_token_budget(
            context_limit=limit,
            max_tokens=reserved_output,
            fixed_prompt_tokens=fixed_prompt_tokens,
            output_token_mode="shared_budget",
            reasoning_reserve=0,
            tokenizer_fudge=fudge,
            chat_template_overhead=overhead,
        )
        return not plan.infeasible and plan.neighbor_budget >= need_neighbors

    if not ok(search_hi):
        return None
    lo, hi = 1, search_hi
    best = search_hi
    while lo <= hi:
        mid = (lo + hi) // 2
        if ok(mid):
            best = mid
            hi = mid - 1
        else:
            lo = mid + 1
    return best


def _draft_critique_proxies(source: str, stage: str) -> tuple[str, str]:
    if stage == "draft":
        return "", ""
    if stage == "critique":
        return source, ""
    return source, _CRITIQUE_PROXY


def recommend_context_limits(
    segments: list[StoredSegment],
    llm: LLMProvider,
    *,
    stages: list[str] | None = None,
    configured_limit: int | None = None,
    neighbor_expansion: float = NEIGHBOR_EXPANSION,
    search_hi: int = _SEARCH_HI,
) -> ContextLimitRecommendation:
    """Compute min/max useful ``model_context_limit`` from post-sync TM sources.

    ``min_bare`` matches translate preflight (fixed + output).
    ``min_full_neighbors`` is steady-state StagePolicy capacity (source proxies).
    """
    ordered = _active_ordered(segments)
    plane = _cost_plane(llm)
    draft_provider = _stage_provider(llm, "draft")
    configured = int(
        configured_limit
        if configured_limit is not None
        else getattr(draft_provider, "model_context_limit", 8192)
    )
    if stages is None:
        stages = (
            ["draft", "critique", "refine"] if plane.reflection_enabled else ["draft"]
        )

    stage_results: dict[str, StageContextRecommendation] = {}
    any_bare_bad = False
    any_trunc = False

    for stage in stages:
        provider = _stage_provider(llm, stage)
        window = plane.stage(stage).context_window
        bidirectional = stage in {"critique", "refine"}

        best_full = 0
        best_bare = 0
        worst_id = ""
        worst_n = -1
        stage_bare_bad = False
        trunc_under = False

        if not ordered:
            stage_results[stage] = StageContextRecommendation(
                stage=stage,
                min_bare=0,
                min_full_neighbors=0,
                max_useful=0,
                worst_segment_id="",
                neighbor_tokens_needed=0,
                bare_infeasible=False,
                neighbors_truncated_under_configured=False,
            )
            continue

        for idx, seg in enumerate(ordered):
            draft_proxy, critique_proxy = _draft_critique_proxies(
                seg.source_text, stage
            )
            plan = provider.plan_budget(
                stage=stage,
                source_text=seg.source_text,
                draft_text=draft_proxy,
                critique_text=critique_proxy,
            )
            backward, forward = _neighbor_sources(
                ordered, idx, window=window, bidirectional=bidirectional
            )
            n_needed = _neighbor_tokens_needed(
                backward, forward, expansion=neighbor_expansion
            )
            bare = _smallest_limit(
                fixed_prompt_tokens=plan.fixed_prompt_tokens,
                reserved_output=plan.reserved_output,
                fudge=plan.fudge,
                overhead=plan.chat_template_overhead,
                need_neighbors=0,
                search_hi=search_hi,
            )
            full = _smallest_limit(
                fixed_prompt_tokens=plan.fixed_prompt_tokens,
                reserved_output=plan.reserved_output,
                fudge=plan.fudge,
                overhead=plan.chat_template_overhead,
                need_neighbors=n_needed,
                search_hi=search_hi,
            )
            if bare is None:
                stage_bare_bad = True
                bare_v = search_hi
            else:
                bare_v = bare
            if full is None:
                full_v = search_hi
                trunc_under = True
            else:
                full_v = full

            check = plan_token_budget(
                context_limit=configured,
                max_tokens=plan.reserved_output,
                fixed_prompt_tokens=plan.fixed_prompt_tokens,
                output_token_mode="shared_budget",
                tokenizer_fudge=plan.fudge,
                chat_template_overhead=plan.chat_template_overhead,
            )
            if n_needed > 0 and (check.infeasible or check.neighbor_budget < n_needed):
                trunc_under = True

            if full_v > best_full or (full_v == best_full and n_needed > worst_n):
                worst_n = n_needed
                worst_id = seg.id
            best_bare = max(best_bare, bare_v)
            best_full = max(best_full, full_v)

        any_bare_bad = any_bare_bad or stage_bare_bad
        any_trunc = any_trunc or trunc_under
        stage_results[stage] = StageContextRecommendation(
            stage=stage,
            min_bare=best_bare,
            min_full_neighbors=best_full,
            max_useful=best_full,
            worst_segment_id=worst_id,
            neighbor_tokens_needed=max(0, worst_n),
            bare_infeasible=stage_bare_bad,
            neighbors_truncated_under_configured=trunc_under,
        )

    recommend_min = max(
        (s.min_full_neighbors for s in stage_results.values()), default=0
    )
    recommend_max = max((s.max_useful for s in stage_results.values()), default=0)
    if any_bare_bad:
        verdict: Verdict = "bare_infeasible"
    elif configured < recommend_min:
        verdict = "raise_config"
    elif configured > recommend_max * 2 and recommend_max > 0:
        verdict = "oversized_vs_need"
    else:
        verdict = "ok"

    return ContextLimitRecommendation(
        stages=stage_results,
        configured_limit=configured,
        recommend_min=recommend_min,
        recommend_max_useful=recommend_max,
        verdict=verdict,
        bare_infeasible=any_bare_bad,
        neighbors_truncated_under_configured=any_trunc,
    )


def format_capacity_warnings(report: ContextLimitRecommendation) -> list[str]:
    """Human-readable advisories for sync/translate surfaces."""
    messages: list[str] = []
    if report.bare_infeasible:
        worst = ", ".join(report.worst_segment_ids[:5]) or "unknown"
        messages.append(
            "Token budget: at least one segment cannot fit fixed prompt + output "
            f"under any practical context limit (worst ids: {worst}). "
            "Raise model_context_limit / serving n_ctx, lower max_tokens or "
            "reasoning_reserve, or shorten domain_context. "
            "See `lilt tm budget` for details."
        )
    elif report.verdict == "raise_config":
        messages.append(
            f"Token budget: configured model_context_limit={report.configured_limit} "
            f"is below recommended min {report.recommend_min} for StagePolicy "
            "neighbor windows (steady-state). Neighbors may truncate. "
            "Align serving n_ctx and llm.model_context_limit, or lower "
            "llm.context_window / stage_policies. "
            "Run `lilt tm budget` for per-stage detail."
        )
    elif report.neighbors_truncated_under_configured:
        messages.append(
            f"Token budget: under model_context_limit={report.configured_limit}, "
            "some segments will pack fewer neighbors than StagePolicy requests. "
            f"Recommended min={report.recommend_min}. Run `lilt tm budget`."
        )
    return messages


def advise_context_capacity(
    llm: LLMProvider,
    segments: list[StoredSegment],
    *,
    stages: list[str] | None = None,
    configured_limit: int | None = None,
) -> ContextLimitRecommendation:
    """Compute recommendation for sync/translate advisory surfaces."""
    return recommend_context_limits(
        segments,
        llm,
        stages=stages,
        configured_limit=configured_limit,
    )
