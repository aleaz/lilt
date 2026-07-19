"""Shared workspace dependencies for service-layer composition."""

import os
from dataclasses import dataclass, field
from pathlib import Path

from lilt.exceptions import WorkspacePathError
from lilt.services.preconditions import WorkspacePreconditions
from lilt.telemetry.service import TelemetryService
from lilt.tm.repository import TMRepository
from lilt.utils.path_utils import path_is_under_workspace


@dataclass
class WorkspaceContext:
    """Holds workspace paths and shared persistence for all services."""

    workspace_dir: str
    lilt_dir: str
    config_path: str
    tm_dir: str
    repo: TMRepository
    _telemetry: TelemetryService | None = field(default=None, repr=False)
    _preconditions: WorkspacePreconditions | None = field(default=None, repr=False)

    @property
    def telemetry_db_path(self) -> Path:
        """Path to the workspace SQLite telemetry database."""
        return Path(self.lilt_dir) / "telemetry.db"

    @property
    def preconditions(self) -> WorkspacePreconditions:
        """Lazy workspace precondition guards."""
        if self._preconditions is None:
            self._preconditions = WorkspacePreconditions(
                self.workspace_dir,
                self.config_path,
                self.tm_dir,
                self.repo,
            )
        return self._preconditions

    @property
    def telemetry(self) -> TelemetryService:
        """Lazy singleton telemetry service for this workspace."""
        if self._telemetry is None:
            self._telemetry = TelemetryService(self.telemetry_db_path)
        return self._telemetry

    def resolve_under_workspace(self, input_path: str) -> str:
        """Resolve ``input_path`` and ensure it stays inside the workspace sandbox."""
        abs_path = os.path.abspath(
            input_path
            if os.path.isabs(input_path)
            else os.path.join(self.workspace_dir, input_path)
        )
        real_path = os.path.realpath(abs_path)
        real_workspace = os.path.realpath(self.workspace_dir)
        if not path_is_under_workspace(real_path, real_workspace):
            raise WorkspacePathError(input_path)
        return abs_path

    @classmethod
    def from_workspace(cls, workspace_dir: str) -> "WorkspaceContext":
        """Create a context rooted at the given workspace directory."""
        abs_workspace = os.path.abspath(workspace_dir)
        lilt_dir = os.path.join(abs_workspace, ".lilt")
        tm_dir = os.path.join(lilt_dir, "tm")
        durability = "strict"
        config_path = os.path.join(lilt_dir, "lilt.yaml")
        if os.path.isfile(config_path):
            try:
                from lilt.utils.yaml_loader import load_yaml_config

                raw = load_yaml_config(config_path)
                durability = str(raw.get("tm", {}).get("durability", "strict"))
            except Exception:
                durability = "strict"
        return cls(
            workspace_dir=abs_workspace,
            lilt_dir=lilt_dir,
            config_path=config_path,
            tm_dir=tm_dir,
            repo=TMRepository(base_dir=tm_dir, durability=durability),
        )
