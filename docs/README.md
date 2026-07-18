# Documentation

Hub for LILT user, operator, and developer documentation.

Runtime behavior and architectural decisions live under
[architecture/](architecture/README.md) (L1 guides). This tree holds getting
started, guides, reference, runbooks, and development docs extracted from the
former monolithic README.

## Audiences and reading paths

| Audience | Start here | Then |
|----------|------------|------|
| **New user** | [Getting started](getting-started.md) | [Concepts](concepts.md) → [Workflows](guides/workflows.md) |
| **Technical user** (author / translator) | [Concepts](concepts.md) | [Configuration guide](guides/configuration.md) → [Human review](guides/human-review.md) → [CLI reference](reference/cli.md) → [Troubleshooting](runbooks/troubleshooting.md) |
| **Translation maintainer** | [Workflows](guides/workflows.md) | [Config reference](reference/config.md) → [02-persistence](architecture/02-persistence.md) → runbooks |
| **Developer** (extends the engine) | [Architecture README](architecture/README.md) | [00-glossary](architecture/00-glossary.md) → L1 domain guide → [Development overview](development/overview.md) |
| **Contributor** | [CONTRIBUTING.md](../CONTRIBUTING.md) | [Development overview](development/overview.md) → PR template → L1 for the area you change |

## Getting started

- [Getting started](getting-started.md) — install, workspace, first pipeline
- [Concepts](concepts.md) — purpose, features, architecture overview (user view)

## Guides

- [Workflows](guides/workflows.md) — init, translate, resume, conflicts
- [Human review](guides/human-review.md) — review queue, export/import, statuses
- [Configuration guide](guides/configuration.md) — LLM topologies and operator tips

## Reference

- [CLI reference](reference/cli.md) — canonical command surface
- [Configuration reference](reference/config.md) — env vars and `lilt.yaml`

## Runbooks

- [Troubleshooting](runbooks/troubleshooting.md)
- [Performance](runbooks/performance.md)

## Architecture (SSOT behavior)

- [Architecture README](architecture/README.md) — reading order and product boundary
- [00-glossary](architecture/00-glossary.md) — canonical vocabulary
- [00-product-context](architecture/00-product-context.md) — PRD / product intent
- [01-platform](architecture/01-platform.md) … [08-observability](architecture/08-observability.md)
- [appendix-deferred](architecture/appendix-deferred.md) — not yet implemented

## Development

- [Development overview](development/overview.md)
- [Project layout](development/project-layout.md)
- [Testing](development/testing.md)

## Project governance (repository root)

- [CONTRIBUTING.md](../CONTRIBUTING.md)
- [CODE_OF_CONDUCT.md](../CODE_OF_CONDUCT.md)
- [SECURITY.md](../SECURITY.md)
- [CHANGELOG.md](../CHANGELOG.md)
- [AGENTS.md](../AGENTS.md) — pointer for AI coding agents
- [LICENSE](../LICENSE)
