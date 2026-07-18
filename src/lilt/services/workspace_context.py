"""Shared workspace dependencies for service-layer composition."""

import os
from dataclasses import dataclass, field
from pathlib import Path

from lilt.services.preconditions import WorkspacePreconditions
from lilt.telemetry.service import TelemetryService
from lilt.tm.repository import TMRepository


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

    @classmethod
    def from_workspace(cls, workspace_dir: str) -> "WorkspaceContext":
        """Create a context rooted at the given workspace directory."""
        abs_workspace = os.path.abspath(workspace_dir)
        lilt_dir = os.path.join(abs_workspace, ".lilt")
        tm_dir = os.path.join(lilt_dir, "tm")
        return cls(
            workspace_dir=abs_workspace,
            lilt_dir=lilt_dir,
            config_path=os.path.join(lilt_dir, "lilt.yaml"),
            tm_dir=tm_dir,
            repo=TMRepository(base_dir=tm_dir),
        )
