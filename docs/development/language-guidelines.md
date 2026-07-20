# Language guidelines

Rules for naming and terminology in LILT. **Definitions** live only in the [Canonical Domain Language](../architecture/00-glossary.md) (also linked from [docs/glossary.md](../glossary.md)).

Index: [Developer Guide](README.md).

## Core rules

1. **One concept = one canonical name.** Prefer glossary terms in code comments, docs, PR titles, and CLI help.
2. **One name = one meaning.** If a word is overloaded (stage, context, model, workflow), **qualify** it (see glossary disambiguation tables).
3. **Code wins** when docs and implementation disagree — update docs (or fix a tracked bug), do not invent a second vocabulary.
4. **New concepts require a glossary entry in the same PR** before spreading the term across guides or agent rules.

## Introducing a new concept

1. Check [00-glossary](../architecture/00-glossary.md) and [appendix-deferred](../architecture/appendix-deferred.md).
2. Add a glossary entry (same schema: definition, responsibility, relationships, code example, alternatives, recommendation).
3. Use the canonical name in code/docs; list deprecated synonyms under “Deprecated terminology” if needed.
4. Do not introduce product terms for deferred features as if shipped.

## Naming modules and layers

Follow [architectural-guidelines](architectural-guidelines.md) and [project-layout](project-layout.md):

| Layer | Owns |
|-------|------|
| `cli/` | Thin adapters — group names fixed: `project`, `pipeline`, `tm`, `telemetry` |
| `services/` | Orchestration (`PipelineService`, `WorkspaceContext`, …) |
| `core/` | Domain algorithms (translate, build, sync, review policy) |
| `tm/` | Translation Memory I/O and checkpoints |
| `parser/` | AST / placeholders |
| `llm/` | Providers, prompts, reflection passes |
| `validation/` | Structural validation / AccuracyGate |

Prefer existing suffixes: `*Policy` (rules), `*Strategy` (orchestration), `*Resolver` (qualified which one), `*Provider` (LLM port). Avoid new vague `*Manager` / `*Handler` / `*Agent` types.

## Naming CLI commands

- Do **not** add top-level verbs outside the four groups.
- Flags and help text must match Typer; document in [cli.md](../reference/cli.md) same PR.
- `pipeline review` = human Review; never describe LLM Critique as “review” in help strings.

## Naming configuration fields

- Keys follow shipped `LiltConfig` / [config.md](../reference/config.md).
- Do not document synonym keys (`settings.*`, invented aliases).
- `translation_mode: workflow` means **Execution Mode**, not the Translation Pipeline and not the operator “Workflows” guide.

## Avoid semantic drift

| Incorrect | Correct |
|-----------|---------|
| Critique = Review | Critique = LLM; Review = human |
| `refined` = approved | `refined` = machine-finished; human gates are `reviewed` / `approved` / `locked` |
| Agent / multi-agent product | Reflection stages D→C→R |
| PDF as CLI output | Build emits `.tex`; PDF external |
| `pip install lilt` | Dist `latex-lilt`; CLI `lilt` |
| Workspace = Workspace Context | Directory vs composition root |
| Namespace = document | Encoded TM partition vs `.tex` file |

## Forbidden / deprecated

See glossary [Deprecated terminology](../architecture/00-glossary.md#deprecated-terminology-do-not-use-in-new-docs). Do not revive those phrases in new docs or agent rules.

## Related

- [ai-domain-language-guide.md](ai-domain-language-guide.md)
- [conventions.md](conventions.md)
- [engineering-invariants.md](engineering-invariants.md)
