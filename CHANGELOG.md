# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

There is no tagged release yet. Everything below is on `main` under
**[Unreleased]** until the first Git tag (intended package line: 0.1.0).

## [Unreleased]

### Added

- Public beta of the LILT localization engine (sync, translate, build, review, TM, telemetry), still unreleased.
- Architecture L1 guides under `docs/architecture/`.
- CI via `make ci` (ruff, mypy, pytest).
- Provider-agnostic `plan_token_budget` / `pack_neighbor_context`, batch budget preflight, and config for `output_token_mode` / `tokenizer_fudge` / domain context caps.
- Translate preflight warns once when `project.domain_context` is empty (still optional).
- `plan_budget` on the LLM provider port; progress event TypedDicts; linguistic eligibility in `parser.linguistic`.

### Changed

- Evaluation corpus tooling and harnesses live outside this repository.
- CLI consolidated (`project configure --dry-run`, `tm list`/`status`/`admin`).
- Pre-test checklist in troubleshooting; L1 persistence documents that machine translate uses `SegmentPolicy` only (not `SegmentTransitionPolicy`).
- Default `llm.max_tokens` is `4096` so new workspaces keep headroom under `model_context_limit` (`8192`).
- Pre-test docs mark `project.domain_context` as highly recommended before serious runs.
- Domain errors no longer inherit Click; CLI adapts `LiltDomainError` at the edge.
- Workspace path sandbox lives on `WorkspaceContext`; `PipelineService` is a typed composition root (no monkey-patch facade).
- Removed dead `require_path_exists`; path sandbox SSOT is `WorkspaceContext.resolve_under_workspace`.
- Translate selects reflection strategy via `create_reflection_strategy` (removed `TranslatorPipeline` wrapper).
- Token budget/neighbor packing exposed as module functions; `EmptyLLMOutputError` / `ContextLengthExceededError` live in `exceptions.py`.
- `SegmentTransitionPolicy` matrix is human/CLI/import only (no machine mid-pipeline edges).
- Strategies import stage/budget helpers via `core.translation.reflection_runtime`.
- PDF compile lives in `PdfCompileService` (not inside build orchestrator).
- Human-edit validation raises `ValidationError` directly (no re-wrap that drops `attempt_text`).
- Empty-LLM progress events use `kind=llm` in workflow (aligned with sequential).
- Namespace derivation lives in `tm.namespace`; TM status cost estimates via `TMService`.
- Translate CLI uses public workspace APIs (no `_get_config` / `service.repo` privates).
- Docs label Terminology/Structure validators as Phase 3 (aligned with product context).

### Fixed

- Context budgeting now reserves completion tokens and chat overhead before packing neighbors (replacing the fixed 600-token heuristic).
- Empty LLM `content` with non-zero completion tokens raises `OutputTokenStarvationError` instead of blind retry.
- TM repair no longer blocked by strict load of corrupt namespaces; workspace path checks reject sibling-prefix escapes; namespace encoding collisions fail loudly at sync.
- Sequential runs keep successful segment writes when later segments hit empty LLM output or soft telemetry failures; import and build treat placeholder map drift correctly.
- Aggregate TM status/list soft-skip corrupt namespaces with repair hints; human edit writes validate like submit; checkpoint appends fsync; partial sync reports namespaces already written.
- Corrupt telemetry DB raises consistently on summary, stage breakdown, and workflow reads (missing file still soft-empty).
- Idle translation with leftover `drafted`/`critiqued` segments hints workflow stage resume or sequential `--force`.
- Placeholder validation reports count-only multiset mismatches (same tokens, different cardinality).
- Idle `--stage critique|refine` with no eligible segments hints `--stage draft [--force]` first; CLI/docs clarify that workflow `--force` expands draft only.
- Empty or null `lilt.yaml` raises `ConfigurationError` instead of applying silent full defaults.
- Non-empty critique output that is not valid JSON with `requires_refine` marks the segment `conflict` and does not run refine.
