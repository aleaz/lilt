"""Workspace and namespace preconditions for service-layer operations."""

import os

from lilt.exceptions import (
    NamespaceNotFoundError,
    ProjectNotInitializedError,
)
from lilt.models.config import LiltConfig
from lilt.tm.repository import TMRepository
from lilt.utils.config_loader import load_lilt_config
from lilt.utils.path_utils import path_is_under_workspace


class WorkspacePreconditions:
    """Centralized guards before pipeline and TM operations."""

    def __init__(
        self,
        workspace_dir: str,
        config_path: str,
        tm_dir: str,
        repo: TMRepository,
    ) -> None:
        self.workspace_dir = workspace_dir
        self.config_path = config_path
        self.tm_dir = tm_dir
        self.repo = repo

    def require_initialized(self) -> None:
        """Raise if the workspace has no lilt.yaml."""
        if not os.path.exists(self.config_path):
            raise ProjectNotInitializedError(self.workspace_dir)

    def load_config(self) -> LiltConfig:
        """Load validated configuration after initialization check."""
        self.require_initialized()
        return load_lilt_config(self.config_path)

    def require_namespace_file_exists(self, namespace: str) -> None:
        """Raise if the namespace JSONL file is missing (does not load contents)."""
        namespace_path = os.path.join(self.tm_dir, f"{namespace}.jsonl")
        if not os.path.exists(namespace_path):
            raise NamespaceNotFoundError(namespace)

    def require_namespace(self, namespace: str) -> None:
        """Raise if the namespace JSONL file does not exist or is empty."""
        self.require_namespace_file_exists(namespace)
        segments = self.repo.load_namespace(namespace)
        if not segments:
            raise NamespaceNotFoundError(namespace)

    def require_path_exists(self, path: str) -> str:
        """Resolve path within workspace and ensure it exists."""
        abs_path = os.path.abspath(
            path if os.path.isabs(path) else os.path.join(self.workspace_dir, path)
        )
        real_path = os.path.realpath(abs_path)
        real_workspace = os.path.realpath(self.workspace_dir)
        if not path_is_under_workspace(real_path, real_workspace):
            raise ValueError(
                f"Security Error: Path '{path}' attempts to traverse outside the workspace sandbox."
            )
        if not os.path.exists(real_path):
            raise FileNotFoundError(f"Path '{path}' not found.")
        return abs_path
