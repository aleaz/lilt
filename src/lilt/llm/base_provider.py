"""Base LLM provider with shared reflection and validation orchestration."""

import logging
from collections.abc import Iterable

from lilt.llm.output_gate import validate_llm_output
from lilt.llm.provider import ContextData, LLMProvider
from lilt.llm.reflection_pass import (
    run_reflection_pass,
    validation_retries_for_source,
)
from lilt.utils.text_utils import has_linguistic_content

logger = logging.getLogger(__name__)


class BaseLLMProvider(LLMProvider):
    """Base class for LLM Providers implementing the unified translate_segment_iter.

    This allows SequentialReflectionStrategy to execute the translation loop
    by automatically calling generate_draft, generate_critique, and generate_refine
    across ANY provider (OpenAI, Router, etc).
    """

    @property
    def reflection_enabled(self) -> bool:
        """Subclasses should override this to control if critique/refine run."""
        return True

    def get_prompt_version(self, stage: str) -> str:
        """Return a content-hash-based version string for the given pipeline stage.

        Delegates to ``self.prompt_manager.get_template_hash(stage)`` if the subclass
        exposes a ``prompt_manager`` attribute (as OpenAIProvider does). Falls back to
        ``"<stage>:unknown"`` for providers that don't use Jinja2 templates.
        """
        pm = getattr(self, "prompt_manager", None)
        if pm is not None and hasattr(pm, "get_template_hash"):
            return str(pm.get_template_hash(stage))
        return f"{stage}:unknown"

    def stage_model_name(self, stage: str) -> str:
        """Return the model name used for a workflow stage or sequential pass."""
        if stage == "sequential":
            return self.stage_model_name("draft")
        stage_attr = f"{stage}_model"
        return getattr(self, stage_attr, getattr(self, "model", "unknown"))

    def translate_segment_iter(
        self, text: str, context: ContextData | None = None
    ) -> Iterable[dict]:
        """Translate *text* using the configured LLM provider, yielding progress events."""
        if not has_linguistic_content(text):
            yield {"type": "status", "message": "Bypassing (No linguistic content)"}
            yield {
                "type": "result",
                "text": text,
                "meta": {"used": True, "draft_accepted": True, "bypass": True},
            }
            return

        yield {"type": "status", "message": "Drafting"}
        pass_result = run_reflection_pass(
            self,
            text,
            context,
            max_validation_retries=validation_retries_for_source(text),
        )

        if pass_result.critique is not None:
            yield {"type": "status", "message": "Critiquing"}
        if pass_result.refine is not None:
            yield {"type": "status", "message": "Refining"}

        yield {
            "type": "result",
            "text": validate_llm_output(
                pass_result.text, source=text, stage="sequential"
            ),
            "meta": pass_result.meta,
        }
