# sync-partial-fail

| Field | Value |
|-------|-------|
| `asset_id` | `sync-partial-fail` |
| Path | `validation/workflow/sync-partial-fail/` |
| Status | `accepted` |
| Owner | Maintainer of `latex-lilt` |
| Family / level | W-SYNC · L2 |
| Engine | `pdflatex` (optional; sync fail is the claim) |
| Sync root | `main.tex` |
| Mode | CV |

Hub: [../HUB_STATUS.md](../HUB_STATUS.md)

## Purpose

Prove mid-tree sync failure reports **already-updated namespaces** (no silent
half-success) — CL-122. Engineered via namespace collision (`parts/x.tex` vs
`parts__x.tex`), not Recovery interrupt/lease scenarios.

## Covered Validation Claims

| Claim | How observed |
|-------|----------------|
| CL-122 | `pipeline sync main.tex` errors with `Partial sync: already updated namespaces: […]` after `main` / `ok` succeed; nested `parts/x` hits namespace collision with flat `parts__x.tex` |

## Expected execution (CV)

```bash
DIR=validation/workflow/sync-partial-fail
uv run lilt -C "$DIR" project init
uv run lilt -C "$DIR" project configure .
uv run lilt -C "$DIR" pipeline sync main.tex
# Expect: ConfigurationError / panel with Partial sync: already updated namespaces
```

Translate / review / Recovery: **N/A**.

## Non-goals

Happy-path multifile (`document-types/multifile-input`); lease reclaim; translate interrupt.

## Related

[../HUB_STATUS.md](../HUB_STATUS.md) · [../../CLAIMS.md](../../CLAIMS.md)
