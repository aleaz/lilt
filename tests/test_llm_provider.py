from unittest.mock import MagicMock

from lilt.llm.base_provider import BaseLLMProvider
from lilt.llm.router_provider import RouterLLMProvider


class _SingleModelProvider(BaseLLMProvider):
    def __init__(self, model: str) -> None:
        self.model = model

    def generate_draft(self, text, context=None):
        raise NotImplementedError

    def generate_critique(self, draft_text, source_text, context=None):
        raise NotImplementedError

    def generate_refine(self, draft_text, critique_text, source_text, context=None):
        raise NotImplementedError


def test_stage_model_name_for_single_model_provider():
    provider = _SingleModelProvider("gpt-4o")

    assert provider.stage_model_name("draft") == "gpt-4o"
    assert provider.stage_model_name("critique") == "gpt-4o"
    assert provider.stage_model_name("refine") == "gpt-4o"
    assert provider.stage_model_name("sequential") == "gpt-4o"


class _PerStageModelProvider(_SingleModelProvider):
    def __init__(self) -> None:
        super().__init__("default")
        self.draft_model = "local-draft"
        self.critique_model = "cloud-critique"
        self.refine_model = "cloud-refine"


def test_stage_model_name_for_per_stage_models():
    provider = _PerStageModelProvider()

    assert provider.stage_model_name("draft") == "local-draft"
    assert provider.stage_model_name("critique") == "cloud-critique"
    assert provider.stage_model_name("refine") == "cloud-refine"


def test_stage_model_name_for_router_delegates_to_stage_provider():
    draft = MagicMock()
    draft.draft_model = "local-draft"
    critique = MagicMock()
    critique.critique_model = "cloud-critique"
    refine = MagicMock()
    refine.refine_model = "cloud-refine"
    router = RouterLLMProvider(draft, critique, refine)

    assert router.stage_model_name("draft") == "local-draft"
    assert router.stage_model_name("critique") == "cloud-critique"
    assert router.stage_model_name("refine") == "cloud-refine"
    assert router.stage_model_name("sequential") == "local-draft"


def test_router_get_prompt_version_maps_sequential_to_draft():
    draft = MagicMock()
    draft.get_prompt_version.return_value = "draft:abc12345"
    critique = MagicMock()
    refine = MagicMock()
    router = RouterLLMProvider(draft, critique, refine)

    assert router.get_prompt_version("sequential") == "draft:abc12345"
    draft.get_prompt_version.assert_called_once_with("draft")
