# Architectural guidelines

Where new code goes and how architecture evolves safely. Complements [project-layout](project-layout.md) and L1. Hard stops: [engineering-invariants.md](engineering-invariants.md).

Index: [Developer Guide](README.md).

## Where to put new code

| You are adding… | Put it in | Do not |
|-----------------|-----------|--------|
| Operator-facing command | Existing Typer group under `cli/` + thin handler | New top-level verb outside `project` / `pipeline` / `tm` / `telemetry` |
| Multi-step use-case | `services/` | Fat logic in CLI handlers |
| Domain algorithm (translate, sync, build, reflect) | `core/` | Direct TM I/O sprawled across CLI |
| Segment memory I/O | `tm/` | Ad-hoc JSONL writes from CLI |
| Structure / AST work | `parser/` | Regex-only “parsing” in services unless justified |
| Model HTTP / prompts | `llm/` (+ Jinja templates) | Vendor SDK inside `core/` |
| Structural checks | `validation/` | Letting critique JSON own placeholders |
| Shared types / config schema | `models/` | Duplicating pydantic shapes |
| Cross-cutting helpers | `utils/` | Hidden globals bypassing `WorkspaceContext` |

## Composition root

- Prefer obtaining paths, TM store, and telemetry through **`WorkspaceContext`**.
- New long-lived workspace services should be constructed there (or clearly documented if not).

## LLM providers

- Register adapters via the existing factory pattern.
- Shipped default: OpenAI-compatible adapter name `openai`.
- New providers: design + L1 Decision + docs — do not silently fork HTTP clients in core.

## Prompts

- Edit package Jinja or document `llm.prompt_dir` overrides.
- Keep stage roles aligned with L1-05 (Draft / Critique / Refine, etc.).
- Do not store large prompt bodies in `lilt.yaml`.

## Reflection and quality

- Treat Draft / Critique / Refine as **pipeline stages** with persisted TM artifacts.
- Do not introduce a separate “agent framework” layer without design + appendix/L1 update.
- Editorial critique ≠ human Review; AccuracyGate ≠ critique.

## When to touch which L1 doc

| Change type | Update |
|-------------|--------|
| Observable Behavior (statuses, build rules, pipeline steps) | Matching L1 **Behavior** (+ tests) |
| Tradeoff / “why we chose X” | L1 **Decisions** |
| Known limitation still true | L1 **Known gaps** |
| Not implemented yet | [appendix-deferred](../architecture/appendix-deferred.md) only |
| New term / status name | [glossary](../architecture/00-glossary.md) **first** |
| Operator flags / keys | [cli.md](../reference/cli.md) / [config.md](../reference/config.md) same PR |

## Evolving architecture safely

1. **Ship:** implement → tests → shrink appendix if the item was deferred → expand L1 Behavior → PRD Shipped if user-visible.
2. **Defer:** leave or add in appendix; do not document as current Behavior.
3. **Rename terms:** glossary + Derived docs + code in one PR when possible.
4. **Layer breach:** if you must call “upward,” stop — refactor toward services/core instead.

## Safe extension checklist

- [ ] Fits an existing CLI group or is service-only
- [ ] Respects dependency direction
- [ ] Human locks still hold
- [ ] Validation / AccuracyGate ownership unchanged unless Decision says so
- [ ] Same-PR docs for surface/contract changes
- [ ] No corpus/eval/ADR revival

## Related

- [engineering-philosophy.md](engineering-philosophy.md)
- [engineering-principles.md](engineering-principles.md)
- [ai-engineering-guide.md](ai-engineering-guide.md)
- [Architecture README](../architecture/README.md)
