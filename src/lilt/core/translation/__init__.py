"""Translation engine: strategies, context resolution, and pipeline orchestration."""

from lilt.core.translation.context_resolver import ContextResolver
from lilt.core.translation.pipeline import TranslatorPipeline
from lilt.core.translation.protocols import ReflectionStrategy
from lilt.core.translation.sequential_strategy import SequentialReflectionStrategy
from lilt.core.translation.workflow_strategy import WorkflowReflectionStrategy

__all__ = [
    "ContextResolver",
    "ReflectionStrategy",
    "SequentialReflectionStrategy",
    "TranslatorPipeline",
    "WorkflowReflectionStrategy",
]
