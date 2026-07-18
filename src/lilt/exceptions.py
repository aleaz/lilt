"""Domain exceptions for LILT.

These types are raised by core, services, and CLI layers.
"""

import click


class LiltDomainError(click.ClickException):
    """Base exception for all domain logic errors in LILT."""

    def __init__(self, message: str):
        super().__init__(message)


class ProjectNotInitializedError(LiltDomainError):
    """Raised when the workspace does not contain a .lilt/lilt.yaml configuration."""

    def __init__(self, workspace_dir: str):
        super().__init__(
            f"Not initialized. Workspace '{workspace_dir}' lacks a .lilt/lilt.yaml config. Run 'lilt project init' first."
        )
        self.workspace_dir = workspace_dir


class NamespaceNotFoundError(LiltDomainError):
    """Raised when a specific namespace is not found in the Translation Memory."""

    def __init__(self, namespace: str):
        super().__init__(f"Namespace '{namespace}' not found in TM.")
        self.namespace = namespace


class SegmentNotFoundError(LiltDomainError):
    """Raised when a segment ID is not found in a namespace."""

    def __init__(self, segment_id: str, namespace: str):
        super().__init__(
            f"No segment found matching '{segment_id}' in namespace '{namespace}'."
        )
        self.segment_id = segment_id
        self.namespace = namespace


class MultipleSegmentsFoundError(LiltDomainError):
    """Raised when a segment ID prefix matches multiple segments."""

    def __init__(self, segment_id: str):
        super().__init__(
            f"Multiple segments match prefix '{segment_id}'. Please be more specific."
        )
        self.segment_id = segment_id


class InvalidStatusError(LiltDomainError):
    """Raised when an invalid segment status is provided."""

    def __init__(self, status: str, valid_options: str):
        super().__init__(
            f"Invalid status '{status}'. Valid options are: {valid_options}"
        )
        self.status = status


class BuildError(LiltDomainError):
    """Raised when the document fails to build."""

    pass


class TMImportError(LiltDomainError):
    """Raised when TM import fails. Named TMImportError to avoid shadowing the Python built-in."""

    pass


class ConfigurationError(LiltDomainError):
    """Raised when configuration loading or validation fails."""

    pass


class TranslationValidationError(LiltDomainError):
    """Raised when a human-edited translation fails structural validation."""

    def __init__(self, message: str):
        super().__init__(message)


class PreconditionError(LiltDomainError):
    """Raised when a workflow stage lacks required prior artifacts."""

    pass


class TMConcurrencyError(LiltDomainError):
    """Raised when TM file lock cannot be acquired after retries."""

    pass


class NamespaceBusyError(LiltDomainError):
    """Raised when a namespace session lock is already held by another operation."""

    def __init__(self, namespace: str):
        super().__init__(
            f"Namespace '{namespace}' is in use by another operation. "
            "Wait for it to finish and retry."
        )
        self.namespace = namespace


class TMCorruptionError(LiltDomainError):
    """Raised when TM JSONL contains unrecoverable corrupt lines."""

    def __init__(self, filepath: str, line_number: int, detail: str):
        super().__init__(f"Corrupt TM line {line_number} in '{filepath}': {detail}")
        self.filepath = filepath
        self.line_number = line_number


class TelemetryCorruptionError(LiltDomainError):
    """Raised when telemetry database cannot be read."""

    pass


class InvalidTransitionError(LiltDomainError):
    """Raised when a segment status transition is not allowed."""

    def __init__(self, from_status: str, to_status: str):
        super().__init__(f"Invalid status transition: {from_status} -> {to_status}")
        self.from_status = from_status
        self.to_status = to_status
