# multifile-input

| Field | Value |
|-------|-------|
| `asset_id` | `multifile-input` |
| Path | `validation/document-types/multifile-input/` |
| Status | `accepted` |
| Owner | Maintainer of `latex-lilt` |
| Family / level | D-MULTI · L2 |
| Engine | `pdflatex` |
| Sync root | `main.tex` |
| Mode | CV (primary); RV optional |

## Purpose

Prove `\input` trees sync to expected namespaces from a declared root, with
stable path encoding (CL-120, CL-123).

## Covered Validation Claims

| Claim | How observed |
|-------|----------------|
| CL-120 | Sync root `main.tex` discovers children; exit 0; multiple namespaces under `.lilt/tm/` |
| CL-123 | Namespace IDs correspond to encoded relative paths (e.g. root + `chapters/intro`, `chapters/methods`) without collision |

## Non-goals

`subfiles` (see `multifile-subfiles`); partial-fail messaging (workflow); beamer.

## Expected execution

```bash
uv run lilt -C validation/document-types/multifile-input project init
uv run lilt -C validation/document-types/multifile-input project configure .
uv run lilt -C validation/document-types/multifile-input pipeline sync main.tex
uv run lilt -C validation/document-types/multifile-input tm status
```

Expect ≥1 namespace beyond a single-file project. Optional `pdflatex main.tex`.

## Related

[../HUB_STATUS.md](../HUB_STATUS.md) · [../../CLAIMS.md](../../CLAIMS.md)
