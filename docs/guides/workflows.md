# Workflows

### 1. Initialize a New Workspace

```bash
cd my-paper/
git init                    # recommended
lilt project init
lilt project configure .
# Edit .lilt/lilt.yaml: set target_lang, base_url, model
# Edit .lilt/.env: set OPENAI_API_KEY if using cloud models
```

### 2. Translate a Project

```bash
lilt pipeline sync main.tex          # crawls \input{} dependencies
lilt pipeline translate --all
lilt pipeline review main            # human approval loop
mkdir -p i18n/build
lilt pipeline build main main.tex i18n/build/main.tex
```

### 3. Resume After Interruption

Translation checkpoints append each segment to JSONL during a run. If the process is interrupted (`Ctrl+C`), completed segments are persisted. Re-run:

```bash
lilt pipeline translate --all
```

Only `generated` and `error` segments are picked up by default. Use `--force` to re-translate specific segments.

### 4. Manage TM Conflicts

When source text changes on a human-protected segment, sync marks it `conflict`:

```bash
lilt pipeline sync main.tex          # reports new conflicts
lilt tm list main --status conflict
lilt pipeline edit main <segment_id> # resolve manually
# Or reject in review:
lilt pipeline review main
```

## See also

- [Human review](human-review.md)
- [CLI reference](../reference/cli.md)
