"""Factory for instantiating LLM providers from project configuration."""

from typing import Any

from lilt.llm.openai_provider import OpenAIProvider
from lilt.llm.provider import LLMProvider


class ProviderFactory:
    """Instantiates an OpenAI-compatible LLMProvider from the llm config block."""

    @staticmethod
    def create(config: dict[str, Any]) -> LLMProvider:
        """Create an LLM provider based on the llm config block.

        If ``stages`` is present, builds a :class:`RouterLLMProvider` mapping each
        stage to its OpenAI-compatible provider.
        """
        if "stages" in config and isinstance(config["stages"], dict):
            from lilt.llm.router_provider import RouterLLMProvider  # noqa: PLC0415

            stages_config = config["stages"]

            def get_stage_config(stage_name: str) -> dict[str, Any]:
                stage_cfg = stages_config.get(stage_name, {})
                merged = config.copy()
                merged.pop("stages", None)
                merged.update(stage_cfg)
                return merged

            draft_cfg = get_stage_config("draft")
            critique_cfg = get_stage_config("critique")
            refine_cfg = get_stage_config("refine")

            return RouterLLMProvider(
                draft_provider=ProviderFactory._create_single(draft_cfg),
                critique_provider=ProviderFactory._create_single(critique_cfg),
                refine_provider=ProviderFactory._create_single(refine_cfg),
                reflection_enabled=config.get("reflection_enabled", True),
            )
        return ProviderFactory._create_single(config)

    @staticmethod
    def _create_single(config: dict[str, Any]) -> LLMProvider:
        """Create a single OpenAI-compatible provider instance."""
        provider_name = config.get("provider", "openai").lower()
        if provider_name != "openai":
            raise ValueError(
                f"Unsupported LLM provider: {provider_name}. "
                "Only 'openai' (OpenAI-compatible HTTP APIs) is supported."
            )

        api_key = config.get("api_key")
        base_url = config.get("base_url")
        model = config.get("model")
        draft_model = config.get("draft_model")
        critique_model = config.get("critique_model")
        refine_model = config.get("refine_model")
        temperature = config.get("temperature", 0.3)
        max_tokens = config.get("max_tokens")
        reflection_enabled = config.get("reflection_enabled", True)
        reflection_temperature = config.get("reflection_temperature", 0.0)
        timeout = config.get("timeout", 600.0)
        retry_config = config.get("retry", {})
        prompt_dir = config.get("prompt_dir")
        source_lang = config.get("source_lang", "English")
        target_lang = config.get("target_lang", "Spanish")
        domain_context = config.get("domain_context")
        domain_context_max_tokens = int(config.get("domain_context_max_tokens", 512))
        model_context_limit = int(config.get("model_context_limit", 8192))
        output_token_mode = config.get("output_token_mode", "shared_budget")
        reasoning_reserve = int(config.get("reasoning_reserve", 0))
        tokenizer_fudge = float(config.get("tokenizer_fudge", 1.1))
        chat_template_overhead = int(config.get("chat_template_overhead", 48))
        cost_profile = config.get("cost_profile", "balanced")
        stage_policies = config.get("stage_policies")

        return OpenAIProvider(
            api_key=api_key,
            base_url=base_url,
            model=model,
            draft_model=draft_model,
            critique_model=critique_model,
            refine_model=refine_model,
            temperature=float(temperature),
            max_tokens=max_tokens,
            reflection_enabled=reflection_enabled,
            reflection_temperature=float(reflection_temperature),
            timeout=float(timeout),
            retry_config=retry_config,
            prompt_dir=prompt_dir,
            source_lang=source_lang,
            target_lang=target_lang,
            domain_context=domain_context,
            model_context_limit=model_context_limit,
            output_token_mode=str(output_token_mode),
            reasoning_reserve=reasoning_reserve,
            tokenizer_fudge=tokenizer_fudge,
            chat_template_overhead=chat_template_overhead,
            domain_context_max_tokens=domain_context_max_tokens,
            cost_profile=str(cost_profile),
            stage_policies=stage_policies,
        )
