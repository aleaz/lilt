# AGENTS.md — LILT

Pointer file for AI coding agents (Cursor, Antigravity, and others).
**Do not treat this file as a full architecture dump.**

## Source of truth

1. Always-on invariants: [`.cursor/rules/lilt-architecture.mdc`](.cursor/rules/lilt-architecture.mdc)
2. Git discipline: [`.cursor/rules/lilt-git-agent.mdc`](.cursor/rules/lilt-git-agent.mdc)
3. Documentation hub: [`docs/README.md`](docs/README.md)
4. Deep product docs (L1): [`docs/architecture/README.md`](docs/architecture/README.md)
5. Canonical vocabulary: [`docs/architecture/00-glossary.md`](docs/architecture/00-glossary.md) (redirect: [`docs/glossary.md`](docs/glossary.md))
6. Naming / terminology rules: [`docs/development/language-guidelines.md`](docs/development/language-guidelines.md)
7. Dev lifecycle skill: [`.cursor/skills/lilt-dev/SKILL.md`](.cursor/skills/lilt-dev/SKILL.md)

Scoped rules (auto when editing those paths):

- Parser/masking: [`.cursor/rules/lilt-parser-masking.mdc`](.cursor/rules/lilt-parser-masking.mdc)
- TM lifecycle: [`.cursor/rules/lilt-tm-lifecycle.mdc`](.cursor/rules/lilt-tm-lifecycle.mdc)

Human process: [`CONTRIBUTING.md`](CONTRIBUTING.md).

## Hard stops

- Do **not** reintroduce `corpus/`, `tools/corpus/`, `evaluation/`, `lilt corpus`, or `project evaluate`.
- Do **not** invent CLI commands outside `project` / `pipeline` / `tm` / `telemetry` (see [docs/reference/cli.md](docs/reference/cli.md)).
- Do **not** restore `docs/adrs/` — decisions live in L1 guides.
- Prefer `make ci` before considering a change done.
- Doc sync (path → which guide/reference to update) lives in [`.cursor/rules/lilt-architecture.mdc`](.cursor/rules/lilt-architecture.mdc) (Documentation policy / matrix). Optional: `make docs-sync-check`.

## Local Antigravity

If you use a local `.agents/` store, keep it aligned with `.cursor/rules/` — never treat gitignored agent memory as project SSOT.
