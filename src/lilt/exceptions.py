"""Domain exceptions for LILT.

These types are raised by core, services, and CLI layers.
The CLI presentation layer maps them to user-facing output; they do not
inherit from Click or Typer types.
"""


class LiltDomainError(Exception):
    """Base exception for all domain logic errors in LILT."""

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


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
    """Raised when a translation fails structural or placeholder validation."""

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


class OutputTokenStarvationError(LiltDomainError):
    """Raised when the model spent completion tokens but returned empty content.

    Typical with thinking/reasoning models when ``max_tokens`` is consumed by
    internal reasoning and ``message.content`` stays empty. The provider may
    retry once with a larger ``effective_max_tokens`` (up to ``max_tokens``);
    if content is still empty, raise ``max_tokens`` or use ``split_budget`` +
    ``reasoning_reserve``, or disable thinking for that stage.
    """

    def __init__(self, completion_tokens: int, stage: str | None = None):
        stage_bit = f" during {stage}" if stage else ""
        super().__init__(
            f"LLM returned empty content{stage_bit} after using "
            f"{completion_tokens} completion token(s). The serving stack likely "
            "spent the output budget on reasoning/thinking. Increase "
            "llm.max_tokens, use output_token_mode=split_budget with "
            "reasoning_reserve, set stage_policies.<stage>.thinking to off, "
            "or disable thinking on the serving stack for this stage."
        )
        self.completion_tokens = completion_tokens
        self.stage = stage


class BudgetPreflightError(LiltDomainError):
    """Raised when token budget preflight proves a batch is infeasible."""

    pass


class WorkspacePathError(LiltDomainError):
    """Raised when a path escapes the workspace sandbox."""

    def __init__(self, input_path: str):
        super().__init__(
            f"Security Error: Path '{input_path}' attempts to traverse outside "
            "the workspace sandbox."
        )
        self.input_path = input_path


class EmptyLLMOutputError(LiltDomainError):
    """Raised when the LLM returns empty text for linguistic source content."""

    def __init__(self, stage: str) -> None:
        super().__init__(
            f"LLM returned empty output during '{stage}' for translatable content."
        )
        self.stage = stage


class ContextLengthExceededError(LiltDomainError):
    """Raised when prompt plus reserved output exceeds the model context limit."""

    pass
