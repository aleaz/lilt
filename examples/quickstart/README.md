# Quick Start

Produce a **localized `.tex`** (and optionally a PDF) from this short technical
note—without pasting raw LaTeX into a chat window.

This folder is the **official onboarding example** for LILT (LaTeX Intelligent
Localization Tool).

## Why this exists

- **Integrity first** — math, refs, cites, floats, and macros are masked and
  validated so translations cannot casually destroy structure.
- **Translation Memory** — segments live in Git-friendly JSONL under `.lilt/tm/`.
- **Local-first LLM** — any OpenAI-compatible endpoint (LM Studio, Ollama-style,
  or cloud) can drive Draft → Critique → Refine.

You should finish knowing *why* LILT exists before reading architecture docs.

## Prerequisites

| Need | Notes |
|------|-------|
| Python 3.13+ | Required |
| `uv` or `pipx` | Install the CLI |
| OpenAI-compatible LLM | Required for `pipeline translate` |
| TeX distribution | Optional — only to compile PDF yourself |

## Install

**Not on PyPI as `lilt`** (that name is another project). Distribution package:
`latex-lilt`. CLI command: `lilt`.

```bash
uv tool install git+https://github.com/aleaz/lilt
lilt --version
```

From a clone of this repository (editable):

```bash
cd /path/to/lilt
uv sync
uv run lilt --version
```

## Run

Work **inside this directory** (`examples/quickstart/`):

```bash
lilt project init
lilt project configure .    # discovers custom macros in main.tex
```

Edit `.lilt/lilt.yaml`: set `project.source_lang` / `target_lang` and point
`llm.base_url` / `llm.model` at your server. Put API keys only in `.lilt/.env`
(gitignored)—never in this tree.

```bash
lilt pipeline sync main.tex
lilt pipeline translate --all
mkdir -p i18n/build
lilt pipeline build main main.tex i18n/build/main.tex
```

Compile PDF yourself if you want it:

```bash
pdflatex i18n/build/main.tex
# or: latexmk -pdf i18n/build/main.tex
```

## Expected outputs

| Step | Success looks like |
|------|-------------------|
| Sync | TM under `.lilt/tm/` (e.g. `main.jsonl`) with placeholders for math/refs/cites |
| Translate | Segments reach buildable statuses (often `refined`) |
| Build | `i18n/build/main.tex` with localized prose |
| PDF | Your TeX toolchain; **not** a `lilt` command |

Default build is **fail-closed** until segments are buildable (`refined`,
`reviewed`, `approved`, or `locked`).

## What to compare

Open `main.tex` (English) next to `i18n/build/main.tex` (target language):

- Abstract and section prose should be translated.
- Inline/display math, `\ref` / `\eqref` / `\pageref`, `\cite`, table/figure
  structure, footnote marker, and the hyperlink target should remain intact.

That contrast *is* the product value.

## Time expectations

With `cost_profile: balanced`, each segment may take **several LLM calls**
(Draft → Critique → Refine). A local mid-size model on this note is often on
the order of **a few minutes**, not a few seconds.

For a faster first win, set in `.lilt/lilt.yaml`:

```yaml
llm:
  cost_profile: draft_only
```

## Next

- [Getting started](../../docs/getting-started.md)
- [First translation](../../docs/guides/first-translation.md)
- [Documentation hub](../../docs/README.md)
- [CLI reference](../../docs/reference/cli.md)

## Notes

- No secrets ship in this example.
- CI does not run translate against this sample automatically.
- Generated `.lilt/`, `i18n/`, and TeX auxiliaries are gitignored here.
