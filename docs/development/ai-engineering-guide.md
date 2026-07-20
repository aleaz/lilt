# AI engineering guide

Agent-facing orientation for changing LILT. Complements [AGENTS.md](../../AGENTS.md) and [`.cursor/rules/lilt-architecture.mdc`](../../.cursor/rules/lilt-architecture.mdc) — it does **not** replace them.

Index: [Developer Guide](README.md). Philosophy pack: [engineering-philosophy.md](engineering-philosophy.md) · [engineering-invariants.md](engineering-invariants.md) · [architectural-guidelines.md](architectural-guidelines.md).

## Read first

1. [AGENTS.md](../../AGENTS.md) — hard stops and path → docs matrix  
2. Always-on rule [`.cursor/rules/lilt-architecture.mdc`](../../.cursor/rules/lilt-architecture.mdc)  
3. Skill [`.cursor/skills/lilt-dev/SKILL.md`](../../.cursor/skills/lilt-dev/SKILL.md) when doing multi-file engine work  
4. This handbook’s [README](README.md) reading order  

## How to organize work

- Prefer **small PRs** that keep Derived docs in sync (Typer ↔ cli.md ↔ agent mirrors).
- Put orchestration in `services/`, domain in `core/` / `tm/` / `parser/` / `llm/` / `validation/` — see [architectural-guidelines.md](architectural-guidelines.md).
- Do not invent product scope (corpus, `project evaluate`, ADR tree, new top-level CLI verbs).

## Naming

| Correct | Incorrect / confusing |
|---------|------------------------|
| Import/CLI: `lilt` | Teaching `pip install lilt` for this project |
| Dist: `latex-lilt` | Treating dist name as the import path |
| Critique (LLM stage) | Equating Critique with human Review |
| `refined` (machine) | Treating as `approved` / `reviewed` |
| AccuracyGate | Letting critique JSON “fix” placeholders |

Full vocabulary: [glossary](../architecture/00-glossary.md).

## Documentation habits for agents

- **Link, don’t invent** encyclopedias of CLI flags — open [cli.md](../reference/cli.md) / Typer.
- New terms → glossary first.
- Behavior change → matching L1 Behavior + tests.
- Not shipped → appendix-deferred only; never document as current Behavior.
- Same-PR updates for surface/contract changes ([conventions](conventions.md)).

## Code that does **not** belong

- Fat CLI handlers with orchestration
- New top-level Typer verbs outside `project` / `pipeline` / `tm` / `telemetry`
- Files under `docs/adrs/`
- Corpus / eval harness trees as product code
- Docs that mark deferred appendix items as shipped
- Vendor SDKs embedded in `core/` without design
- Claims of fully deterministic LLM translation

## When stuck

| Symptom | Check |
|---------|--------|
| Unsure where to put a feature | [architectural-guidelines.md](architectural-guidelines.md) |
| Unsure if allowed | [engineering-invariants.md](engineering-invariants.md) + AGENTS hard stops |
| Unsure of Behavior | L1 for that domain + tests |
| Unsure of a term | Glossary |

## Related

- [engineering-principles.md](engineering-principles.md)
- [conventions.md](conventions.md)
- [project-layout.md](project-layout.md)
