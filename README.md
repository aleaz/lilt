# LILT — LaTeX Intelligent Localization Tool

[![Python 3.13+](https://img.shields.io/badge/python-3.13+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![CI](https://github.com/aleaz/lilt/actions/workflows/ci.yml/badge.svg)](https://github.com/aleaz/lilt/actions/workflows/ci.yml)
[![Status](https://img.shields.io/badge/status-public%20beta%200.1.x-orange.svg)](docs/concepts.md#maturity)

LILT is a CLI for continuous LaTeX localization: AST parse → **segments** → **placeholders** → **Translation Memory** (TM) → LLM Draft → Critique → Refine → rebuilt `.tex`.
It translates prose without sending raw structure to the model, and validates placeholders before a translation is accepted.

> **Not affiliated with [Lilt Inc.](https://lilt.com/) / lilt.com.**  
> This project’s name is the acronym *LaTeX Intelligent Localization Tool*.  
> It is **not** on PyPI as `lilt` (that name belongs to another project). Install from Git as shown below; the distribution package name is `latex-lilt`.

## Why LILT

- **Integrity over linguistics** — keep LaTeX compile-safe; validate placeholders and syntax first.
- **Human priority** — `reviewed` / `approved` / `locked` are never auto-overwritten.
- **TM as source of truth** — append-only JSONL under `.lilt/tm/`.
- **Local-first LLM** — OpenAI-compatible endpoints (local or cloud) per stage.
- **Reproducibility** — stable segment IDs, persisted placeholder maps, checkpoints.

## Quick start

```bash
# Install (Git only — do not use `pip install lilt`)
uv tool install git+https://github.com/aleaz/lilt   # see Getting started for uv sync / editable

# From a directory that contains your .tex sources:
cd your-latex-project
lilt project init
lilt project configure .

# Configure an OpenAI-compatible LLM (required before translate).
# Edit .lilt/lilt.yaml — e.g. local LM Studio / Ollama:
#   llm:
#     base_url: "http://localhost:1234/v1"
#     model: "your-model-id"
#     api_key_env: "OPENAI_API_KEY"   # optional for many local servers
# Put cloud API keys in .lilt/.env or workspace .env if needed.

lilt pipeline sync main.tex
lilt pipeline translate --all
mkdir -p i18n/build
lilt pipeline build main main.tex i18n/build/main.tex
# PDF: compile i18n/build/main.tex yourself (not a lilt command)
```

Full install options, LLM setup, and walkthrough: [Getting started](docs/getting-started.md).

## Documentation

| Doc | Use when |
|-----|----------|
| [Documentation hub](docs/README.md) | Hub / reading paths |
| [Getting started](docs/getting-started.md) | Install & first pipeline |
| [Concepts](docs/concepts.md) | Model & principles |
| [CLI reference](docs/reference/cli.md) | Commands & flags |
| [Architecture](docs/architecture/README.md) | Runtime SSOT (L1) |

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) and [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).
Questions vs bugs: [SUPPORT.md](SUPPORT.md).
Development setup and `make ci`: [docs/development/overview.md](docs/development/overview.md).

## License

LILT is released under the [MIT License](LICENSE).

Copyright (c) 2026 Alejandro Azario
