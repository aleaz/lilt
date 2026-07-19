"""Typed workspace configuration models."""

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class ProjectConfig(BaseModel):
    """Project-level settings (languages, build injections)."""

    model_config = ConfigDict(extra="allow")

    source_lang: str = "English"
    target_lang: str = "Spanish"
    domain_context: str = ""
    domain_context_max_tokens: int = 512
    injections: list[str] = Field(default_factory=list)


class LLMRetryConfig(BaseModel):
    """Retry policy for LLM HTTP calls."""

    model_config = ConfigDict(extra="allow")

    max_attempts: int = 3
    min_wait_seconds: int = 2
    max_wait_seconds: int = 60


class LLMConfig(BaseModel):
    """LLM provider and reflection workflow settings."""

    model_config = ConfigDict(extra="allow")

    provider: str = "openai"
    model: str = "local-model"
    draft_model: str = ""
    critique_model: str = ""
    refine_model: str = ""
    base_url: str = "http://localhost:1234/v1"
    temperature: float = 0.3
    reflection_temperature: float = 0.0
    max_tokens: int = 4096
    model_context_limit: int = 8192
    context_window: int | dict[str, int] = 3
    translation_mode: str = "workflow"
    timeout: float = 600.0
    draft_empty_retries: int = 1
    token_price_per_million: float = 5.0
    reflection_enabled: bool = True
    cost_profile: Literal["balanced", "draft_only", "strict"] = "balanced"
    stage_policies: dict[str, Any] | None = None
    prompt_dir: str | None = None
    retry: LLMRetryConfig = Field(default_factory=LLMRetryConfig)
    stages: dict[str, Any] | None = None
    api_key: str | None = None
    output_token_mode: Literal["shared_budget", "split_budget"] = "shared_budget"
    reasoning_reserve: int = 0
    tokenizer_fudge: float = 1.1
    chat_template_overhead: int = 48

    @field_validator("context_window", mode="before")
    @classmethod
    def _coerce_context_window(cls, value: Any) -> int | dict[str, int]:
        if isinstance(value, dict):
            return value
        if value is None:
            return 3
        return int(value)

    @model_validator(mode="after")
    def _align_reflection_with_cost_profile(self) -> "LLMConfig":
        if self.cost_profile == "draft_only":
            self.reflection_enabled = False
        elif not self.reflection_enabled:
            self.cost_profile = "draft_only"
        return self

    @model_validator(mode="after")
    def _context_limit_exceeds_output_reservation(self) -> "LLMConfig":
        reserved = self.max_tokens
        if self.output_token_mode == "split_budget":
            reserved = self.max_tokens + max(0, self.reasoning_reserve)
        if self.model_context_limit <= reserved:
            raise ValueError(
                "llm.model_context_limit must be greater than reserved output "
                f"({reserved}: max_tokens"
                + (
                    f"+reasoning_reserve={self.reasoning_reserve}"
                    if self.output_token_mode == "split_budget"
                    else ""
                )
                + f"); got model_context_limit={self.model_context_limit}."
            )
        return self

    def build_cost_plane(self, *, durability: str = "strict") -> Any:
        """Resolve :class:`~lilt.models.cost_plane.ReflectionCostPlane` for this LLM block."""
        from lilt.models.cost_plane import build_reflection_cost_plane

        return build_reflection_cost_plane(
            cost_profile=self.cost_profile,
            reflection_enabled=self.reflection_enabled,
            context_window=self.context_window,
            durability=durability,
            stage_overrides=self.stage_policies,
        )

class ParserIdentityConfig(BaseModel):
    """Sync identity carry-over threshold."""

    similarity_threshold: float = 0.85


class ParserConfig(BaseModel):
    """LaTeX parser masking and segmentation settings."""

    model_config = ConfigDict(extra="allow")

    custom_macros: list[dict[str, Any]] = Field(default_factory=list)
    identity: ParserIdentityConfig = Field(default_factory=ParserIdentityConfig)
    block_transparent_macros: list[str] = Field(default_factory=list)
    inline_transparent_macros: list[str] = Field(default_factory=list)
    opaque_environments: list[str] = Field(default_factory=list)
    protected_terms: list[str] = Field(default_factory=list)
    environment_aliases: dict[str, dict[str, str]] = Field(default_factory=dict)
    max_segment_chars: int | None = None


class ReviewConfig(BaseModel):
    """Human review queue configuration."""

    model_config = ConfigDict(extra="allow")

    queue_statuses: list[str] = Field(default_factory=lambda: ["refined", "reviewed"])


class TMConfig(BaseModel):
    """Translation Memory persistence settings."""

    model_config = ConfigDict(extra="allow")

    durability: Literal["strict", "batched"] = "strict"


class LiltConfig(BaseModel):
    """Root validated configuration for a LILT workspace."""

    model_config = ConfigDict(extra="allow")

    project: ProjectConfig = Field(default_factory=ProjectConfig)
    llm: LLMConfig = Field(default_factory=LLMConfig)
    parser: ParserConfig = Field(default_factory=ParserConfig)
    review: ReviewConfig = Field(default_factory=ReviewConfig)
    tm: TMConfig = Field(default_factory=TMConfig)

    def to_llm_factory_dict(
        self,
        *,
        workspace_dir: str | None = None,
    ) -> dict[str, Any]:
        """Build the dict expected by ProviderFactory, with project fields merged."""
        data = self.llm.model_dump()
        data["source_lang"] = self.project.source_lang
        data["target_lang"] = self.project.target_lang
        data["domain_context"] = self.project.domain_context or None
        data["domain_context_max_tokens"] = self.project.domain_context_max_tokens
        data["cost_profile"] = self.llm.cost_profile
        data["stage_policies"] = self.llm.stage_policies
        data["tm_durability"] = self.tm.durability
        if self.llm.prompt_dir and workspace_dir:
            prompt_dir = self.llm.prompt_dir
            data["prompt_dir"] = (
                prompt_dir
                if prompt_dir.startswith("/")
                else f"{workspace_dir.rstrip('/')}/{prompt_dir}"
            )
        return data

    def review_dict(self) -> dict[str, Any]:
        """Dict slice for ReviewPolicy.from_config."""
        return {"review": self.review.model_dump()}
