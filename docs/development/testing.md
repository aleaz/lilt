# Testing

Index: [Developer Guide](README.md). Process: [contribution-workflow.md](contribution-workflow.md) · [CONTRIBUTING.md](../../CONTRIBUTING.md).

## Running tests

```bash
make test
# equivalent
uv run pytest
```

Useful filters:

```bash
uv run pytest tests/test_tm_repository.py -v
uv run pytest -k "workflow" -v
uv run pytest tests/test_cli_pipeline.py -q
```

`pytest-cov` is in the dev group; coverage is optional for local runs (not required by `make ci`). Prefer `make ci` for the gate that matches GitHub Actions.

## Test organization (`tests/`)

| Pattern | Category | Examples |
|---------|----------|----------|
| `test_*_parser*.py`, `test_validators.py`, `test_accuracy_gate.py` | Unit | Parser, validators, AccuracyGate |
| `test_tm_*.py`, `test_sync.py` | Integration | TM, sync, import/export |
| `test_e2e_pipeline.py`, `test_cli_*.py` | End-to-end / CLI | Full pipeline, Typer commands |
| `test_placeholder_persistence.py` | Integration | Masking roundtrip + workflow |
| `tests/release/` (`@pytest.mark.release`) | Release locks | RG-01 `tm status` counts, fail-closed build, idle conflicts, placeholder hints |

Config: `[tool.pytest.ini_options]` in [`pyproject.toml`](../../pyproject.toml) (`testpaths = ["tests"]`). Release locks run in default pytest / `make ci` (not excluded).

Filter release locks only:

```bash
uv run pytest -m release
```

## Release validation (pre-tag)

```bash
make release-validate
```

Runs `scripts/release/check-status-consistency.py`, `check-doc-links.sh`, and
`check-quickstart-structure.sh`. Maintainer strategy (gitignored):
`docs/internal/RELEASE_VALIDATION_STRATEGY.md`.

## CI parity

[`.github/workflows/ci.yml`](../../.github/workflows/ci.yml) runs **`make ci`** (ruff format --check, ruff check, mypy, pytest) on pushes/PRs to `main`/`master`.

Local mutating loop: `make check-all`. Local non-mutating gate: `make ci`.
Before a public RC: `make release-validate` plus the manual UX gate checklist.

## Product boundary

Large-scale empirical campaigns, corpora, and evaluation sandboxes stay **outside** this repository. Do not commit generated workspaces, PDF campaigns, or model traces here — [CONTRIBUTING.md](../../CONTRIBUTING.md) §5 and [architecture product boundary](../architecture/README.md).

This repo ships the localization engine and its unit/CLI tests only.

---
