# Getting started

## Prerequisites and install

### Prerequisites

| Requirement | Required for | Notes |
|-------------|--------------|-------|
| **Python 3.13+** | All commands | Enforced in `pyproject.toml` |
| **uv** or **pipx** | Installation | `uv` is the project-standard tool |
| **TeX Live / MacTeX / MiKTeX** | Manual PDF compilation | Not required for sync/translate/build |
| **Git** | Recommended | TM JSONL files are version-control friendly |

### Global Install (recommended)

> **Not on PyPI as `lilt`.** That name is taken by another project. Install from
> Git. The distribution name is `latex-lilt`; the CLI command remains `lilt`.

```bash
uv tool install git+https://github.com/aleaz/lilt
```

Or with pipx:

```bash
pipx install git+https://github.com/aleaz/lilt
```

### Editable Install from Source

```bash
git clone https://github.com/aleaz/lilt
cd lilt
uv sync
uv run lilt --help
```

### Development Install

```bash
git clone https://github.com/aleaz/lilt
cd lilt
uv sync          # installs runtime + dev dependencies
source .venv/bin/activate   # optional, for IDE integration
```

### Platform Notes

- **macOS / Linux:** Fully supported. File locks use `filelock` (POSIX-safe).
- **Windows:** Not explicitly tested; path handling uses `os.path` throughout.

---

## Workspace layout

Running `lilt project init` creates:

```text
your-latex-project/
├── .lilt/
│   ├── lilt.yaml          # Main configuration (typed, validated)
│   ├── .env               # API keys (git-ignored)
│   ├── .gitignore         # Ignores *.db, .env, lilt.log
│   ├── tm/                # Translation Memory (JSONL per namespace)
│   │   ├── main.jsonl
│   │   └── chapters__intro.jsonl
│   ├── telemetry.db       # LLM inference telemetry (SQLite)
│   └── lilt.log           # Debug log (when .lilt exists)
├── main.tex
└── ...
```

Namespaces are derived from encoded relative `.tex` paths (e.g. `chapters/intro.tex` → `chapters__intro.jsonl`).

## First sync → translate → build

From your LaTeX project directory:

```bash
# 1. Initialize workspace
lilt project init

# 2. Discover custom macros (optional but recommended)
lilt project configure .
```

### Configure LLM (required before translate)

Edit `.lilt/lilt.yaml` so `llm.base_url` and `llm.model` point at an
OpenAI-compatible server. Local example (LM Studio / Ollama):

```yaml
llm:
  base_url: "http://localhost:1234/v1"
  model: "your-model-id"
  api_key_env: "OPENAI_API_KEY"   # often unused for local servers
```

For cloud providers, set the API key in `.lilt/.env` or a workspace `.env`
(both are git-ignored). Details: [Configuration guide](guides/configuration.md).
If translate fails immediately, see [Troubleshooting](runbooks/troubleshooting.md).

```bash
# 3. Parse source and populate Translation Memory
lilt pipeline sync main.tex

# 4. Translate all namespaces
lilt pipeline translate --all

# 5. Build translated output into a shadow directory
mkdir -p i18n/build
lilt pipeline build main main.tex i18n/build/main.tex
```

Review and approve translations:

```bash
lilt pipeline review main
```

---

## Next steps

- [Concepts](concepts.md)
- [Workflows](guides/workflows.md)
- [Configuration guide](guides/configuration.md)
- [CLI reference](reference/cli.md)
