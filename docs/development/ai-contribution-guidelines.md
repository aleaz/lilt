# AI contribution guidelines

Rules for **human contributors** who use AI tools (Cursor, Copilot, chat agents, etc.) when sending changes to LILT.

- Agent orientation (organize / name / docs habits): [ai-engineering-guide.md](ai-engineering-guide.md)  
- Hard stops / path matrix: [AGENTS.md](../../AGENTS.md), [`.cursor/rules/lilt-architecture.mdc`](../../.cursor/rules/lilt-architecture.mdc)  
- This file does **not** replace those — it states accountability for PRs.

Cursor SSOT table and anti-drift order: [CONTRIBUTING.md](../../CONTRIBUTING.md) (§ Optional: AI assistant setup).

## Allowed

- AI may assist with drafting code, tests, docs, and refactors.
- AI may help navigate L1 / reference / handbook.

## Required (human responsibility)

- The **human author** owns correctness, architecture fit, and honesty of docs.
- Generated code must follow [architectural-guidelines.md](architectural-guidelines.md) and [engineering-invariants.md](engineering-invariants.md).
- Generated documentation must be **validated against the implementation** — no invented Behavior, flags, or statuses.
- Run **`make ci`** yourself (or ensure it is green) before asking for review — do not bypass tests.
- Complete [pull-request-checklist.md](pull-request-checklist.md).

## Forbidden

| Do not | Why |
|--------|-----|
| Invent CLI surface or Behavior | Implementation is SSOT |
| Fat CLI / new top-level verbs | Product + architecture invariants |
| Restore `docs/adrs/` or corpus/eval trees | Product boundary |
| Mark appendix-deferred as shipped | Honest maturity |
| Skip or weaken tests to “make CI green” | Quality gate |
| Expand architecture (new providers, plugin layer, agent framework) without review | Needs L1 Decision + maintainer agreement |
| Treat Critique as Review / `refined` as `approved` | Glossary |
| Commit secrets, sandboxes, PDFs, model traces | Empirical boundary |

## Suggested workflow with AI

1. Point the tool at AGENTS.md + architecture rule + the L1 guide for the domain.
2. Ask for a design that names the **layer** and docs to update — reject scope creep.
3. Implement in small steps; keep Derived docs in the same PR.
4. Diff-review as if a stranger wrote it (especially imports and CLI handlers).
5. `make ci` → open PR with honest verification notes.

## Maintaining AI context (pointer)

When architecture, CLI surface, or CI commands change, update Cursor rules / AGENTS / skill in the order documented in [CONTRIBUTING.md](../../CONTRIBUTING.md). Do not add duplicate checklists to the skill — link the contribution pack instead.

## Related

- [contributor-guide.md](contributor-guide.md)
- [code-review-guidelines.md](code-review-guidelines.md)
- [contribution-workflow.md](contribution-workflow.md)
