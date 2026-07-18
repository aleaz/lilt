# Contributing to LILT

First off, thank you for considering contributing to `lilt`! It's people like you that make open source such a fantastic community.

## 1. Development Environment

This project strictly uses `uv` for dependency management and Python toolchains.
Ensure you have `uv` installed (`curl -LsSf https://astral.sh/uv/install.sh | sh`).

1. Clone the repository: `git clone https://github.com/aleaz/lilt`
2. Sync the environment: `uv sync`
3. Activate the virtual environment (if needed by your IDE): `source .venv/bin/activate`

## 2. Testing and Standards

We strictly enforce formatting, linting, and static typing.

Before submitting a Pull Request, you **must** run our QA checks locally:

```bash
make check-all
```

This will automatically format your code (`ruff format`), lint it (`ruff check`), run strict static type checking (`mypy`), and execute all unit tests (`pytest`). `check-all` may modify files in place (format and auto-fix).

For a **non-mutating** check that matches CI (no auto-format or auto-fix), run:

```bash
make ci
```

GitHub Actions runs `make ci` on every push to `main`/`master` and on pull requests (see [`.github/workflows/ci.yml`](.github/workflows/ci.yml)).

## 3. Architecture Guides

Significant architectural changes (TM schema, masking taxonomy, new core commands) must be documented in the relevant guide under `docs/architecture/`. Read [docs/architecture/README.md](docs/architecture/README.md) before proposing major design changes.

## 4. Pull Request Process

1. Ensure your code conforms to the style guides (`make check-all` or `make ci` must pass).
2. Update the README.md or docs with details of changes to the interface, if applicable.
3. CI runs `make ci` via [`.github/workflows/ci.yml`](.github/workflows/ci.yml); verify locally before opening a PR.

## 5. Large-Scale Empirical Tests

If you run large-scale experiments on real books or papers, keep generated workspaces, PDFs, and campaign artifacts **outside** this repository (for example under a private sibling directory or a separate evaluation repo). Do not commit evaluation sandboxes, corpus downloads, or model traces here. This repository ships the localization engine and its unit/CLI tests only.
