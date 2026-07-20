# Contributing to LILT

Thank you for considering a contribution.

**Start here:** [Contributor Guide](docs/development/contributor-guide.md) — expectations, setup pointers, contribution types, and how to avoid common mistakes.

| Need | Document |
|------|----------|
| End-to-end process (branch → PR → release honesty) | [Contribution workflow](docs/development/contribution-workflow.md) |
| Author self-check | [Pull request checklist](docs/development/pull-request-checklist.md) |
| What reviewers verify | [Code review guidelines](docs/development/code-review-guidelines.md) |
| AI-assisted PRs | [AI contribution guidelines](docs/development/ai-contribution-guidelines.md) |
| Engineering handbook (setup, layout, tests, philosophy) | [docs/development/README.md](docs/development/README.md) |

## Quick start

1. Install [`uv`](https://docs.astral.sh/uv/) (`curl -LsSf https://astral.sh/uv/install.sh | sh`).
2. `git clone https://github.com/aleaz/lilt` → `uv sync` → optional `source .venv/bin/activate`.
3. Before a PR: run **`make ci`** (matches [`.github/workflows/ci.yml`](.github/workflows/ci.yml)). Local auto-format/fix first: `make check-all`.

Detail: [docs/development/overview.md](docs/development/overview.md).

## Large-scale empirical tests

If you run large-scale experiments on real books or papers, keep generated workspaces, PDFs, and campaign artifacts **outside** this repository (for example under a private sibling directory or a separate evaluation repo). Do not commit evaluation sandboxes, corpus downloads, or model traces here. This repository ships the localization engine and its unit/CLI tests only.

## Optional: AI assistant setup

Process rules for AI-assisted contributions: [AI contribution guidelines](docs/development/ai-contribution-guidelines.md). Agent orientation: [AI engineering guide](docs/development/ai-engineering-guide.md).

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
6. Update the [contribution pack](docs/development/contributor-guide.md) / [PR checklist](docs/development/pull-request-checklist.md) and [`.github/PULL_REQUEST_TEMPLATE.md`](.github/PULL_REQUEST_TEMPLATE.md) if the human checklist changes; update the matching L1 guide under `docs/architecture/` when runtime behavior changes; update [docs/reference/](docs/reference/cli.md) / guides when the operator CLI or config surface changes.
7. If you use Antigravity locally, sync any local memory file from step 1.

Do not add duplicate checklists to the skill — link the contribution pack instead.
Do not add generic always-on Cursor rules (benchmark prompts, web-app templates); they contradict LILT invariants.
CI ([`.github/workflows/ci.yml`](.github/workflows/ci.yml)) is the objective final check; keep it aligned with [overview](docs/development/overview.md) quality commands.

If you do **not** use Antigravity, you can remove local AG Kit with `rm -rf .agents/ .temp_ag_kit` to reduce editor noise.
