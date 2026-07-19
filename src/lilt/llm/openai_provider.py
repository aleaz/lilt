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
from lilt.models.cost_plane import (
    PromptProfile,
    ReflectionCostPlane,
    StagePolicy,
    ThinkingMode,
    adaptive_output_tokens,
    build_reflection_cost_plane,
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


def _is_unsupported_param_error(exc: BaseException) -> bool:
    """Return True when the server rejects an unknown request field."""
    text = str(exc).lower()
    needles = (
        "reasoning_effort",
        "unexpected keyword",
        "unknown field",
        "unrecognized",
        "extra inputs",
        "invalid parameter",
    )
    return any(n in text for n in needles)


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
        cost_plane: ReflectionCostPlane | None = None,
        cost_profile: str = "balanced",
        stage_policies: dict | None = None,
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
        self.model_context_limit: int = model_context_limit
        self.timeout: float = timeout
        self.output_token_mode = OutputTokenMode(output_token_mode)
        self.reasoning_reserve = max(0, reasoning_reserve)
        self.tokenizer_fudge = max(1.0, tokenizer_fudge)
        self.chat_template_overhead = max(0, chat_template_overhead)
        self.domain_context_max_tokens = max(0, domain_context_max_tokens)

        self.cost_plane = cost_plane or build_reflection_cost_plane(
            cost_profile=cost_profile,
            reflection_enabled=reflection_enabled,
            stage_overrides=stage_policies,
        )
        self._reflection_enabled: bool = self.cost_plane.reflection_enabled

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
            profile = self._stage_policy("critique").prompt_profile
            profile_value = (
                profile.value if isinstance(profile, PromptProfile) else str(profile)
            )
            user_tokens = self.prompt_manager.measure(
                "critique",
                text=source_text,
                draft=draft_text,
                prompt_profile=profile_value,
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

    def _stage_policy(self, stage: str) -> StagePolicy:
        return self.cost_plane.stage(stage)

    def _effective_max_tokens(self, stage: str, source_text: str) -> int | None:
        if self.max_tokens is None:
            return None
        source_tokens = count_tokens(source_text, model_name=self.model)
        return adaptive_output_tokens(
            source_tokens,
            ceiling=self.max_tokens,
            policy=self._stage_policy(stage),
        )

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
        reserved = self._effective_max_tokens(stage, source_text)
        if reserved is None:
            reserved = 0
        return plan_token_budget(
            context_limit=self.model_context_limit,
            max_tokens=reserved,
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
    ) -> tuple[str, int]:
        """Return ``(context_block, pack_context_ms)`` under the measured budget."""
        t0 = time.perf_counter()
        if not context:
            return "", int((time.perf_counter() - t0) * 1000)

        backward: list[str] = []
        forward: list[str] = []
        if isinstance(context, dict):
            backward = list(context.get("backward", []))
            forward = list(context.get("forward", []))
        else:
            backward = list(context)

        if not backward and not forward:
            return "", int((time.perf_counter() - t0) * 1000)

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
            return "", int((time.perf_counter() - t0) * 1000)

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
        return block, int((time.perf_counter() - t0) * 1000)

    def _call_llm(
        self,
        model: str,
        messages: list[dict[str, str]],
        temperature: float,
        *,
        stage: str | None = None,
        source_text: str = "",
    ) -> LLMResponse:
        """Single LLM API call with the configured model and token settings."""
        total_prompt_tokens = sum(
            count_tokens(m["content"], model_name=model) for m in messages
        )
        effective_max = (
            self._effective_max_tokens(stage or "draft", source_text)
            if source_text
            else (self.max_tokens if self.max_tokens is not None else 0)
        )
        if effective_max is None:
            effective_max = 0
        ceiling = self.max_tokens if self.max_tokens is not None else effective_max
        stage_name = stage or "draft"
        thinking = self._stage_policy(stage_name).thinking
        thinking_forced_off = False
        starvation_bumped = False
        attempt = 1

        while True:
            self._assert_call_footprint(
                total_prompt_tokens=total_prompt_tokens,
                effective_max=effective_max,
            )
            active_thinking = ThinkingMode.OFF if thinking_forced_off else thinking
            try:
                res = self._invoke_chat_completion(
                    model=model,
                    messages=messages,
                    temperature=temperature,
                    effective_max=effective_max,
                    stage=stage,
                    thinking=active_thinking,
                )
            except OutputTokenStarvationError:
                if not thinking_forced_off and thinking != ThinkingMode.OFF:
                    thinking_forced_off = True
                    attempt += 1
                    logger.warning(
                        "Output token starvation stage=%s; retrying once with "
                        "thinking=off (retry_reason=thinking_disabled)",
                        stage,
                    )
                    continue
                if starvation_bumped or effective_max >= ceiling:
                    raise
                bump = (
                    max(self.reasoning_reserve, 512) if self.reasoning_reserve else 512
                )
                bumped = min(ceiling, max(effective_max * 2, effective_max + bump))
                if bumped <= effective_max:
                    raise
                logger.warning(
                    "Output token starvation stage=%s effective_max=%s; "
                    "retrying once with effective_max=%s (retry_reason=reasoning_budget)",
                    stage,
                    effective_max,
                    bumped,
                )
                effective_max = bumped
                starvation_bumped = True
                attempt += 1
                continue

            if thinking_forced_off:
                res.retry_reason = "thinking_disabled"
            elif starvation_bumped:
                res.retry_reason = "reasoning_budget"
            res.attempt = max(res.attempt or 1, attempt)
            return res

    def _assert_call_footprint(
        self, *, total_prompt_tokens: int, effective_max: int
    ) -> None:
        plan = plan_token_budget(
            context_limit=self.model_context_limit,
            max_tokens=effective_max,
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

    @staticmethod
    def _thinking_request_kwargs(thinking: ThinkingMode) -> dict[str, Any]:
        """Best-effort OpenAI-compatible extras for server thinking control."""
        if thinking == ThinkingMode.OFF:
            return {"reasoning_effort": "none"}
        if thinking == ThinkingMode.MINIMAL:
            return {"reasoning_effort": "low"}
        return {}

    def _invoke_chat_completion(
        self,
        *,
        model: str,
        messages: list[dict[str, str]],
        temperature: float,
        effective_max: int,
        stage: str | None,
        thinking: ThinkingMode = ThinkingMode.OFF,
    ) -> LLMResponse:
        kwargs: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "stream": True,
        }
        if effective_max:
            kwargs["max_tokens"] = effective_max
        kwargs.update(self._thinking_request_kwargs(thinking))

        max_attempts = self.retry_config.get("max_attempts", 3)
        min_wait = self.retry_config.get("min_wait_seconds", 2)
        max_wait = self.retry_config.get("max_wait_seconds", 60)
        attempt_number = 1

        for attempt in Retrying(
            wait=wait_exponential(multiplier=1, min=min_wait, max=max_wait),
            stop=stop_after_attempt(max_attempts),
            retry=retry_if_exception(_is_retryable),
            reraise=True,
            before_sleep=before_sleep_log(logger, logging.WARNING),
        ):
            with attempt:
                attempt_number = attempt.retry_state.attempt_number
                t0 = time.perf_counter()
                ttft_ms = None

                kwargs["stream_options"] = {"include_usage": True}
                try:
                    response = self.client.chat.completions.create(**kwargs)  # type: ignore
                except TypeError:
                    # Drop unsupported extras (stream_options and/or reasoning_effort).
                    kwargs.pop("stream_options", None)
                    if "reasoning_effort" in kwargs:
                        logger.debug(
                            "Provider rejected reasoning_effort; retrying without it"
                        )
                        kwargs.pop("reasoning_effort", None)
                    try:
                        response = self.client.chat.completions.create(**kwargs)  # type: ignore
                    except TypeError:
                        kwargs.pop("stream_options", None)
                        response = self.client.chat.completions.create(**kwargs)  # type: ignore
                except Exception as exc:
                    # Some servers return 400 for unknown fields instead of TypeError.
                    if "reasoning_effort" in kwargs and _is_unsupported_param_error(
                        exc
                    ):
                        logger.debug(
                            "Provider rejected reasoning_effort (%s); retrying without it",
                            exc,
                        )
                        kwargs.pop("reasoning_effort", None)
                        response = self.client.chat.completions.create(**kwargs)  # type: ignore
                    else:
                        raise

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
                    attempt=attempt_number,
                    retry_reason="http" if attempt_number > 1 else None,
                    effective_max_tokens=effective_max if effective_max else None,
                )

                if final_usage:
                    res.prompt_tokens = final_usage.prompt_tokens
                    res.completion_tokens = final_usage.completion_tokens
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
                    res.reasoning_tokens = reasoning_tokens
                    spent = max(res.completion_tokens or 0, reasoning_tokens)
                    if not res.text and spent > 0:
                        raise OutputTokenStarvationError(spent, stage=stage)
                else:
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

        context_block, pack_ms = self._build_context_block(
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
            source_text=text,
        )
        res.pack_context_ms = pack_ms
        res.text = validate_llm_output(res.text, source=text, stage="draft")
        return res

    def generate_critique(
        self, draft_text: str, source_text: str, context: ContextData | None = None
    ) -> LLMResponse:
        """Generate a critique of the given draft."""
        context_block, pack_ms = self._build_context_block(
            context,
            target_text=source_text,
            stage="critique",
            draft_text=draft_text,
        )
        current_system_prompt = self._render_system_prompt(context_block)
        prompt_profile = self._stage_policy("critique").prompt_profile
        if isinstance(prompt_profile, PromptProfile):
            prompt_profile_value = prompt_profile.value
        else:
            prompt_profile_value = str(prompt_profile)

        critique_prompt = self.prompt_manager.render(
            "critique",
            text=source_text,
            draft=draft_text,
            prompt_profile=prompt_profile_value,
        )

        res = self._call_llm(
            model=self.critique_model,
            messages=[
                {"role": "system", "content": current_system_prompt},
                {"role": "user", "content": critique_prompt},
            ],
            temperature=self.reflection_temperature,
            stage="critique",
            source_text=source_text,
        )
        res.pack_context_ms = pack_ms
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
        context_block, pack_ms = self._build_context_block(
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
            source_text=source_text,
        )
        res.pack_context_ms = pack_ms
        res.text = validate_llm_output(res.text, source=source_text, stage="refine")
        return res

    # (translate_segment_iter inherited from BaseLLMProvider)
