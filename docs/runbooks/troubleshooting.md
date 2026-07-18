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

---
