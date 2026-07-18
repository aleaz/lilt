"""Jinja2 prompt template loading and rendering for LLM workflow stages."""

import hashlib
import logging
import os
from pathlib import Path
from typing import Any

from jinja2 import BaseLoader, ChoiceLoader, Environment, FileSystemLoader

from lilt.exceptions import ConfigurationError
from lilt.utils.token_utils import count_tokens

logger = logging.getLogger(__name__)


class PromptManager:
    """Manages loading and rendering of Jinja2 prompts for the LLM."""

    def __init__(self, override_dir: str | None = None):
        self.override_dir = override_dir
        if override_dir is not None and not os.path.isdir(override_dir):
            raise ConfigurationError(
                f"Configured prompt_dir is not a directory: {override_dir}"
            )

        # Built-in prompts package directory
        self.builtin_dir = Path(__file__).parent.parent / "prompts"

        self.env = self._create_env()

    def _create_env(self) -> Environment:
        """Create a Jinja2 Environment with the correct loader hierarchy."""
        loaders: list[BaseLoader] = []

        if self.override_dir and os.path.isdir(self.override_dir):
            loaders.append(FileSystemLoader(self.override_dir))

        if self.builtin_dir.is_dir():
            loaders.append(FileSystemLoader(str(self.builtin_dir)))
        else:
            logger.warning(f"Built-in prompt directory not found: {self.builtin_dir}")

        return Environment(loader=ChoiceLoader(loaders), autoescape=False)

    def render(self, template_name: str, **kwargs: Any) -> str:
        """Render a specific template by name (without .jinja extension)."""
        filename = f"{template_name}.jinja"
        try:
            template = self.env.get_template(filename)
            return template.render(**kwargs).strip()
        except Exception as e:
            logger.error(f"Failed to load or render template {filename}: {e}")
            raise

    def measure(self, template_name: str, **kwargs: Any) -> int:
        """Return tiktoken count for a rendered template."""
        return count_tokens(self.render(template_name, **kwargs))

    def _resolve_template_source(self, template_name: str) -> str:
        filename = f"{template_name}.jinja"
        source, _, _ = self.env.loader.get_source(self.env, filename)  # type: ignore[union-attr]
        return source

    def get_template_hash(self, template_name: str) -> str:
        """Return a short content-based hash of a template for telemetry versioning.

        Computes SHA-256 of the resolved template source (following the same loader
        priority as render()), returning the first 8 hex characters. Cached per
        process to avoid redundant I/O across pipeline stages.

        Args:
            template_name: Template name without the .jinja extension.

        Returns:
            A string like ``"draft:a3f2e1b4"`` or ``"unknown"`` if the template
            cannot be resolved.
        """
        filename = f"{template_name}.jinja"
        try:
            source = self._resolve_template_source(template_name)
            digest = hashlib.sha256(source.encode()).hexdigest()[:8]
            return f"{template_name}:{digest}"
        except Exception as e:
            logger.error(f"Failed to resolve template {filename}: {e}")
            return "unknown"
