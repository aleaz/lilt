# Getting started (Quick Start)

Get from zero to a **rebuilt localized `.tex`** as fast as possible. No architecture — just a successful first run.

Expanded walkthrough: [First translation](guides/first-translation.md). Hub: [Documentation](README.md).

## Before you start

| Need | Notes |
|------|-------|
| **Python 3.13+** | Required |
| **`uv` or `pipx`** | Install the CLI |
| **LaTeX sources** | A project directory with at least one `.tex` file — or use the [official Quick Start](../examples/quickstart/) |
| **OpenAI-compatible LLM** | Required for `translate` (local or cloud) |
| **TeX distribution** | Optional — only if you will compile PDF yourself |

> **Not on PyPI as `lilt`.** That name is another project. Install from Git. Distribution package: **`latex-lilt`**. CLI command: **`lilt`**.

## 1. Install

**Recommended (tool install):**

```bash
uv tool install git+https://github.com/aleaz/lilt
lilt --version
```

After pulling a newer `main`, refresh the tool install (`uv tool upgrade` /
reinstall) so `PATH` does not keep an old shim. When developing from a clone,
prefer `uv run lilt` — see [Contributor guide](development/contributor-guide.md).

Or with pipx:

```bash
pipx install git+https://github.com/aleaz/lilt
```

**From source (editable):**

```bash
git clone https://github.com/aleaz/lilt
cd lilt
uv sync
uv run lilt --version
```

## 2. Initialize your LaTeX project

```bash
cd /path/to/your-latex-project
lilt project init
lilt project configure .    # optional but recommended — discovers custom macros
```

This creates `.lilt/lilt.yaml`, `.lilt/.env`, and `.lilt/tm/` beside your sources.

## 3. Configure the LLM (required before translate)

Edit `.lilt/lilt.yaml`. Set languages and an OpenAI-compatible endpoint. Example (local LM Studio / Ollama-style):

```yaml
project:
  source_lang: en
  target_lang: es

llm:
  provider: openai
  base_url: "http://localhost:1234/v1"
  model: "your-model-id"
  api_key_env: "OPENAI_API_KEY"   # often unused for local servers
```

For cloud APIs, put the key in `.lilt/.env` (git-ignored), for example:

```bash
echo 'OPENAI_API_KEY=sk-...' >> .lilt/.env
```

More topologies: [Configuration guide](guides/configuration.md). If translate fails immediately: [Troubleshooting](runbooks/troubleshooting.md).

## 4. First execution

Replace `main.tex` with your project’s root file if needed:

```bash
lilt pipeline sync main.tex
lilt pipeline translate --all
mkdir -p i18n/build
lilt pipeline build main main.tex i18n/build/main.tex
```

## 5. Expected result

| Check | Success looks like |
|-------|-------------------|
| Sync | TM files under `.lilt/tm/` (e.g. `main.jsonl`) |
| Translate | Segments progress toward translated statuses (`tm status`) |
| Build | File `i18n/build/main.tex` exists with localized prose |
| PDF | **Not** produced by LILT — compile `i18n/build/main.tex` yourself if you need PDF |

**Default build is fail-closed:** it fails if segments are still `generated`, `drafted`, `critiqued`, `conflict`, or `error`. Buildable statuses include `refined`, `reviewed`, `approved`, and `locked`. See [First translation](guides/first-translation.md) if build refuses incomplete work.

## 6. Next steps

| Goal | Go to |
|------|--------|
| Official Quick Start (~2–3 page note) | [examples/quickstart](../examples/quickstart/) |
| Same path with more explanation | [First translation](guides/first-translation.md) |
| Resume, conflicts, multi-file, TM | [Workflows](guides/workflows.md) |
| Human approve / export-import | [Human review](guides/human-review.md) |
| Modes, stages, automation | [Advanced usage](guides/advanced-usage.md) |
| Stuck? | [Troubleshooting](runbooks/troubleshooting.md) · [FAQ](faq.md) · [Recovery](runbooks/recovery.md) |
| What / why (user view) | [Concepts](concepts.md) |
| Exact flags | [CLI reference](reference/cli.md) |

---

### Workspace layout (reference)

```text
your-latex-project/
├── .lilt/
│   ├── lilt.yaml
│   ├── .env
│   ├── tm/                 # Translation Memory (JSONL)
│   ├── telemetry.db
│   └── lilt.log            # with --debug
├── main.tex
└── ...
```

Namespaces come from encoded relative paths (e.g. `chapters/intro.tex` → `chapters__intro`).
