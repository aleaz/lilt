# Project layout

Index: [Developer Guide](README.md).

## Repository tree

```text
lilt/
├── src/lilt/                  # Main package (import name: lilt)
│   ├── cli/                   # Typer CLI (project, pipeline, tm, telemetry)
│   ├── core/                  # Sync, build, review policy, translation strategies
│   ├── llm/                   # Providers, factory, router, prompts, reflection
│   ├── models/                # Pydantic domain models + config
│   ├── parser/                # AST parser, masking, dependency resolver
│   ├── prompts/               # Jinja2 templates (draft, critique, refine, system)
│   ├── services/              # Application services + WorkspaceContext
│   ├── telemetry/             # SQLite telemetry and cost estimation
│   ├── tm/                    # JSONL repository, identity, checkpoints
│   ├── utils/                 # YAML loader, paths, tokens
│   ├── validation/            # Segment / placeholder / syntax / build / AccuracyGate
│   └── exceptions.py          # Domain exceptions
├── tests/                     # pytest suite (unit + integration + CLI)
├── docs/
│   ├── README.md              # Documentation hub
│   ├── development/           # This handbook
│   ├── reference/             # CLI + config SSOT
│   └── architecture/          # L1 behavior SSOT
├── scripts/                   # e.g. check-doc-sync.sh
├── Makefile                   # format, lint, typecheck, test, ci
├── pyproject.toml             # package metadata, ruff, mypy, pytest
└── README.md                  # Public landing (not engineering handbook)
```

## Module responsibilities

| Package | Responsibility | Deeper docs |
|---------|----------------|-------------|
| `cli/` | Thin Typer adapters; global `-C` / `--debug` / `--version` | [CLI reference](../reference/cli.md), [07-cli-application](../architecture/07-cli-application.md) |
| `services/` | Orchestration (`PipelineService`, `TMService`, `ProjectService`, …) | L1-07 |
| `services/workspace_context.py` | **Composition root**: paths, TM repo, lazy telemetry | L1-07 |
| `core/` | Sync, build, reflection strategies, review policy | L1-04, L1-06 |
| `tm/` | Append-only JSONL TM, identity, checkpoints | L1-02 |
| `parser/` | AST, placeholders, deps | L1-03 |
| `llm/` | OpenAI-compatible providers, gates, reflection pass | L1-05 |
| `validation/` | Structural validators + AccuracyGate | L1-04 |
| `models/` | Segments, statuses, `LiltConfig` | Glossary, [config reference](../reference/config.md) |
| `telemetry/` | Inference records / cost estimates | L1-08 |
| `prompts/` | Jinja templates | L1-04 / L1-05 |

## Dependency direction

```text
CLI (Typer)
  → services (WorkspaceContext wires TM + telemetry)
    → core / tm / parser / llm / validation
      → models / utils
```

Prefer extending **services/core** over putting orchestration in CLI handlers ([architecture rule](../../.cursor/rules/lilt-architecture.mdc)).

## Extension points (implemented)

| Extension | How | Docs |
|-----------|-----|------|
| New CLI command/flag | Typer under `cli/commands/` | Update [cli.md](../reference/cli.md) + agent mirrors same PR |
| Prompt text | Jinja under `prompts/` or `llm.prompt_dir` | L1-04 / config reference |
| Per-stage models / URLs | `llm.stages` | [config reference](../reference/config.md), configuration guide |
| Cost / thinking floors | `llm.stage_policies`, `cost_profile` | L1-05, `lilt tm budget` |
| Parser masking | `parser.*` in `lilt.yaml` + configure | L1-03 |

## Not implemented (do not document as shipped)

Plugins, multi-language `.lilt/<lang>/`, corpus/eval CLI, `compile_pdf` as a user command — see [appendix-deferred](../architecture/appendix-deferred.md) and product boundary on the [architecture README](../architecture/README.md).

---
