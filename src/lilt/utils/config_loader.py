"""Load and validate workspace configuration into typed models."""

from typing import Any

from lilt.exceptions import ConfigurationError
from lilt.models.config import LiltConfig
from lilt.utils.yaml_loader import load_yaml_config


def _ensure_mapping_root(data: Any, *, path: str) -> dict[str, Any]:
    if data is None:
        return {}
    if not isinstance(data, dict):
        raise ConfigurationError(
            f"Configuration root in '{path}' must be a mapping, got {type(data).__name__}."
        )
    return data


def _validate_llm_block(raw: dict[str, Any], *, path: str) -> None:
    if "llm" not in raw:
        return
    llm_block = raw["llm"]
    if llm_block is not None and not isinstance(llm_block, dict):
        raise ConfigurationError(
            f"'llm' in '{path}' must be a mapping, got {type(llm_block).__name__}."
        )


def load_lilt_config(config_path: str) -> LiltConfig:
    """Load lilt.yaml with syntax and semantic validation.

    Raises:
        ConfigurationError: On invalid YAML, non-mapping root, or schema errors.
    """
    raw = load_yaml_config(config_path)
    root = _ensure_mapping_root(raw, path=config_path)
    _validate_llm_block(root, path=config_path)
    try:
        return LiltConfig.model_validate(root)
    except Exception as exc:
        raise ConfigurationError(
            f"Invalid configuration in '{config_path}': {exc}"
        ) from exc
