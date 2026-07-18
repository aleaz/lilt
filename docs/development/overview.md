# Development overview

Also see [CONTRIBUTING.md](../../CONTRIBUTING.md) and [AGENTS.md](../../AGENTS.md).

### Install Dev Dependencies

```bash
uv sync
```

Dev group includes: `pytest`, `ruff`, `mypy`, `pytest-mock`, `pytest-cov`.

### Quality Commands

| Command | Description |
|---------|-------------|
| `make format` | Auto-format and fix with Ruff |
| `make lint` | Ruff check (no auto-fix) |
| `make typecheck` | Mypy strict on `src/` and `tests/` |
| `make test` | Run pytest |
| `make check-all` | format + lint + typecheck + test (may modify files) |
| `make ci` | Non-mutating CI check (matches GitHub Actions) |
| `make docs-sync-check` | Warn-only: `src/lilt/` changes without mapped docs (never fails CI) |

Path → docs matrix for agents: [`.cursor/rules/lilt-architecture.mdc`](../../.cursor/rules/lilt-architecture.mdc) (Documentation policy). Script: [`scripts/check-doc-sync.sh`](../../scripts/check-doc-sync.sh).

### Build Distributions

```bash
uv build
```

Produces wheel and sdist in `dist/`.

---
