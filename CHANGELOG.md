# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

There is no tagged Git release yet. Everything below is on `main` under
**[Unreleased]** (package line: 0.1.0; distribution name: `latex-lilt`).

## [Unreleased]

### Added

- Public beta of the LILT localization engine (sync, translate, build, review, TM, telemetry).
- Architecture L1 guides under `docs/architecture/`.
- CI via `make ci` (ruff, mypy, pytest).
- Provider-agnostic `plan_token_budget` / `pack_neighbor_context`, batch budget preflight, and config for `output_token_mode` / `tokenizer_fudge` / domain context caps.
- Translate preflight warns once when `project.domain_context` is empty (still optional).
- `plan_budget` on the LLM provider port; progress event TypedDicts; linguistic eligibility in `parser.linguistic`.
- Dual-gate critique: deterministic `AccuracyGate` + resilient critique JSON parse/degrade (placeholder quotes).
- Post-sync context capacity SSOT (`llm/context_recommend.py`) + `lilt tm budget`.
- Per-stage `StagePolicy.thinking` (`off`/`on`/`minimal`) with best-effort `reasoning_effort` request hints; starvation retry can force thinking off.
- Telemetry persists `reasoning_tokens` when the provider reports them.
- `lilt --version` from installed package metadata.
- Community health: `SUPPORT.md`, issue template chooser links, OSS readiness docs (disclaimer vs Lilt Inc.).

### Changed

- Packaging project name is `latex-lilt` (import package and CLI stay `lilt`).
- Balanced StagePolicy output floors raised for thinking models (draft/refine 1536, critique 1024); starvation retries: optional `thinking_disabled` then `reasoning_budget` bump.
- Docs: capacity tiers (incl. 24GB+MoE), content vs server-thinking contract, `reasoned_gate` ≠ Enable Thinking; runbook performance expanded.
- Docs recommend matching `model_context_limit` to serving n_ctx (e.g. 32768) for reflection with neighbor paragraphs; 8k is smoke/microbench only.
- Placeholder ACCURACY checklist strengthened in system/critique/refine prompts; critique prompt focuses on editorial axes (AccuracyGate owns placeholders).
- `adaptive_output_tokens` never returns above `max_tokens` ceiling; strict profile uses thinking-safe floors.
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
- Maturity wording: honest 0.x public beta (not “approaching 1.0”).

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
