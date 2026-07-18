# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-07-17

### Added

- Public beta of the LILT localization engine (sync, translate, build, review, TM, telemetry).
- Architecture L1 guides under `docs/architecture/`.
- CI via `make ci` (ruff, mypy, pytest).

### Changed

- Evaluation corpus tooling and harnesses live outside this repository.
- CLI consolidated (`project configure --dry-run`, `tm list`/`status`/`admin`).
