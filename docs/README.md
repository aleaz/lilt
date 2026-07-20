# Documentation

Hub for LILT user, operator, and developer documentation.

Runtime behavior and architectural decisions live under
[architecture/](architecture/README.md) (L1 guides). This tree holds getting
started, guides, reference, runbooks, and development docs.

## Audiences and reading paths

| Audience | Start here | Then |
|----------|------------|------|
| **New user** | [Getting started](getting-started.md) | [First translation](guides/first-translation.md) → [Workflows](guides/workflows.md) |
| **Technical user** (author / translator) | [Concepts](concepts.md) | [Configuration guide](guides/configuration.md) → [Human review](guides/human-review.md) → [Advanced usage](guides/advanced-usage.md) → [CLI reference](reference/cli.md) → [Troubleshooting](runbooks/troubleshooting.md) · [FAQ](faq.md) |
| **Translation maintainer** | [Workflows](guides/workflows.md) | [Config reference](reference/config.md) → runbooks ([troubleshooting](runbooks/troubleshooting.md), [recovery](runbooks/recovery.md), [error reference](runbooks/error-reference.md)) |
| **Developer** (extends the engine) | [Developer Guide](development/README.md) | [Architecture README](architecture/README.md) → glossary → L1 → [overview](development/overview.md) |
| **Contributor** | [CONTRIBUTING.md](../CONTRIBUTING.md) | [Contributor Guide](development/contributor-guide.md) → [Developer Guide](development/README.md) → L1 for the area you change |

## Getting started

- [Getting started](getting-started.md) — Quick Start: install, LLM, first sync→translate→build
- [Official Quick Start example](../examples/quickstart/) — short technical note + walkthrough (~2–3 pages)
- [First translation](guides/first-translation.md) — Expanded first successful workflow
- [Concepts](concepts.md) — purpose, features, architecture overview (user view)
- [FAQ](faq.md) — conceptual questions (not symptom encyclopedias)
- [Glossary](glossary.md) — redirect to canonical domain language

## Guides

- [Workflows](guides/workflows.md) — project, resume, TM, review, debug scenarios
- [Advanced usage](guides/advanced-usage.md) — modes, stages, budget, shell automation
- [Human review](guides/human-review.md) — review queue, export/import, statuses
- [Configuration guide](guides/configuration.md) — LLM topologies and operator tips

## Reference

- [CLI reference](reference/cli.md) — canonical command surface
- [Configuration reference](reference/config.md) — env vars and `lilt.yaml`

## Runbooks

- [Troubleshooting](runbooks/troubleshooting.md) — categories, decision trees, onboarding index
- [Error reference](runbooks/error-reference.md) — domain exceptions → fix
- [Recovery](runbooks/recovery.md) — multi-step recovery procedures
- [Performance](runbooks/performance.md)

## Architecture (SSOT behavior)

- [Architecture README](architecture/README.md) — reading order and product boundary
- [00-glossary](architecture/00-glossary.md) — canonical vocabulary ([docs/glossary.md](glossary.md) redirect)
- [00-product-context](architecture/00-product-context.md) — PRD / product intent
- [01-platform](architecture/01-platform.md) … [08-observability](architecture/08-observability.md)
- [appendix-deferred](architecture/appendix-deferred.md) — not yet implemented

## Development

- [Developer Guide (handbook index)](development/README.md)
- [Development overview](development/overview.md)
- [Project layout](development/project-layout.md)
- [Engineering conventions](development/conventions.md)
- [Testing](development/testing.md)
- [Contributor Guide](development/contributor-guide.md)

## Project governance (repository root)

- [CONTRIBUTING.md](../CONTRIBUTING.md)
- [SUPPORT.md](../SUPPORT.md) — questions vs bugs; check FAQ / troubleshooting first
- [CODE_OF_CONDUCT.md](../CODE_OF_CONDUCT.md)
- [SECURITY.md](../SECURITY.md)
- [CHANGELOG.md](../CHANGELOG.md)
- [AGENTS.md](../AGENTS.md) — pointer for AI coding agents
- [LICENSE](../LICENSE)
