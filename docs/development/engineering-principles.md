# Engineering principles

Design principles **actually used** in LILT. Each row cites evidence. Unsupported slogans are omitted.

Companion: [engineering-philosophy.md](engineering-philosophy.md). Index: [Developer Guide](README.md).

## Applied principles

| Principle | What it means here | Evidence |
|-----------|-------------------|----------|
| **Separation of concerns** | CLI adapts; services orchestrate; core/parser/tm/llm/validation own domains | `src/lilt/cli/` vs `services/` vs `core/`… |
| **Single responsibility (pragmatic)** | One package primary job (e.g. `tm/` = JSONL memory) | [project-layout](project-layout.md) |
| **Dependency direction** | Imports point inward only | Architecture rule layers; layout doc |
| **Composition over inheritance** | Strategies and services compose; `WorkspaceContext` wires deps | `WorkspaceContext`, reflection strategies |
| **Composition root** | One place builds shared workspace deps | `services/workspace_context.py` |
| **Thin adapters** | No business orchestration in Typer handlers | Architecture rule; L1-07 |
| **Explicit configuration** | Typed `LiltConfig` / `lilt.yaml` + env | `models/config.py`, config reference |
| **Fail closed (where shipped)** | Incomplete build does not look successful by default | `core/build.py`, cli `build --allow-partial` |
| **Validate then persist** | Structural checks before TM commit | SegmentTranslationValidator; human edit path |
| **Deterministic structural gate** | AccuracyGate owns placeholder/syntax vs draft | `validation/accuracy_gate.py` |
| **Progressive disclosure** | Shallow README → hub → L1 depth | docs IA / hub |
| **Link, don’t copy** | One SSOT per fact; mirrors for agents | cli.md → rules/skill; glossary |
| **Minimal public surface** | Four CLI groups only | Typer app; AGENTS hard stops |
| **Low coupling at provider edge** | Core uses LLM abstractions; one shipped HTTP adapter name | `llm/` factory `openai` |
| **High cohesion in pipelines** | Sync → translate → build as clear stages | L1-04 / L1-06 |
| **Human priority** | Protected statuses never auto-overwritten | L1-02; architecture rule |
| **Integrity over linguistics** | Structure before “better prose” | Architecture rule; validators |
| **Architecture as decision log** | Decisions in L1; no ADR tree | L1 sections; appendix-deferred |
| **Honest maturity** | Beta / Unreleased until intentional tag | CHANGELOG; conventions |

## Principles we do **not** claim

| Slogan | Why omitted |
|--------|-------------|
| Fully deterministic translation | LLM stages are stochastic; only structural gates are deterministic |
| Immutable domain models everywhere | Segments mutate through explicit lifecycle transitions |
| Plugin architecture | Deferred — [appendix-deferred](../architecture/appendix-deferred.md) |
| Universal backward compatibility | Public beta may change CLI/config until intentional release |

## How to use this list

When proposing a change, ask: does it violate dependency direction, thin CLI, human locks, or Derived docs sync? If yes, redesign or update L1 Decisions deliberately.

---

*See also [engineering-invariants.md](engineering-invariants.md).*
