# Development overview

Also see the [Developer Guide index](README.md), [CONTRIBUTING.md](../../CONTRIBUTING.md), and [AGENTS.md](../../AGENTS.md).

## Prerequisites

- **Python 3.13+**
- **[`uv`](https://docs.astral.sh/uv/)** for sync, run, and build

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh   # if needed
git clone https://github.com/aleaz/lilt
cd lilt
```

## Install development dependencies

```bash
uv sync
```

Dev group includes: `pytest`, `ruff`, `mypy`, `pytest-mock`, `pytest-cov`.

The package is installed editable via `uv sync`. Run the CLI from the workspace:

```bash
uv run lilt --version
uv run lilt -C /path/to/latex-project pipeline sync main.tex
```

IDE tip: point the interpreter at `.venv` (`source .venv/bin/activate` if you prefer an activated shell).

## Quality commands

| Command | Description |
|---------|-------------|
| `make format` | Auto-format and fix with Ruff |
| `make lint` | Ruff check (no auto-fix) |
| `make typecheck` | Mypy strict on `src/` and `tests/` |
| `make test` | Run pytest |
| `make check-all` | format + lint + typecheck + test (**may modify** files) |
| `make ci` | Non-mutating gate matching GitHub Actions |
| `make docs-sync-check` | Warn-only: `src/lilt/` changes without mapped docs (never fails CI) |

Use **`make ci`** before opening a PR (same as CI). Use **`make check-all`** when you want local auto-format/fix first.

Path → docs matrix: [`.cursor/rules/lilt-architecture.mdc`](../../.cursor/rules/lilt-architecture.mdc). Script: [`scripts/check-doc-sync.sh`](../../scripts/check-doc-sync.sh).

## Debugging

| Technique | How |
|-----------|-----|
| CLI debug log | `lilt --debug …` → stdout + `.lilt/lilt.log` under the workspace (`-C`) |
| Single test file | `uv run pytest tests/test_tm_repository.py -v` |
| Keyword filter | `uv run pytest -k "workflow" -v` |
| Narrow failure | Re-run the failing node id from pytest output |

Domain errors surface through `lilt.exceptions` and thin CLI adapters — service/CLI invariants: [07-cli-application](../architecture/07-cli-application.md). Do not invent new top-level exception hierarchies without updating L1.

## Logging and telemetry

- Operator/debug logging: `--debug` / `.lilt/lilt.log`.
- Inference telemetry (tokens, stages): SQLite under `.lilt/telemetry.db` — [08-observability](../architecture/08-observability.md), `lilt telemetry show`.

## Packaging

```bash
uv build
```

Produces wheel and sdist in `dist/`. Distribution name is **`latex-lilt`**; import/CLI name is **`lilt`**.

## Release and versioning (honest)

- Version lives in [`pyproject.toml`](../../pyproject.toml) (currently `0.1.0` public beta).
- [CHANGELOG.md](../../CHANGELOG.md) uses **Unreleased** until the maintainer cuts an **intentional** tag.
- Do not invent release theater (fake tags, “approaching 1.0”) in docs or CI.
- When cutting a release: update CHANGELOG, confirm [SECURITY.md](../../SECURITY.md) supported-versions lines, then tag deliberately.

## Docs sync when code changes

1. Map paths via the architecture rule matrix.  
2. Update L1 Behavior / Known gaps and/or [CLI](../reference/cli.md) / [config](../reference/config.md) in the **same** change set.  
3. Optionally run `make docs-sync-check` (warn-only).  
4. State `Docs updated: …` or `Docs N/A: …` in the PR / reply.

---
