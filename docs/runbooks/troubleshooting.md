# Troubleshooting

### Missing API Key

**Symptom:** LLM connection errors or 401 responses.

**Fix:** Set `OPENAI_API_KEY` in `.lilt/.env` or pass `api_key` in `llm.stages` for cloud providers. Verify `base_url` matches your provider.

### Workspace Not Initialized

**Symptom:** `Not initialized. Workspace '...' lacks a .lilt/lilt.yaml config.`

**Fix:** Run `lilt project init` from your LaTeX project root.

### `TMCorruptionError` on Load

**Symptom:** `Corrupt TM line N in '...'`.

**Fix:** Run `lilt tm admin repair NAMESPACE` to skip bad lines and compact. Original file is backed up as `*.corrupt-<timestamp>`.

### Partial Sync

**Symptom:** `Partial sync: already updated namespaces: [...]` after a multi-file sync failure.

**Fix:** The listed namespaces were written before the failure. Fix the failing `.tex` (or dependency), then re-run `lilt pipeline sync` on the root file. No automatic rollback.

### `NamespaceBusyError`

**Symptom:** `Namespace '...' is in use by another operation.`

**Fix:** Wait for the other `lilt` process to finish. Only one mutating operation per namespace is allowed at a time. Do not run `sync` and `translate` in parallel on the same namespace.

### Placeholder Mismatch / Validation Failure

**Symptom:** Segment marked `conflict`; `Placeholder mismatch` in logs.

**Fix:** Edit the segment manually (`lilt pipeline edit`) ensuring all `<macro id="N"/>` tags are preserved exactly. Re-sync if placeholder maps are stale: `lilt pipeline sync main.tex`.

### Build Emits Untranslated Source

**Symptom:** English text in output despite TM having translations.

**Causes:**

- Segment status is `generated` or `conflict` (not in buildable statuses).
- Source changed without re-sync (segment ID no longer matches).
- Missing placeholder map: run `lilt pipeline sync`.

### PDF Shows `???` for References

**Symptom:** Unresolved cross-references or citations in compiled PDF.

**Fix:** Standard LaTeX multi-pass compilation. From the shadow directory:

```bash
cd i18n/build/
TEXINPUTS=".:../../:" pdflatex main.tex
BSTINPUTS=".:../../:" BIBINPUTS=".:../../:" bibtex main
TEXINPUTS=".:../../:" pdflatex main.tex
TEXINPUTS=".:../../:" pdflatex main.tex
```

### Before real testing

Checklist for a careful first run on a real project (single writer, explicit config):

1. **Config** — Ensure `.lilt/lilt.yaml` is non-empty and sets at least `project.source_lang` / `project.target_lang` and `llm.base_url` / `llm.model` for your endpoint. An empty file raises `ConfigurationError` (no silent Spanish/localhost defaults).
2. **One writer per namespace** — Do not run `sync` and `translate` in parallel on the same namespace (`NamespaceBusyError`).
3. **Resume mid-pipeline** — After `--stage draft`, continue with `--stage critique` then `--stage refine`. In workflow mode, `--force` only expands **draft** eligibility; `--force --stage refine` alone will not invent `critiqued` artifacts.
4. **Sequential vs workflow** — Sequential `--force` re-runs full D→C→R on non-immutable segments; workflow stage resume is safer for partial progress.
5. **Namespace paths** — Avoid filenames that collide under `__` encoding (e.g. `chapters/intro.tex` vs `chapters__intro.tex`); sync fails loud when collisions exist.
6. **Flaky local LLMs** — Raise `llm.draft_empty_retries` (default `1`) if empty drafts are common; garbage critique JSON marks the segment `conflict` instead of feeding refine.
7. **Partial sync** — If multi-file sync fails mid-way, fix the failing `.tex` and re-sync; already-updated namespaces are listed in the error (no automatic rollback).

---
