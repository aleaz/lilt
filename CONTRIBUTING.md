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

User-facing docs (getting started, guides, CLI/config reference, runbooks) live under [docs/README.md](docs/README.md). Update those when the operator-facing interface changes. Agents: follow the path → docs matrix in [`.cursor/rules/lilt-architecture.mdc`](.cursor/rules/lilt-architecture.mdc); optional warn-only check `make docs-sync-check`.

## 4. Pull Request Process

1. Ensure your code conforms to the style guides (`make check-all` or `make ci` must pass).
2. Update [docs/](docs/README.md) (and L1 guides when behavior changes) with details of interface or runtime changes, if applicable.
3. CI runs `make ci` via [`.github/workflows/ci.yml`](.github/workflows/ci.yml); verify locally before opening a PR.

## 5. Large-Scale Empirical Tests

If you run large-scale experiments on real books or papers, keep generated workspaces, PDFs, and campaign artifacts **outside** this repository (for example under a private sibling directory or a separate evaluation repo). Do not commit evaluation sandboxes, corpus downloads, or model traces here. This repository ships the localization engine and its unit/CLI tests only.

## 6. Optional: AI assistant setup

**Canonical AI context for this repo (versioned in git):**

| Tool | Location | Purpose |
| --- | --- | --- |
| **Any agent** | [`AGENTS.md`](AGENTS.md) | Short pointer to SSOT paths (Antigravity-friendly) |
| **Cursor** | [`.cursor/rules/lilt-architecture.mdc`](.cursor/rules/lilt-architecture.mdc) | Architecture and product-boundary invariants (always apply) |
| **Cursor** | [`.cursor/rules/lilt-git-agent.mdc`](.cursor/rules/lilt-git-agent.mdc) | Git for agents: no co-author trailers, no push unless asked |
| **Cursor** | [`.cursor/rules/lilt-parser-masking.mdc`](.cursor/rules/lilt-parser-masking.mdc) | Parser/placeholder integrity (when editing parser paths) |
| **Cursor** | [`.cursor/rules/lilt-tm-lifecycle.mdc`](.cursor/rules/lilt-tm-lifecycle.mdc) | TM statuses and human protection (when editing TM/sync) |
| **Cursor** | [`.cursor/skills/lilt-dev/SKILL.md`](.cursor/skills/lilt-dev/SKILL.md) | CLI workflows and pre-PR pointers |
| **Cursor** | [`.cursorignore`](.cursorignore) | Keep venv, `.lilt/`, PDFs, and caches out of agent context |

Use `.cursor/` as the single source of truth for Cursor and for human onboarding.
Do not rely on gitignored local paths (for example `.agents/`) for architecture rules.

Deep product documentation remains under [docs/](docs/README.md) (hub) and [docs/architecture/](docs/architecture/README.md) (L1 SSOT); the Cursor rules pin the path agents must follow without inventing CLI surface, corpus tooling, or ADRs.

**Optional — Antigravity / AG Kit (local only, not in git):**

- You may initialize a local AG Kit / Antigravity agent store on your machine (creates `.agents/`).
- Generic AG Kit skills and workflows are not curated for LILT; prefer `.cursor/` above.
- If you keep a local Antigravity memory file, keep it aligned with
  [`.cursor/rules/lilt-architecture.mdc`](.cursor/rules/lilt-architecture.mdc)
  (do not treat gitignored paths as the project source of truth).

### Maintaining AI context (anti-drift)

When architecture, product boundary, CLI surface, or CI validation commands change, update sources in this order:

1. Edit [`.cursor/rules/lilt-architecture.mdc`](.cursor/rules/lilt-architecture.mdc) — canonical source for agents and humans.
2. Keep [`.cursor/rules/lilt-git-agent.mdc`](.cursor/rules/lilt-git-agent.mdc) aligned if git agent policy changes.
3. Keep scoped rules ([parser](.cursor/rules/lilt-parser-masking.mdc), [TM](.cursor/rules/lilt-tm-lifecycle.mdc)) aligned when those domains change.
4. Update [`.cursor/skills/lilt-dev/SKILL.md`](.cursor/skills/lilt-dev/SKILL.md) only if it mentions the changed behavior explicitly.
5. Update [`AGENTS.md`](AGENTS.md) only if SSOT paths or hard stops change (keep it pointer-only).
6. Update this file and the PR template if the human checklist changes; update the matching L1 guide under `docs/architecture/` when runtime behavior changes; update [docs/reference/](docs/reference/cli.md) / guides when the operator CLI or config surface changes.
7. If you use Antigravity locally, sync any local memory file from step 1.

Do not add duplicate checklists to the skill — link to this file instead.
Do not add generic always-on Cursor rules (benchmark prompts, web-app templates); they contradict LILT invariants.
CI ([`.github/workflows/ci.yml`](.github/workflows/ci.yml)) is the objective final check; keep it aligned with the Testing and Standards section above.

If you do **not** use Antigravity, you can remove local AG Kit with `rm -rf .agents/ .temp_ag_kit` to reduce editor noise.
