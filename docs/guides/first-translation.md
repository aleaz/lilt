# First translation

**Goal:** Complete one successful sync → translate → build cycle and understand what you produced.

Shorter path: [Getting started](../getting-started.md). Commands catalog: [CLI reference](../reference/cli.md).

## Prerequisites

- `lilt` installed (`lilt --version` works)
- A LaTeX project directory you can write to
- An OpenAI-compatible LLM reachable at the `base_url` you will configure

## Environment

```bash
cd /path/to/your-latex-project
# Prefer a git repo so you can track .lilt/tm/*.jsonl
```

Use your real root `.tex` below wherever you see `main.tex` / namespace `main`.

## Steps

### 1. Initialize and discover macros

```bash
lilt project init
lilt project configure .
```

**Expected:** `.lilt/lilt.yaml` and `.lilt/.env` exist. Configure may update macro lists in yaml.

### 2. Set languages and LLM

Edit `.lilt/lilt.yaml` so at least `project.source_lang`, `project.target_lang`, `llm.base_url`, and `llm.model` are set. Cloud keys go in `.lilt/.env`.

**Expected:** Config is non-empty and matches your endpoint. Empty yaml is not a valid “defaults” setup.

### 3. Sync source into Translation Memory

```bash
lilt pipeline sync main.tex
```

**Expected:** Namespaces appear under `.lilt/tm/`. `\input{}` / `\include{}` dependencies are crawled from the root file.

**Agent / state check:** After sync, `lilt tm list` shows namespaces; segments exist with machine-ready statuses (typically `generated` for new text).

### 4. Translate

```bash
lilt pipeline translate --all
```

**Expected:** LLM calls succeed; progress visible via:

```bash
lilt tm status --all
```

**Recovery:** Connection/401 → [Troubleshooting](../runbooks/troubleshooting.md#missing-api-key). Interrupted run → re-run the same `translate` command ([Workflows — resume](workflows.md#scenario-resume-an-interrupted-translation)).

### 5. Build localized `.tex`

```bash
mkdir -p i18n/build
lilt pipeline build main main.tex i18n/build/main.tex
```

**Expected:** `i18n/build/main.tex` written when segments are in **buildable** statuses (`refined`, `reviewed`, `approved`, `locked`).

If build fails because work is incomplete, finish translate/review first, or (advanced) see `--allow-partial` in [Advanced usage](advanced-usage.md).

### 6. Optional: skim review

```bash
lilt pipeline review main
```

Interactive prompts: approve / edit / reject / skip / quit. Detail: [Human review](human-review.md).

## What happened (short explanation)

1. **Sync** parsed LaTeX into **segments** stored in JSONL TM (structure stays out of the raw model prompt via placeholders).
2. **Translate** asked your LLM to draft (and, by default, critique/refine) eligible segments.
3. **Build** stitched accepted translations back into a `.tex` file.

You compile PDF **outside** LILT if you need it.

## Common mistakes

| Mistake | Fix |
|---------|-----|
| `pip install lilt` | Install from Git — dist is `latex-lilt` |
| Translate before LLM config | Set `base_url` / `model` (+ key if cloud) |
| Build before segments are buildable | Check `lilt tm status`; finish translate |
| Expecting PDF from CLI | Compile `i18n/build/…` yourself |
| Parallel `sync` + `translate` on same namespace | Run one writer at a time |
| Wrong work directory | Use `-C /path/to/project` or `cd` first |

## Next steps

- [Workflows](workflows.md) — full project, resume, TM, debug  
- [Human review](human-review.md) — approve and export/import  
- [Advanced usage](advanced-usage.md) — modes, stages, automation  
- [Concepts](../concepts.md) — product model without L1 depth  

### AI-oriented summary

| Item | Value |
|------|--------|
| Required steps | init → configure LLM → sync → translate → build |
| Expected state after success | Localized `.tex` under `i18n/build/`; TM JSONL under `.lilt/tm/` |
| Key commands | `project init`, `pipeline sync`, `pipeline translate --all`, `pipeline build` |
| Common errors | Not initialized; 401/LLM down; fail-closed build; NamespaceBusyError |
| Recovery | troubleshooting runbook; re-run translate; `tm list --status error` |
