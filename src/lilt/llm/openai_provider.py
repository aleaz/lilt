"""OpenAI-compatible LLM provider with streaming and telemetry hooks."""

import logging
import os
import time
from typing import Any

from openai import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    OpenAI,
    RateLimitError,
)
from tenacity import (
    Retrying,
    before_sleep_log,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
)

from lilt.exceptions import (
    ConfigurationError,
    ContextLengthExceededError,
    OutputTokenStarvationError,
)
from lilt.llm.base_provider import BaseLLMProvider
from lilt.llm.context_packer import pack_neighbor_context
from lilt.llm.output_gate import validate_llm_output
from lilt.llm.prompt_manager import PromptManager
from lilt.llm.provider import ContextData, LLMResponse
from lilt.llm.token_budget import (
    BudgetPlan,
    OutputTokenMode,
    call_footprint,
    plan_token_budget,
)
from lilt.parser.linguistic import has_linguistic_content
from lilt.utils.token_utils import count_tokens

_RETRYABLE_EXCEPTIONS = (
    APIConnectionError,
    APITimeoutError,
    RateLimitError,
    ConnectionError,
    TimeoutError,
)


def _is_retryable(exc: BaseException) -> bool:
    # EmptyLLMOutputError is intentionally NOT retryable here. It is raised by
    # validate_llm_output() outside the tenacity Retrying block, so tenacity never
    # actually sees it; treating it as retryable was a latent footgun. Empty-output
    # handling lives in the workflow strategy (see draft_empty_retries).
    if isinstance(exc, _RETRYABLE_EXCEPTIONS):
        return True
    return isinstance(exc, APIStatusError) and exc.status_code >= 500


logger = logging.getLogger(__name__)


def _truncate_to_token_cap(text: str, max_tokens: int) -> tuple[str, bool]:
    """Truncate ``text`` so ``count_tokens`` stays at or under ``max_tokens``."""
    if max_tokens <= 0 or not text:
        return "", bool(text)
    if count_tokens(text) <= max_tokens:
        return text, False
    # Binary search on character length; tiktoken is monotonic with prefix length.
    lo, hi = 0, len(text)
    best = ""
    while lo <= hi:
        mid = (lo + hi) // 2
        candidate = text[:mid]
        if count_tokens(candidate) <= max_tokens:
            best = candidate
            lo = mid + 1
        else:
            hi = mid - 1
    return best.rstrip(), True


class OpenAIProvider(BaseLLMProvider):
    """OpenAI-compatible LLM Provider.

    Supports an optional 3-step Reflective Agentic Workflow (arch-04):
        1. Draft   — initial translation at `temperature` (creative)
        2. Critique — structured MQM analysis at `reflection_temperature` (deterministic)
        3. Refine  — guided revision at `reflection_temperature` (precise)

    Short-circuit optimisation: if the Critique phase returns JSON with
    ``requires_refine: false``, the Refine call is skipped entirely,
    saving roughly one third of the token cost of the reflection cycle.

    See docs/architecture/04-translation-engine.md.

    By default uses LM Studio local server if OPENAI_BASE_URL / OPENAI_API_KEY
    are not set.
    """

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
        draft_model: str | None = None,
        critique_model: str | None = None,
        refine_model: str | None = None,
        temperature: float = 0.3,
        max_tokens: int | None = None,
        reflection_enabled: bool = False,
        reflection_temperature: float = 0.0,
        retry_config: dict | None = None,
        prompt_dir: str | None = None,
        source_lang: str = "English",
        target_lang: str = "Spanish",
        domain_context: str | None = None,
        model_context_limit: int = 8192,
        timeout: float = 600.0,
        output_token_mode: str = OutputTokenMode.SHARED_BUDGET.value,
        reasoning_reserve: int = 0,
        tokenizer_fudge: float = 1.1,
        chat_template_overhead: int = 48,
        domain_context_max_tokens: int = 512,
    ):
        _api_key = api_key if api_key is not None else os.getenv("OPENAI_API_KEY")
        self.base_url: str = (
            base_url
            if base_url is not None
            else os.getenv("OPENAI_BASE_URL", "http://localhost:1234/v1")
        )

        if not _api_key:
            if any(
                local in self.base_url
                for local in ("localhost", "127.0.0.1", "0.0.0.0")
            ):
                self.api_key = "lm-studio"
            else:
                raise ConfigurationError(
                    "OPENAI_API_KEY is not set for remote provider."
                )
        else:
            self.api_key = _api_key
        self.model: str = (
            model if model is not None else os.getenv("LLM_MODEL", "local-model")
        )
        self.draft_model: str = draft_model if draft_model else self.model
        self.critique_model: str = critique_model if critique_model else self.model
        self.refine_model: str = refine_model if refine_model else self.model

        # Draft temperature: controls creativity of the initial translation pass.
        self.temperature: float = temperature

        # Reflection temperature: used for both Critique and Refine calls.
        # A lower value (default 0.0) produces deterministic, instruction-following
        # outputs — ideal for structured analysis and guided revision.
        self.reflection_temperature: float = reflection_temperature

        self.max_tokens: int | None = max_tokens
        self._reflection_enabled: bool = reflection_enabled
        self.model_context_limit: int = model_context_limit
        self.timeout: float = timeout
        self.output_token_mode = OutputTokenMode(output_token_mode)
        self.reasoning_reserve = max(0, int(reasoning_reserve))
        self.tokenizer_fudge = max(1.0, float(tokenizer_fudge))
        self.chat_template_overhead = max(0, int(chat_template_overhead))
        self.domain_context_max_tokens = max(0, int(domain_context_max_tokens))

        self.client = OpenAI(
            api_key=self.api_key, base_url=self.base_url, timeout=self.timeout
        )

        self.retry_config = retry_config or {}

        # Initialize Prompt Manager
        self.prompt_manager = PromptManager(override_dir=prompt_dir)

        # Store context variables for rendering
        self.source_lang = source_lang
        self.target_lang = target_lang
        self.domain_truncated = False
        self.domain_context = self._cap_domain_context(domain_context)

    def _cap_domain_context(self, domain_context: str | None) -> str | None:
        if not domain_context:
            return domain_context
        capped, truncated = _truncate_to_token_cap(
            domain_context, self.domain_context_max_tokens
        )
        if truncated:
            self.domain_truncated = True
            logger.warning(
                "domain_context truncated to %s tokens (project.domain_context_max_tokens)",
                self.domain_context_max_tokens,
            )
        return capped or None

    def _render_system_prompt(self, context_block: str) -> str:
        """Build the system message for a reflection stage."""
        return self.prompt_manager.render(
            "system",
            source_lang=self.source_lang,
            target_lang=self.target_lang,
            domain_context=self.domain_context,
            context_block=context_block,
        )

    def _measure_fixed_prompt_tokens(
        self,
        *,
        stage: str,
        source_text: str,
        draft_text: str = "",
        critique_text: str = "",
    ) -> int:
        """Count system + user templates with an empty neighbor block."""
        system_tokens = self.prompt_manager.measure(
            "system",
            source_lang=self.source_lang,
            target_lang=self.target_lang,
            domain_context=self.domain_context,
            context_block="",
        )
        if stage == "draft":
            user_tokens = self.prompt_manager.measure("draft", text=source_text)
        elif stage == "critique":
            user_tokens = self.prompt_manager.measure(
                "critique", text=source_text, draft=draft_text
            )
        elif stage == "refine":
            user_tokens = self.prompt_manager.measure(
                "refine",
                text=source_text,
                draft=draft_text,
                critique=critique_text,
            )
        else:
            user_tokens = self.prompt_manager.measure("draft", text=source_text)
        return system_tokens + user_tokens

    def plan_budget(
        self,
        *,
        stage: str,
        source_text: str,
        draft_text: str = "",
        critique_text: str = "",
    ) -> BudgetPlan:
        """Compute a :class:`BudgetPlan` for a stage without packing neighbors."""
        fixed = self._measure_fixed_prompt_tokens(
            stage=stage,
            source_text=source_text,
            draft_text=draft_text,
            critique_text=critique_text,
        )
        return plan_token_budget(
            context_limit=self.model_context_limit,
            max_tokens=self.max_tokens if self.max_tokens is not None else 0,
            fixed_prompt_tokens=fixed,
            output_token_mode=self.output_token_mode,
            reasoning_reserve=self.reasoning_reserve,
            tokenizer_fudge=self.tokenizer_fudge,
            chat_template_overhead=self.chat_template_overhead,
            domain_truncated=self.domain_truncated,
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _build_context_block(
        self,
        context: ContextData | None,
        target_text: str = "",
        *,
        stage: str = "draft",
        draft_text: str = "",
        critique_text: str = "",
    ) -> str:
        """Return the XML-fenced context block, packed under the measured budget."""
        if not context:
            return ""

        backward: list[str] = []
        forward: list[str] = []
        if isinstance(context, dict):
            backward = list(context.get("backward", []))
            forward = list(context.get("forward", []))
        else:
            backward = list(context)

        if not backward and not forward:
            return ""

        plan = self.plan_budget(
            stage=stage,
            source_text=target_text,
            draft_text=draft_text,
            critique_text=critique_text,
        )
        if plan.infeasible:
            logger.warning(
                "Token budget infeasible for stage=%s: fixed=%s reserved_output=%s "
                "limit=%s; skipping neighbor context.",
                stage,
                plan.fixed_prompt_tokens,
                plan.reserved_output,
                plan.context_limit,
            )
            return ""

        block, _neighbor_tokens, truncated = pack_neighbor_context(
            backward=backward,
            forward=forward,
            neighbor_budget=plan.neighbor_budget,
            count_tokens=count_tokens,
        )
        if truncated:
            logger.warning(
                "neighbors_truncated stage=%s neighbor_budget=%s "
                "reserved_output=%s fixed_prompt_tokens=%s context_limit=%s",
                stage,
                plan.neighbor_budget,
                plan.reserved_output,
                plan.fixed_prompt_tokens,
                plan.context_limit,
            )
        return block

    def _call_llm(
        self,
        model: str,
        messages: list[dict[str, str]],
        temperature: float,
        *,
        stage: str | None = None,
    ) -> LLMResponse:
        """Single LLM API call with the configured model and token settings."""
        total_prompt_tokens = sum(
            count_tokens(m["content"], model_name=model) for m in messages
        )
        plan = plan_token_budget(
            context_limit=self.model_context_limit,
            max_tokens=self.max_tokens if self.max_tokens is not None else 0,
            fixed_prompt_tokens=total_prompt_tokens,
            output_token_mode=self.output_token_mode,
            reasoning_reserve=self.reasoning_reserve,
            tokenizer_fudge=self.tokenizer_fudge,
            chat_template_overhead=self.chat_template_overhead,
            domain_truncated=self.domain_truncated,
        )
        effective, footprint = call_footprint(total_prompt_tokens, plan)
        if footprint > self.model_context_limit:
            raise ContextLengthExceededError(
                "Prompt plus reserved output exceeds model context limit. "
                f"effective_prompt={effective}, overhead={plan.chat_template_overhead}, "
                f"reserved_output={plan.reserved_output}, "
                f"limit={self.model_context_limit}, "
                f"raw_prompt_tokens={total_prompt_tokens}."
            )

        kwargs: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
        }
        if self.max_tokens is not None:
            kwargs["max_tokens"] = self.max_tokens

        max_attempts = self.retry_config.get("max_attempts", 3)
        min_wait = self.retry_config.get("min_wait_seconds", 2)
        max_wait = self.retry_config.get("max_wait_seconds", 60)

        kwargs["stream"] = True

        for attempt in Retrying(
            wait=wait_exponential(multiplier=1, min=min_wait, max=max_wait),
            stop=stop_after_attempt(max_attempts),
            retry=retry_if_exception(_is_retryable),
            reraise=True,
            before_sleep=before_sleep_log(logger, logging.WARNING),
        ):
            with attempt:
                t0 = time.perf_counter()
                ttft_ms = None

                # Try to request usage in stream
                kwargs["stream_options"] = {"include_usage": True}
                try:
                    response = self.client.chat.completions.create(**kwargs)  # type: ignore
                except TypeError:
                    # Older openai clients might reject stream_options
                    kwargs.pop("stream_options")
                    response = self.client.chat.completions.create(**kwargs)  # type: ignore

                chunks = []
                final_usage = None

                for chunk in response:
                    if ttft_ms is None:
                        ttft_ms = int((time.perf_counter() - t0) * 1000)
                    if isinstance(chunk, tuple):
                        continue
                    if chunk.choices and chunk.choices[0].delta.content:
                        chunks.append(chunk.choices[0].delta.content)
                    if hasattr(chunk, "usage") and chunk.usage:
                        final_usage = chunk.usage

                content = "".join(chunks)
                duration_ms = int((time.perf_counter() - t0) * 1000)

                res = LLMResponse(
                    text=content.strip() if content else "",
                    duration_ms=duration_ms,
                    ttft_ms=ttft_ms,
                )

                if final_usage:
                    res.prompt_tokens = final_usage.prompt_tokens
                    res.completion_tokens = final_usage.completion_tokens
                    # Handle token fallback locally if missing? We'll let the provider give it.
                    if (
                        hasattr(final_usage, "prompt_tokens_details")
                        and final_usage.prompt_tokens_details
                    ):
                        res.cached_tokens = getattr(
                            final_usage.prompt_tokens_details, "cached_tokens", 0
                        )
                    reasoning_tokens = 0
                    details = getattr(final_usage, "completion_tokens_details", None)
                    if details is not None:
                        reasoning_tokens = int(
                            getattr(details, "reasoning_tokens", 0) or 0
                        )
                    spent = max(res.completion_tokens or 0, reasoning_tokens)
                    if not res.text and spent > 0:
                        raise OutputTokenStarvationError(spent, stage=stage)
                else:
                    # Fallback token estimation
                    res.prompt_tokens = sum(len(m["content"]) // 4 for m in messages)
                    res.completion_tokens = len(res.text) // 4
                    res.cached_tokens = 0
                return res

        raise RuntimeError("_call_llm exhausted retries without a response")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def reflection_enabled(self) -> bool:
        """Return whether reflection is enabled for this provider."""
        return self._reflection_enabled

    def generate_draft(
        self, text: str, context: ContextData | None = None
    ) -> LLMResponse:
        """Generate the initial translation draft."""
        if not has_linguistic_content(text):
            return LLMResponse(text=text)

        context_block = self._build_context_block(
            context, target_text=text, stage="draft"
        )
        current_system_prompt = self._render_system_prompt(context_block)

        user_prompt = self.prompt_manager.render("draft", text=text)

        res = self._call_llm(
            model=self.draft_model,
            messages=[
                {"role": "system", "content": current_system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=self.temperature,
            stage="draft",
        )
        res.text = validate_llm_output(res.text, source=text, stage="draft")
        return res

    def generate_critique(
        self, draft_text: str, source_text: str, context: ContextData | None = None
    ) -> LLMResponse:
        """Generate a critique of the given draft."""
        context_block = self._build_context_block(
            context,
            target_text=source_text,
            stage="critique",
            draft_text=draft_text,
        )
        current_system_prompt = self._render_system_prompt(context_block)

        critique_prompt = self.prompt_manager.render(
            "critique",
            text=source_text,
            draft=draft_text,
        )

        res = self._call_llm(
            model=self.critique_model,
            messages=[
                {"role": "system", "content": current_system_prompt},
                {"role": "user", "content": critique_prompt},
            ],
            temperature=self.reflection_temperature,
            stage="critique",
        )
        res.text = validate_llm_output(res.text, source=source_text, stage="critique")
        return res

    def generate_refine(
        self,
        draft_text: str,
        critique_text: str,
        source_text: str,
        context: ContextData | None = None,
    ) -> LLMResponse:
        """Apply critique to draft and return the refined translation."""
        context_block = self._build_context_block(
            context,
            target_text=source_text,
            stage="refine",
            draft_text=draft_text,
            critique_text=critique_text,
        )
        current_system_prompt = self._render_system_prompt(context_block)

        refine_prompt = self.prompt_manager.render(
            "refine",
            text=source_text,
            draft=draft_text,
            critique=critique_text,
        )

        res = self._call_llm(
            model=self.refine_model,
            messages=[
                {"role": "system", "content": current_system_prompt},
                {"role": "user", "content": refine_prompt},
            ],
            temperature=self.reflection_temperature,
            stage="refine",
        )
        res.text = validate_llm_output(res.text, source=source_text, stage="refine")
        return res

    # (translate_segment_iter inherited from BaseLLMProvider)
