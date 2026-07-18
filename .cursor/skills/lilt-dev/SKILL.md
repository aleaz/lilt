---
name: lilt-dev
description: >-
  LILT (LaTeX Intelligent Localization Tool) CLI development and usage workflows.
  Use when syncing or translating LaTeX, managing Translation Memory, changing the
  CLI/services/parser/TM/LLM layers, or preparing a change for PR in this repository.
---

# LILT — CLI development and usage

LILT localizes LaTeX via AST parse → mask → TM → LLM reflection → build.
Invariants: [`.cursor/rules/lilt-architecture.mdc`](../../rules/lilt-architecture.mdc).
Deep architecture: [docs/architecture/README.md](../../../docs/architecture/README.md).
Docs hub: [docs/README.md](../../../docs/README.md).

## Lifecycle (README)

```bash
# 1. Initialize workspace in a LaTeX project
cd my-paper/
lilt project init
lilt project configure .
# Optional dry-run analysis without writing lilt.yaml:
lilt project configure . --dry-run --gaps
# Edit .lilt/lilt.yaml (target_lang, base_url, model) and .lilt/.env if needed

# 2. Sync source into Translation Memory (crawls \input / \usepackage deps)
lilt pipeline sync main.tex

# 3. Translate (workflow = breadth-first D→C→R; sequential = depth-first)
lilt pipeline translate --all
lilt pipeline translate main --mode sequential
lilt pipeline translate main --stage draft   # workflow only

# 4. Human review / edit
lilt pipeline review main
lilt pipeline edit main <segment_id>
lilt tm list main --status conflict
lilt tm list main --id <segment_id>
lilt tm status main

# 5. Build translated .tex (PDF is manual)
mkdir -p i18n/build
lilt pipeline build main main.tex i18n/build/main.tex
cd i18n/build && pdflatex main.tex   # or latexmk — not a lilt CLI command

# 6. TM maintenance
lilt tm export main review.csv
lilt tm import main review.csv
lilt tm set-status main <id> locked
lilt tm admin repair main
lilt tm admin prune main
lilt tm admin reset main

# 7. Telemetry
lilt telemetry show
```

## Code map

| Path | Responsibility |
|------|----------------|
| `src/lilt/cli/` | Typer commands (thin adapters) |
| `src/lilt/services/` | Application orchestration + preconditions |
| `src/lilt/core/` | Sync, translation strategies, build, review policy |
| `src/lilt/parser/` | AST, masking, placeholders, deps, roundtrip |
| `src/lilt/tm/` | JSONL repository, identity, checkpoint, locks |
| `src/lilt/llm/` | OpenAI-compatible provider, router, reflection, prompts |
| `src/lilt/validation/` | Placeholder / syntax / segment / build validators |
| `src/lilt/models/` | Pydantic domain models and status transitions |

## Do not implement as if shipped

- Corpus / evaluation tooling or `project evaluate`
- `compile_pdf` as a CLI command
- Plugins, multi-language `.lilt/<lang>/`, Terminology/Structure validators, HTTP/TUI
- Restoring `docs/adrs/` — use L1 **Decisions** / [appendix-deferred](../../../docs/architecture/appendix-deferred.md)

Canonical CLI table: [docs/reference/cli.md](../../../docs/reference/cli.md).
Services/invariants: [docs/architecture/07-cli-application.md](../../../docs/architecture/07-cli-application.md).

## Validation and PR

- Local gate matching CI: `make ci` (see [CONTRIBUTING.md](../../../CONTRIBUTING.md)).
- Do not duplicate PR checklists here — use CONTRIBUTING and [`.github/PULL_REQUEST_TEMPLATE.md`](../../../.github/PULL_REQUEST_TEMPLATE.md).
- Behavior changes in `src/lilt/` must update the matching L1 guide in the same change set.

## Git

Follow [`.cursor/rules/lilt-git-agent.mdc`](../../rules/lilt-git-agent.mdc): commit/push/PR only when the user explicitly asks.
