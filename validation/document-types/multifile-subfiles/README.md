# multifile-subfiles

| Field | Value |
|-------|-------|
| `asset_id` | `multifile-subfiles` |
| Path | `validation/document-types/multifile-subfiles/` |
| Status | `accepted` |
| Owner | Maintainer of `latex-lilt` |
| Family / level | D-MULTI · L2 |
| Engine | `pdflatex` |
| Sync root | `main.tex` (subfiles master) |
| Mode | CV |

## Purpose

Prove the `subfiles` master/root workflow syncs without path escape: syncing
the declared master discovers `\subfile` children into TM namespaces (CL-121).

## Covered Validation Claims

| Claim | How observed |
|-------|----------------|
| CL-121 | Sync `main.tex`; namespaces include `main` and `child`; paths stay under the asset workspace |

## Non-goals

Plain `\input` trees (`multifile-input`); workflow partial-fail (CL-122).

## Expected execution

```bash
uv run lilt -C validation/document-types/multifile-subfiles project init
uv run lilt -C validation/document-types/multifile-subfiles project configure .
uv run lilt -C validation/document-types/multifile-subfiles pipeline sync main.tex
uv run lilt -C validation/document-types/multifile-subfiles tm status
```

Optional: `pdflatex main.tex` and `pdflatex child.tex`.

## Related

[../HUB_STATUS.md](../HUB_STATUS.md) · [../../CLAIMS.md](../../CLAIMS.md)
