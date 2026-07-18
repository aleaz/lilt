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

### Changed

- Evaluation corpus tooling and harnesses live outside this repository.
- CLI consolidated (`project configure --dry-run`, `tm list`/`status`/`admin`).

### Fixed

- TM repair no longer blocked by strict load of corrupt namespaces; workspace path checks reject sibling-prefix escapes; namespace encoding collisions fail loudly at sync.
- Sequential runs keep successful segment writes when later segments hit empty LLM output or soft telemetry failures; import and build treat placeholder map drift correctly.
- Aggregate TM status/list soft-skip corrupt namespaces with repair hints; human edit writes validate like submit; checkpoint appends fsync; partial sync reports namespaces already written.
- Corrupt telemetry DB raises consistently on summary, stage breakdown, and workflow reads (missing file still soft-empty).
- Idle translation with leftover `drafted`/`critiqued` segments hints workflow stage resume or sequential `--force`.
- Placeholder validation reports count-only multiset mismatches (same tokens, different cardinality).
