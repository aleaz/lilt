"""Tests for reflection cost plane and adaptive output budgets."""

from lilt.models.cost_plane import (
    CostProfileName,
    DurabilityPolicy,
    PromptProfile,
    adaptive_output_tokens,
    build_reflection_cost_plane,
    default_stage_policies,
)
from lilt.models.config import LLMConfig, LiltConfig


def test_balanced_defaults_cheap_critique_gate():
    plane = build_reflection_cost_plane(cost_profile="balanced")
    assert plane.profile == CostProfileName.BALANCED
    assert plane.reflection_enabled
    assert plane.stages["critique"].context_window == 1
    assert plane.stages["critique"].prompt_profile == PromptProfile.JSON_GATE
    assert plane.stages["draft"].context_window == 3
    assert plane.stages["draft"].output_floor == 1536
    assert plane.stages["critique"].output_floor == 1024
    assert plane.stages["refine"].output_floor == 1536


def test_draft_only_disables_reflection():
    plane = build_reflection_cost_plane(
        cost_profile="balanced", reflection_enabled=False
    )
    assert plane.profile == CostProfileName.DRAFT_ONLY
    assert not plane.reflection_enabled


def test_strict_uses_reasoned_critique():
    plane = build_reflection_cost_plane(cost_profile="strict")
    assert plane.stages["critique"].prompt_profile == PromptProfile.REASONED_GATE
    assert plane.stages["critique"].context_window == 3


def test_context_window_dict_overlays_policy():
    plane = build_reflection_cost_plane(
        cost_profile="balanced",
        context_window={"critique": 5, "draft": 2},
    )
    assert plane.stages["critique"].context_window == 5
    assert plane.stages["draft"].context_window == 2


def test_adaptive_output_tokens_caps_below_ceiling():
    from lilt.models.cost_plane import StagePolicy

    policy = StagePolicy(output_multiplier=1.5, output_floor=256, output_margin=64)
    assert adaptive_output_tokens(100, ceiling=4096, policy=policy) == 256
    assert adaptive_output_tokens(2000, ceiling=4096, policy=policy) == 3064
    assert adaptive_output_tokens(10000, ceiling=2048, policy=policy) == 2048


def test_adaptive_output_tokens_floor_never_exceeds_ceiling():
    from lilt.models.cost_plane import StagePolicy

    policy = StagePolicy(output_multiplier=2.0, output_floor=1536, output_margin=0)
    assert adaptive_output_tokens(10, ceiling=1024, policy=policy) == 1024


def test_strict_thinking_safe_floors():
    plane = build_reflection_cost_plane(cost_profile="strict")
    assert plane.stages["draft"].output_floor == 1536
    assert plane.stages["critique"].output_floor == 1024
    assert plane.stages["refine"].output_floor == 1536


def test_llm_config_aligns_cost_profile_with_reflection_flag():
    cfg = LLMConfig(reflection_enabled=False)
    assert cfg.cost_profile == "draft_only"
    cfg2 = LLMConfig(cost_profile="draft_only")
    assert cfg2.reflection_enabled is False


def test_lilt_config_builds_plane_with_tm_durability():
    root = LiltConfig()
    root.tm.durability = "batched"
    plane = root.llm.build_cost_plane(durability=root.tm.durability)
    assert plane.durability == DurabilityPolicy.BATCHED
    assert default_stage_policies(CostProfileName.BALANCED)["refine"].context_window == 2
