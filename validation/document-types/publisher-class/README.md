# publisher-class

| Field | Value |
|-------|-------|
| `asset_id` | `publisher-class` |
| Path | `validation/document-types/publisher-class/` |
| Status | `accepted` |
| Owner | Maintainer of `latex-lilt` |
| Family / level | D-PUB · L2 |
| Engine | `pdflatex` |
| Sync root | `main.tex` |
| Mode | CV |
| Representative class | `IEEEtran` (conference) — present in TeX Live 2026 |

## Purpose

Prove a publisher/document class preamble (IEEEtran) survives sync without
being normalized to `article` (CL-200).

## Covered Validation Claims

| Claim | How observed |
|-------|----------------|
| CL-200 | After sync: `\documentclass[...]{IEEEtran}` and IEEE author/abstract constructs remain; `pdflatex` compiles |

## Non-goals

Full IEEE paper length; biblatex scholarly stack; Xe engine.

## Expected execution

```bash
uv run lilt -C validation/document-types/publisher-class project init
uv run lilt -C validation/document-types/publisher-class project configure .
uv run lilt -C validation/document-types/publisher-class pipeline sync main.tex
pdflatex -interaction=nonstopmode main.tex
```

## Related

[../HUB_STATUS.md](../HUB_STATUS.md) · [../../CLAIMS.md](../../CLAIMS.md)
