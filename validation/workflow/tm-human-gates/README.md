# tm-human-gates

| Field | Value |
|-------|-------|
| `asset_id` | `tm-human-gates` |
| Path | `validation/workflow/tm-human-gates/` |
| Status | `accepted` |
| Owner | Maintainer of `latex-lilt` |
| Family / level | W-TM · L2 |
| Engine | `pdflatex` (optional) |
| Sync root | `main.tex` |
| Mode | CV (primary); RV translate N/A when no LLM |

Hub: [../HUB_STATUS.md](../HUB_STATUS.md)

## Purpose

Prove human statuses (`reviewed` / `approved` / `locked`) are not clobbered,
source edits on protected segments with translations yield `conflict`, and
`tm status` counts are honest (CL-141, CL-142, CL-143).

## Covered Validation Claims

| Claim | How observed |
|-------|----------------|
| CL-141 | `tm set-status` → `refined` then seed human translation + `reviewed`; re-sync **without** source edit keeps `reviewed` |
| CL-142 | Minor source edit of protected+translated prose → sync reports conflict (carryover); `tm list --status conflict` non-empty |
| CL-143 | `tm status` counts match inventory (conflict/reviewed/generated/deprecated as applicable) |

## Expected execution (CV)

```bash
DIR=validation/workflow/tm-human-gates
uv run lilt -C "$DIR" project init
uv run lilt -C "$DIR" project configure .
uv run lilt -C "$DIR" pipeline sync main.tex
uv run lilt -C "$DIR" tm list main
# Use segment id for "gate sentence one":
uv run lilt -C "$DIR" tm set-status main <SEG_ID> refined
# Seed a human translation on that segment (required for identity carryover),
# then set status reviewed — e.g. edit .lilt/tm/main.jsonl translation field
# or use `tm import` with a one-row file. Documented seed is operator-local.
uv run lilt -C "$DIR" pipeline sync main.tex
uv run lilt -C "$DIR" tm list main --status reviewed   # CL-141 still reviewed

# CL-142: change only the last letter of sentence one in main.tex (keep similarity), then:
uv run lilt -C "$DIR" pipeline sync main.tex
uv run lilt -C "$DIR" tm list main --status conflict
uv run lilt -C "$DIR" tm status   # CL-143
```

**Note:** Segment IDs are content-hash based; carryover to `conflict` requires a
non-empty translation on the prior human-protected segment (product behavior).

Review queue / import validation: **N/A** (Human Review hub). LLM translate: **N/A** when unavailable (seed translation instead). Recovery: **N/A**.

## Non-goals

`pipeline review` / import claims; session leases; smoke full translate path.

## Related

[../HUB_STATUS.md](../HUB_STATUS.md) · [../../CLAIMS.md](../../CLAIMS.md)
