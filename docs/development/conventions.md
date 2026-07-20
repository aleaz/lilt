# Engineering conventions

Index: [Developer Guide](README.md).

## Code style and typing

- **Formatter / linter:** [Ruff](https://docs.astral.sh/ruff/) — see `[tool.ruff]` in [`pyproject.toml`](../../pyproject.toml) (Google pydocstyle convention).
- **Types:** Mypy **strict** on `src/` and `tests/` — `[tool.mypy]` in `pyproject.toml`.
- Run `make format` / `make lint` / `make typecheck`, or the full gates in [overview](overview.md).

Do not paste full tool configs into PRs; change `pyproject.toml` when policy changes.

## Naming

| Thing | Canonical |
|-------|-----------|
| Import / CLI | `lilt` |
| PyPI / dist name | `latex-lilt` (not `pip install lilt`) |
| Segment statuses | Glossary + `SegmentStatus` — [00-glossary](../architecture/00-glossary.md) |
| Critique vs Review | Critique = LLM stage; Review = human — never synonymize |
| Package layout | `src/lilt/…` |

## Design principles (pointers)

Culture, named principles, hard invariants, and where code goes: [Philosophy & invariants](README.md#philosophy--invariants) (start at [engineering-philosophy.md](engineering-philosophy.md)). Domain naming: [language-guidelines.md](language-guidelines.md) + [glossary](../architecture/00-glossary.md). Do not duplicate those packs here.

- Layering and domain Behavior: [Architecture README](../architecture/README.md) + L1 guides.
- Composition: CLI thin; services orchestrate; `WorkspaceContext` is the wiring root — [project layout](project-layout.md).
- Human-protected statuses never auto-overwritten — L1-02 / glossary.
- Prefer link-to-canonical over copying L1 into README or this handbook.

## Documentation conventions

| Change | Update in the same PR |
|--------|------------------------|
| Typer command / flag | [docs/reference/cli.md](../reference/cli.md) + AGENTS/rules/skill mirrors |
| `LiltConfig` / yaml keys | [docs/reference/config.md](../reference/config.md) |
| Domain contract / behavior | Matching L1 Behavior / Decisions / Known gaps |
| New ubiquitous term | [00-glossary](../architecture/00-glossary.md) first |

- **No** `docs/adrs/` — Decisions live in L1 / appendix-deferred.
- Optional warn-only: `make docs-sync-check`.
- Matrix: [`.cursor/rules/lilt-architecture.mdc`](../../.cursor/rules/lilt-architecture.mdc).

## Git (agents and humans)

Follow [`.cursor/rules/lilt-git-agent.mdc`](../../.cursor/rules/lilt-git-agent.mdc): commit/push/PR only when asked; no co-author trailers unless requested.

## Known limitations and debt

- Deferred features (plugins, multi-lang layout, Phase 3 validators, etc.): [appendix-deferred](../architecture/appendix-deferred.md).
- Product boundary (no corpus/eval in this repo): [architecture README](../architecture/README.md).
- Public beta: CLI/config may change until an intentional release — [CHANGELOG](../../CHANGELOG.md).

Do not document deferred items as shipped.

---
