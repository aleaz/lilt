# Developer Guide (Engineering Handbook)

| | |
|---|---|
| **Purpose** | Primary engineering handbook for maintainers, contributors, and AI agents |
| **Audience** | People who change `src/lilt/`, tests, CI, or engineering docs |
| **Not this guide** | End-user install/tutorial → [Getting started](../getting-started.md); runtime Behavior → [Architecture](../architecture/README.md) |

This is the **single entry** for development practices. Deep product behavior stays in L1; operator commands stay in [CLI](../reference/cli.md) / [config](../reference/config.md) reference.

## Philosophy (short)

- **Implementation is SSOT** for behavior — docs follow code.
- **No ADR tree** — decisions live in L1 Decisions / Known gaps / [appendix-deferred](../architecture/appendix-deferred.md).
- **Human locks** (`reviewed` / `approved` / `locked`) are never auto-overwritten — [glossary](../architecture/00-glossary.md).
- **Local-first** LLM (OpenAI-compatible); product boundary excludes corpus/eval harnesses — [architecture README](../architecture/README.md).

Full pack: [Philosophy & invariants](#philosophy--invariants).

## Reading order

1. [Development overview](overview.md) — setup, make, debug, packaging, release honesty  
2. [Project layout](project-layout.md) — tree, modules, dependency direction  
3. [Engineering conventions](conventions.md) — style, naming, docs sync  
4. [Philosophy & invariants](#philosophy--invariants) — culture, principles, hard rules, where code goes  
5. [Testing](testing.md) — pytest and CI  
6. [Contribution](#contribution) — how to change the project safely  
7. [Architecture README](../architecture/README.md) → glossary → L1 for the domain you touch  
8. [CLI](../reference/cli.md) / [config](../reference/config.md) if the operator surface changes  

Agents: start at [AGENTS.md](../../AGENTS.md), [`.cursor/rules/lilt-architecture.mdc`](../../.cursor/rules/lilt-architecture.mdc), [ai-engineering-guide.md](ai-engineering-guide.md), [ai-domain-language-guide.md](ai-domain-language-guide.md), and [ai-contribution-guidelines.md](ai-contribution-guidelines.md).

GitHub entry for humans: [CONTRIBUTING.md](../../CONTRIBUTING.md).

## Philosophy & invariants

| Document | Role |
|----------|------|
| [engineering-philosophy.md](engineering-philosophy.md) | How to *think* when changing LILT |
| [engineering-principles.md](engineering-principles.md) | Named principles actually used (with evidence) |
| [engineering-invariants.md](engineering-invariants.md) | Hard rules that must not break |
| [architectural-guidelines.md](architectural-guidelines.md) | Where new code goes; how architecture evolves |
| [ai-engineering-guide.md](ai-engineering-guide.md) | Agent-facing organize / name / docs habits |
| [language-guidelines.md](language-guidelines.md) | Naming and terminology rules |
| [ai-domain-language-guide.md](ai-domain-language-guide.md) | Agent vocabulary / anti-drift |

## Contribution

| Document | Role |
|----------|------|
| [contributor-guide.md](contributor-guide.md) | Expectations, getting started, contribution types |
| [contribution-workflow.md](contribution-workflow.md) | Branch → PR → review → release honesty; feature/bug paths |
| [pull-request-checklist.md](pull-request-checklist.md) | Author self-check (canonical) |
| [code-review-guidelines.md](code-review-guidelines.md) | What reviewers verify |
| [ai-contribution-guidelines.md](ai-contribution-guidelines.md) | Human-owned AI-assisted contributions |

## Link, don’t copy

| Need | Go to |
|------|-------|
| What a command does | [CLI reference](../reference/cli.md) |
| `lilt.yaml` keys | [Configuration reference](../reference/config.md) |
| Why the engine behaves this way | [L1 guides](../architecture/README.md) |
| Domain vocabulary | [Glossary](../architecture/00-glossary.md) · [Language guidelines](language-guidelines.md) |
| First user pipeline | [Getting started](../getting-started.md) |
| Not implemented yet | [appendix-deferred](../architecture/appendix-deferred.md) |
| Docs hub by audience | [docs/README.md](../README.md) |

## Handbook map

| Brief topic | Document |
|-------------|---------|
| Engineering Handbook (this index) | `docs/development/README.md` |
| Development workflow | [overview.md](overview.md) |
| Repository overview | [project-layout.md](project-layout.md) |
| Engineering conventions | [conventions.md](conventions.md) |
| Philosophy & invariants | [engineering-philosophy.md](engineering-philosophy.md) (+ principles, invariants, guidelines, AI + language guides) |
| Testing | [testing.md](testing.md) |
| Contribution | [contributor-guide.md](contributor-guide.md) (+ workflow, checklist, review, AI contribution) |
| Contribution (GitHub entry) | [CONTRIBUTING.md](../../CONTRIBUTING.md) |
