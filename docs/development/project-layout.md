# Project layout

```text
lilt/
├── src/lilt/                  # Main package
│   ├── cli/                   # Typer CLI (project, pipeline, tm, telemetry)
│   ├── core/                  # Sync, build, review policy, translation strategies
│   ├── llm/                   # Providers, factory, router, prompts, reflection
│   ├── models/                # Pydantic domain models
│   ├── parser/                # AST parser, masking, dependency resolver
│   ├── prompts/               # Jinja2 templates (draft, critique, refine, system)
│   ├── services/              # Application services (pipeline, tm, project)
│   ├── telemetry/             # SQLite telemetry and cost estimation
│   ├── tm/                    # JSONL repository, identity, checkpoints
│   ├── utils/                 # Config loader, namespace, token utils
│   └── validation/            # Placeholder, syntax, build validators
├── tests/                     # pytest suite (unit + integration)
├── docs/
│   ├── README.md              # Documentation hub
│   ├── getting-started.md
│   ├── concepts.md
│   ├── guides/
│   ├── reference/
│   ├── runbooks/
│   ├── development/
│   └── architecture/          # L1 architecture guides (SSOT behavior)
├── Makefile                   # format, lint, typecheck, test, ci
├── pyproject.toml
└── README.md
```

---
