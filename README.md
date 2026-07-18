# LILT — LaTeX Intelligent Localization Tool

[![Python 3.13+](https://img.shields.io/badge/python-3.13+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![CI](https://img.shields.io/badge/CI-make%20ci-green.svg)](docs/development/overview.md)

LILT is a CLI for continuous localization of LaTeX projects. It parses documents into an Abstract Syntax Tree (AST), extracts translatable **segments**, masks structural LaTeX into **placeholders**, runs an LLM **reflection pipeline** (Draft → Critique → Refine), persists state in a **Translation Memory** (TM), and reconstructs translated `.tex` files for compilation.

## Why LILT

- **Integrity over linguistics** — placeholders and syntax are validated before a translation is accepted.
- **Human priority** — `reviewed` / `approved` / `locked` segments are protected from automatic overwrite.
- **TM as source of truth** — append-only JSONL under `.lilt/tm/`.
- **Local-first LLM** — OpenAI-compatible endpoints (local or cloud) via staged Draft → Critique → Refine.
- **Reproducibility** — stable segment IDs, persisted placeholder maps, checkpointed runs.

## Quick start

```bash
uv tool install git+https://github.com/aleaz/lilt
cd your-latex-project
lilt project init
lilt project configure .
lilt pipeline sync main.tex
lilt pipeline translate --all
mkdir -p i18n/build
lilt pipeline build main main.tex i18n/build/main.tex
```

Full install options and walkthrough: [Getting started](docs/getting-started.md).

## Documentation

| Doc | For |
|-----|-----|
| [Documentation hub](docs/README.md) | All audiences and reading paths |
| [Getting started](docs/getting-started.md) | Install and first pipeline |
| [Concepts](docs/concepts.md) | Product model and features |
| [CLI reference](docs/reference/cli.md) | Command surface |
| [Architecture](docs/architecture/README.md) | Runtime SSOT (L1 guides) |

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) and [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).
Development setup and `make ci`: [docs/development/overview.md](docs/development/overview.md).

## License

LILT is released under the [MIT License](LICENSE).

Copyright (c) 2026 Alejandro Azario
