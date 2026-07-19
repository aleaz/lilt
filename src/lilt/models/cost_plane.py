"""Reflection cost plane: stage policies, cost profiles, and durability."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class CostProfileName(str, Enum):
    """Product-level reflection cost profile (SSOT for reflection on/off)."""

    BALANCED = "balanced"
    DRAFT_ONLY = "draft_only"
    STRICT = "strict"


class PromptProfile(str, Enum):
    """Critique (and future stage) prompt contract."""

    JSON_GATE = "json_gate"
    REASONED_GATE = "reasoned_gate"


class ThinkingMode(str, Enum):
    """Server-side thinking / reasoning hint for a stage (best-effort to the API).

    Distinct from :class:`PromptProfile.REASONED_GATE`, which only shapes the
    critique *prompt* (``<reasoning>`` block), not LM Studio / vendor thinking.
    """

    OFF = "off"
    ON = "on"
    MINIMAL = "minimal"


class DurabilityPolicy(str, Enum):
    """TM JSONL durability vs I/O cost tradeoff."""

    STRICT = "strict"
    BATCHED = "batched"


class StagePolicy(BaseModel):
    """Per-stage reflection cost and prompt policy."""

    model_config = ConfigDict(extra="forbid")

    context_window: int = 3
    prompt_profile: PromptProfile = PromptProfile.JSON_GATE
    output_multiplier: float = 1.5
    output_floor: int = 256
    output_margin: int = 64
    thinking: ThinkingMode = ThinkingMode.OFF


class ReflectionCostPlane(BaseModel):
    """Resolved cost plane for a translation run."""

    model_config = ConfigDict(extra="forbid")

    profile: CostProfileName = CostProfileName.BALANCED
    stages: dict[str, StagePolicy] = Field(default_factory=dict)
    durability: DurabilityPolicy = DurabilityPolicy.STRICT

    @property
    def reflection_enabled(self) -> bool:
        """Whether critique/refine stages are active for this profile."""
        return self.profile != CostProfileName.DRAFT_ONLY

    def context_windows(self) -> dict[str, int]:
        """Neighbor window sizes keyed by stage name."""
        return {name: policy.context_window for name, policy in self.stages.items()}

    def stage(self, name: str) -> StagePolicy:
        """Return policy for ``name``, or an empty default StagePolicy."""
        return self.stages.get(name, StagePolicy())


def default_stage_policies(profile: CostProfileName) -> dict[str, StagePolicy]:
    """Built-in StagePolicy defaults for a cost profile."""
    if profile == CostProfileName.STRICT:
        return {
            "draft": StagePolicy(
                context_window=3,
                prompt_profile=PromptProfile.JSON_GATE,
                output_multiplier=2.0,
                output_floor=1536,
            ),
            "critique": StagePolicy(
                context_window=3,
                prompt_profile=PromptProfile.REASONED_GATE,
                output_multiplier=1.0,
                output_floor=1024,
            ),
            "refine": StagePolicy(
                context_window=3,
                prompt_profile=PromptProfile.JSON_GATE,
                output_multiplier=2.0,
                output_floor=1536,
            ),
        }
    if profile == CostProfileName.DRAFT_ONLY:
        return {
            "draft": StagePolicy(
                context_window=3,
                output_multiplier=1.5,
                output_floor=256,
            ),
            "critique": StagePolicy(context_window=0),
            "refine": StagePolicy(context_window=0),
        }
    # balanced — cheap critique gate, modest neighbors; floors sized for
    # thinking models so reasoning cannot starve message.content.
    return {
        "draft": StagePolicy(
            context_window=3,
            prompt_profile=PromptProfile.JSON_GATE,
            output_multiplier=1.5,
            output_floor=1536,
        ),
        "critique": StagePolicy(
            context_window=1,
            prompt_profile=PromptProfile.JSON_GATE,
            output_multiplier=0.75,
            output_floor=1024,
            output_margin=32,
        ),
        "refine": StagePolicy(
            context_window=2,
            prompt_profile=PromptProfile.JSON_GATE,
            output_multiplier=1.5,
            output_floor=1536,
        ),
    }


def resolve_cost_profile_name(
    *,
    cost_profile: str | CostProfileName | None,
    reflection_enabled: bool,
) -> CostProfileName:
    """Resolve profile; ``reflection_enabled=false`` forces draft_only."""
    if not reflection_enabled:
        return CostProfileName.DRAFT_ONLY
    if cost_profile is None or cost_profile == "":
        return CostProfileName.BALANCED
    return CostProfileName(str(cost_profile))


def build_reflection_cost_plane(
    *,
    cost_profile: str | CostProfileName | None = None,
    reflection_enabled: bool = True,
    context_window: int | dict[str, int] = 3,
    durability: str | DurabilityPolicy = DurabilityPolicy.STRICT,
    stage_overrides: dict[str, Any] | None = None,
) -> ReflectionCostPlane:
    """Build the SSOT cost plane from config fragments."""
    profile = resolve_cost_profile_name(
        cost_profile=cost_profile,
        reflection_enabled=reflection_enabled,
    )
    stages = default_stage_policies(profile)

    if isinstance(context_window, dict):
        for name, value in context_window.items():
            if name in stages:
                stages[name] = stages[name].model_copy(update={"context_window": value})
    elif isinstance(context_window, int) and context_window != 3:
        # Explicit non-default scalar overrides all stages (legacy opt-in).
        for name in stages:
            stages[name] = stages[name].model_copy(
                update={"context_window": context_window}
            )
    elif isinstance(context_window, int) and profile == CostProfileName.STRICT:
        for name in stages:
            stages[name] = stages[name].model_copy(
                update={"context_window": context_window}
            )
    elif (
        isinstance(context_window, int)
        and context_window == 3
        and profile == CostProfileName.DRAFT_ONLY
    ):
        stages["draft"] = stages["draft"].model_copy(update={"context_window": 3})

    if stage_overrides:
        for name, raw in stage_overrides.items():
            if name not in stages or not isinstance(raw, dict):
                continue
            current = stages[name].model_dump()
            current.update(raw)
            stages[name] = StagePolicy.model_validate(current)

    dur = (
        durability
        if isinstance(durability, DurabilityPolicy)
        else DurabilityPolicy(durability)
    )
    return ReflectionCostPlane(profile=profile, stages=stages, durability=dur)


def adaptive_output_tokens(
    source_tokens: int,
    *,
    ceiling: int,
    policy: StagePolicy | None = None,
) -> int:
    """Cap completion tokens by source size under a stage policy."""
    pol = policy or StagePolicy()
    if ceiling <= 0:
        return ceiling
    estimated = int(max(0, source_tokens) * pol.output_multiplier) + pol.output_margin
    return min(ceiling, max(pol.output_floor, estimated))
