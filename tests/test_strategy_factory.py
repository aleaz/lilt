"""Tests for reflection strategy factory selection."""

from unittest.mock import MagicMock

from lilt.core.translation.sequential_strategy import SequentialReflectionStrategy
from lilt.core.translation.strategy_factory import create_reflection_strategy
from lilt.core.translation.workflow_strategy import WorkflowReflectionStrategy
from lilt.models.translation_mode import TranslationMode


def test_factory_selects_workflow():
    strategy = create_reflection_strategy(
        TranslationMode.WORKFLOW,
        MagicMock(),
        MagicMock(),
        3,
        MagicMock(),
    )
    assert isinstance(strategy, WorkflowReflectionStrategy)


def test_factory_selects_sequential():
    strategy = create_reflection_strategy(
        TranslationMode.SEQUENTIAL,
        MagicMock(),
        MagicMock(),
        3,
        MagicMock(),
    )
    assert isinstance(strategy, SequentialReflectionStrategy)
