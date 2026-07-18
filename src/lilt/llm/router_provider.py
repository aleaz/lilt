"""Stage-specific LLM router for hybrid local and cloud reflection pipelines."""

from lilt.llm.base_provider import BaseLLMProvider
from lilt.llm.provider import ContextData, LLMProvider, LLMResponse
from lilt.llm.token_budget import BudgetPlan


class RouterLLMProvider(BaseLLMProvider):
    """Router that delegates LLM calls to stage-specific providers.

    This enables hybrid architectures, e.g., local Ollama for drafting,
    and OpenAI Cloud for critique/refinement.
    """

    def __init__(
        self,
        draft_provider: LLMProvider,
        critique_provider: LLMProvider,
        refine_provider: LLMProvider,
        reflection_enabled: bool = True,
    ):
        self.draft_provider = draft_provider
        self.critique_provider = critique_provider
        self.refine_provider = refine_provider
        self._reflection_enabled = reflection_enabled

    @property
    def reflection_enabled(self) -> bool:
        """Return whether reflection is enabled for this provider."""
        return self._reflection_enabled

    def generate_draft(
        self, text: str, context: ContextData | None = None
    ) -> LLMResponse:
        """Delegate draft generation to the draft provider."""
        return self.draft_provider.generate_draft(text, context)

    def generate_critique(
        self, draft_text: str, source_text: str, context: ContextData | None = None
    ) -> LLMResponse:
        """Delegate critique generation to the critique provider."""
        return self.critique_provider.generate_critique(
            draft_text, source_text, context
        )

    def generate_refine(
        self,
        draft_text: str,
        critique_text: str,
        source_text: str,
        context: ContextData | None = None,
    ) -> LLMResponse:
        """Delegate refinement generation to the refine provider."""
        return self.refine_provider.generate_refine(
            draft_text, critique_text, source_text, context
        )

    def get_prompt_version(self, stage: str) -> str:
        """Delegate prompt version resolution to the stage-specific provider."""
        if stage == "sequential":
            stage = "draft"
        provider = self.stage_provider(stage)
        if hasattr(provider, "get_prompt_version"):
            return provider.get_prompt_version(stage)
        return f"{stage}:unknown"

    def stage_provider(self, stage: str) -> LLMProvider:
        """Return the delegate provider for a workflow stage."""
        if stage == "sequential":
            stage = "draft"
        provider_map = {
            "draft": self.draft_provider,
            "critique": self.critique_provider,
            "refine": self.refine_provider,
        }
        provider = provider_map.get(stage)
        if provider is None:
            raise ValueError(f"Unknown workflow stage: {stage}")
        return provider

    def stage_model_name(self, stage: str) -> str:
        """Return the model name for telemetry from the stage delegate."""
        if stage == "sequential":
            stage = "draft"
        provider = self.stage_provider(stage)
        stage_attr = f"{stage}_model"
        return getattr(provider, stage_attr, getattr(provider, "model", "unknown"))

    def plan_budget(
        self,
        *,
        stage: str,
        source_text: str,
        draft_text: str = "",
        critique_text: str = "",
    ) -> BudgetPlan:
        """Delegate budget planning to the stage-specific provider."""
        return self.stage_provider(stage).plan_budget(
            stage=stage,
            source_text=source_text,
            draft_text=draft_text,
            critique_text=critique_text,
        )
