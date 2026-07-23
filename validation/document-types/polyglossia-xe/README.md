# polyglossia-xe

| Field | Value |
|-------|-------|
| `asset_id` | `polyglossia-xe` |
| Path | `validation/document-types/polyglossia-xe/` |
| Status | `accepted` |
| Owner | Maintainer of `latex-lilt` |
| Family / level | D-ENGINE · L2 |
| Engine | `xelatex` |
| Sync root | `main.tex` |
| Mode | CV (primary); RV optional |

## Purpose

Prove XeLaTeX + polyglossia (+ fontspec) preamble and bilingual stub survive
sync; engine/build path differs from pdfLaTeX article (CL-191, CL-201).

## Covered Validation Claims

| Claim | How observed |
|-------|----------------|
| CL-191 | Sync exit 0; polyglossia/fontspec preamble lines remain; language envs intact |
| CL-201 | Documented engine is `xelatex`; source compiles with `xelatex main.tex` after sync |

## Non-goals

pdfLaTeX article scholarly stack; publisher classes; beamer.

## Expected execution

```bash
uv run lilt -C validation/document-types/polyglossia-xe project init
uv run lilt -C validation/document-types/polyglossia-xe project configure .
uv run lilt -C validation/document-types/polyglossia-xe pipeline sync main.tex
xelatex -interaction=nonstopmode -output-directory=. main.tex
```

Configure target language as needed for RV. Prefer system fonts via fontspec defaults.

## Related

[../HUB_STATUS.md](../HUB_STATUS.md) · [../../CLAIMS.md](../../CLAIMS.md)
