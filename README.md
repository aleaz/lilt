# LILT — LaTeX Intelligent Localization Tool

[![Python 3.13+](https://img.shields.io/badge/python-3.13+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![CI](https://github.com/aleaz/lilt/actions/workflows/ci.yml/badge.svg)](https://github.com/aleaz/lilt/actions/workflows/ci.yml)
[![Status](https://img.shields.io/badge/status-public%20beta-orange.svg)](docs/concepts.md#maturity)

**Continuous LaTeX localization engine (CLI)** — local-first, structure-preserving, TM-backed, LLM-assisted.

LILT turns `.tex` **prose** into localized `.tex` without pasting raw structure into a chat model. It parses into **segments**, masks macros/math into **placeholders**, stores state in a **Translation Memory**, runs Draft → Critique → Refine, validates structure, then **rebuilds** the document. You compile the PDF yourself.

> **Not affiliated with [Lilt Inc.](https://lilt.com/) / lilt.com.**  
> The name is the acronym *LaTeX Intelligent Localization Tool*.  
> **Not** on PyPI as `lilt` (that name is another project). Install from Git; distribution package: **`latex-lilt`**; CLI: **`lilt`**.

## Who it is for

| Good fit | Not a fit |
|----------|-----------|
| Authors, translators, and maintainers of academic/technical LaTeX | Markdown / UI / app string i18n |
| People who run OpenAI-compatible LLMs (local or cloud) | CAT / WYSIWYG seekers; drag-and-drop SaaS |
| Incremental TM workflows with human review and Git-friendly JSONL | “Fire and forget” with no validation |
| Compile-minded integrity over blind fluency | Users of commercial [Lilt](https://lilt.com/) or `pip install lilt` |

## Why LILT

- **Integrity first** — placeholders and syntax validation before a translation is accepted.
- **Human priority** — `reviewed` / `approved` / `locked` are never auto-overwritten.
- **TM as source of truth** — append-oriented JSONL under `.lilt/tm/`.
- **Local-first LLM** — OpenAI-compatible endpoints (LM Studio, Ollama-style, or cloud) per stage.
- **Continuous** — re-sync when sources change; resume interrupted translates; checkpoints.

Not a generic CAT tool, not gettext/po4a, not a PDF compiler.

## Key features

- Multi-file LaTeX via `\input` / `\include` discovery on sync  
- Placeholder masking so the model sees prose, not raw structure  
- Reflection stages: **Draft → Critique → Refine** (or draft-only cost profiles)  
- Human **Review** queue and CSV/JSON export–import  
- Fail-closed **build** of localized `.tex` (optional `--allow-partial`)  
- TM inspect / budget / status tooling  

## How it works

```text
.tex  →  Sync (AST → segments + TM)
      →  Translate (LLM Draft → Critique → Refine + validation)
      →  Build (localized .tex)
      →  PDF (your TeX toolchain — not a lilt command)
```

More: [Concepts](docs/concepts.md). Runtime detail: [Architecture](docs/architecture/README.md).

## Quick start

Requires **Python 3.13+**, [`uv`](https://docs.astral.sh/uv/) or pipx, and an **OpenAI-compatible LLM** before `translate`.

Prefer the official sample: [`examples/quickstart/`](examples/quickstart/).

```bash
# Install (Git only — do not use `pip install lilt`)
# Tool install puts `lilt` on your PATH. From a clone, use `uv run lilt` instead.
uv tool install git+https://github.com/aleaz/lilt

cd your-latex-project
lilt project init
lilt project configure .

# Edit .lilt/lilt.yaml — set source_lang, target_lang, llm.base_url, llm.model
# Cloud keys: .lilt/.env (git-ignored)

lilt pipeline sync main.tex
lilt pipeline translate --all
mkdir -p i18n/build
lilt pipeline build main main.tex i18n/build/main.tex
# Success: i18n/build/main.tex exists. Compile PDF yourself if needed.
```

Full walkthrough: [Getting started](docs/getting-started.md) · [First translation](docs/guides/first-translation.md) · [Quick Start example](examples/quickstart/).

## Common use cases

| Scenario | Start here |
|----------|------------|
| Academic paper or book | [Getting started](docs/getting-started.md) |
| Multi-file project / resume after interrupt | [Workflows](docs/guides/workflows.md) |
| Local vs cloud LLM / stages / automation | [Advanced usage](docs/guides/advanced-usage.md) · [Configuration](docs/guides/configuration.md) |
| Human review & TM export | [Human review](docs/guides/human-review.md) |
| Stuck on errors | [Troubleshooting](docs/runbooks/troubleshooting.md) · [FAQ](docs/faq.md) |

## Supported capabilities

| Area | Support |
|------|---------|
| **Input** | LaTeX projects (multi-file, macros, math, citations — LaTeX-aware parsing) |
| **LLM** | OpenAI-compatible HTTP (`provider: openai`); per-stage models/endpoints |
| **Workflows** | Sync → translate → build; workflow or sequential modes; TM + review |
| **Integrations** | CLI + shell automation you own; no product SaaS orchestrator |
| **Limits** | No OCR/diagrams; no PDF CLI; no corpus/eval in this repo; Windows not first-class tested; public beta (CLI/config may change) |

Deferred ideas: [appendix-deferred](docs/architecture/appendix-deferred.md).

## Documentation

| Audience | Go to |
|----------|--------|
| **Users** | [Docs hub](docs/README.md) · [Getting started](docs/getting-started.md) · [Quick Start](examples/quickstart/) · [Guides](docs/guides/workflows.md) · [FAQ](docs/faq.md) |
| **Reference** | [CLI](docs/reference/cli.md) · [Config](docs/reference/config.md) |
| **Architecture** | [Architecture](docs/architecture/README.md) · [Glossary](docs/glossary.md) |
| **Developers** | [Developer Guide](docs/development/README.md) |
| **Contributors** | [CONTRIBUTING.md](CONTRIBUTING.md) · [Contributor Guide](docs/development/contributor-guide.md) |
| **Problems** | [Troubleshooting](docs/runbooks/troubleshooting.md) · [SUPPORT.md](SUPPORT.md) |

## Development

```bash
git clone https://github.com/aleaz/lilt && cd lilt
uv sync
make ci    # matches GitHub Actions
```

Details: [Development overview](docs/development/overview.md). Process: [CONTRIBUTING.md](CONTRIBUTING.md).

## Project status

**Public beta** ([CHANGELOG](CHANGELOG.md) still **Unreleased** — no git tag yet). Core pipeline (sync, translate, build, review, TM, telemetry) is implemented and tested. Treat pre-release as SemVer-unstable: CLI and config may still change. See [maturity](docs/concepts.md#maturity).

## Community and contribution

- Contribute: [CONTRIBUTING.md](CONTRIBUTING.md) · [Code of Conduct](CODE_OF_CONDUCT.md)  
- Questions vs bugs: [SUPPORT.md](SUPPORT.md)  
- Security: [SECURITY.md](SECURITY.md)  

## License

LILT is released under the [MIT License](LICENSE).

Copyright (c) 2026 Alejandro Azario
