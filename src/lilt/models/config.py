"""Typed workspace configuration models."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ProjectConfig(BaseModel):
    """Project-level settings (languages, build injections)."""

    model_config = ConfigDict(extra="allow")

    source_lang: str = "English"
    target_lang: str = "Spanish"
    domain_context: str = ""
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
    max_tokens: int = 8192
    model_context_limit: int = 8192
    context_window: int | dict[str, int] = 3
    translation_mode: str = "workflow"
    timeout: float = 600.0
    draft_empty_retries: int = 1
    token_price_per_million: float = 5.0
    reflection_enabled: bool = True
    prompt_dir: str | None = None
    retry: LLMRetryConfig = Field(default_factory=LLMRetryConfig)
    stages: dict[str, Any] | None = None
    api_key: str | None = None

    @field_validator("context_window", mode="before")
    @classmethod
    def _coerce_context_window(cls, value: Any) -> int | dict[str, int]:
        if isinstance(value, dict):
            return value
        if value is None:
            return 3
        return int(value)


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


class LiltConfig(BaseModel):
    """Root validated configuration for a LILT workspace."""

    model_config = ConfigDict(extra="allow")

    project: ProjectConfig = Field(default_factory=ProjectConfig)
    llm: LLMConfig = Field(default_factory=LLMConfig)
    parser: ParserConfig = Field(default_factory=ParserConfig)
    review: ReviewConfig = Field(default_factory=ReviewConfig)

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
