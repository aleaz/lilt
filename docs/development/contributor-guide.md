# Contributor Guide

How to contribute to LILT while preserving quality and architectural integrity.

GitHub entry: [CONTRIBUTING.md](../../CONTRIBUTING.md). Index: [Developer Guide](README.md). Process detail: [contribution-workflow.md](contribution-workflow.md).

## Expectations

- **Implementation is SSOT** — docs follow code; do not invent Behavior.
- **Preserve layers** — thin CLI; orchestration in `services/`; domain in `core/` / `tm/` / `parser/` / `llm/` / `validation/`.
- **Product boundary** — this repo ships the localization engine and its tests only (no corpus/eval harnesses).
- **Same-PR docs** for Typer / config / contract changes.
- **CI gate** — `make ci` must pass (what GitHub Actions runs).

Hard stops: [engineering-invariants.md](engineering-invariants.md), [AGENTS.md](../../AGENTS.md).

## Getting started

Full setup, make targets, debug, packaging: [overview.md](overview.md).

Short path:

1. Python **3.13+** and [`uv`](https://docs.astral.sh/uv/).
2. `git clone https://github.com/aleaz/lilt` → `uv sync`.
3. Optional: `source .venv/bin/activate` (or point the IDE at `.venv`).
4. Sanity: `uv run lilt --version`.
5. Before a PR: `make ci` (non-mutating, matches CI). Local auto-format/fix first: `make check-all`.

Tests: [testing.md](testing.md). Layout: [project-layout.md](project-layout.md). Style/naming: [conventions.md](conventions.md).

## Reading order (new contributor)

1. This guide  
2. [overview.md](overview.md)  
3. [project-layout.md](project-layout.md)  
4. [conventions.md](conventions.md)  
5. [Philosophy & invariants](README.md#philosophy--invariants)  
6. [testing.md](testing.md)  
7. [contribution-workflow.md](contribution-workflow.md) + [pull-request-checklist.md](pull-request-checklist.md)  
8. [Architecture README](../architecture/README.md) → glossary → L1 for the domain you touch  

Agents / AI-assisted work: [ai-contribution-guidelines.md](ai-contribution-guidelines.md) and [ai-engineering-guide.md](ai-engineering-guide.md).

## Contribution types

| Type | Expectations |
|------|----------------|
| **Bug fix** | Repro steps; regression test; update L1/reference if Behavior or operator surface changed |
| **Feature** | Fit existing CLI groups (`project` / `pipeline` / `tm` / `telemetry`); put logic in services/core; L1 Decision if tradeoff; same-PR docs; no new top-level verbs |
| **Documentation** | Correct Diátaxis home; glossary SSOT; never mark [appendix-deferred](../architecture/appendix-deferred.md) items as shipped |
| **Examples** | Prefer [guides](../guides/) / [getting-started](../getting-started.md) until a dedicated `examples/` tree ships — do not invent that tree |
| **Tests** | Follow [testing.md](testing.md) patterns; no large empirical campaigns or corpora in this repo |
| **Refactor** | Preserve Behavior; call out any CLI/config break (public beta may change, but be explicit) |
| **Performance** | Prefer measurable changes (telemetry / existing runbooks); do not invent SLOs in docs |
| **Developer tooling** | Keep Makefile / `scripts/` / CI aligned with `make ci` |
| **Security** | Follow [SECURITY.md](../../SECURITY.md); never commit secrets |

## Architecture preservation (summary)

| Concern | Rule |
|---------|------|
| Dependencies | `cli → services → core\|parser\|tm\|llm\|validation` |
| Business / orchestration | `services/` (not fat CLI handlers) |
| CLI | Thin adapters only; four public groups |
| Providers | LLM factory / OpenAI-compatible `openai` unless designed + documented |
| Human locks | Never auto-overwrite `reviewed` / `approved` / `locked` |
| Structural accuracy | AccuracyGate / validators — not free-text critique JSON |

Detail: [architectural-guidelines.md](architectural-guidelines.md), [engineering-invariants.md](engineering-invariants.md).

## Code contribution rules (pointers)

| Topic | Go to |
|-------|--------|
| Naming (`lilt` vs `latex-lilt`, Critique≠Review) | [conventions.md](conventions.md), [glossary](../architecture/00-glossary.md) |
| Module placement | [architectural-guidelines.md](architectural-guidelines.md) |
| Error handling | Thin CLI; domain exceptions — [07-cli-application](../architecture/07-cli-application.md) |
| Testing | [testing.md](testing.md) |
| Backward compatibility | Public beta: CLI/config may change until intentional release — [overview](overview.md) |
| Docs sync matrix | [conventions.md](conventions.md) |

## Common mistakes

- Fat Typer handlers or new top-level CLI verbs  
- Corpus / `project evaluate` / `docs/adrs/` revival  
- Documenting deferred appendix items as current Behavior  
- Skipping `docs/reference/cli.md` or L1 when Typer/Behavior changes  
- Equating Critique with human Review; treating `refined` as `approved`  
- Committing evaluation sandboxes, PDFs, or model traces  
- Teaching `pip install lilt` (dist name is **`latex-lilt`**)

## Next steps

- How to open a change: [contribution-workflow.md](contribution-workflow.md)  
- Before you click Create PR: [pull-request-checklist.md](pull-request-checklist.md)  
- What maintainers look for: [code-review-guidelines.md](code-review-guidelines.md)  
- AI-assisted PRs: [ai-contribution-guidelines.md](ai-contribution-guidelines.md)
