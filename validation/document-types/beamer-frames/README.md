# beamer-frames

| Field | Value |
|-------|-------|
| `asset_id` | `beamer-frames` |
| Path | `validation/document-types/beamer-frames/` |
| Status | `accepted` |
| Owner | Maintainer of `latex-lilt` |
| Family / level | D-BEAM · L2 |
| Engine | `pdflatex` |
| Sync root | `main.tex` |
| Mode | CV and RV |

Hub status: [../HUB_STATUS.md](../HUB_STATUS.md).

## Purpose

Prove beamer `frame` structure and common overlays survive sync/mask; titles/body
can translate under RV without breaking frames (CL-110, CL-111, CL-112).

## Covered Validation Claims

| Claim | How observed |
|-------|----------------|
| CL-110 | After sync: `\begin{frame}`/`\end{frame}` pairing intact in source/TM |
| CL-111 | Overlay specs (`\item<1->`) do not corrupt structure after sync |
| CL-112 | RV: frame titles/body translate; frames still well-formed after build |

## Non-goals

Scholarly bib/floats, TikZ, multifile, Xe/polyglossia.

## Expected execution

```bash
uv run lilt -C validation/document-types/beamer-frames project init
uv run lilt -C validation/document-types/beamer-frames project configure .
uv run lilt -C validation/document-types/beamer-frames pipeline sync main.tex
mkdir -p validation/document-types/beamer-frames/i18n/build
uv run lilt -C validation/document-types/beamer-frames \
  pipeline build main main.tex i18n/build/main.tex
# CV: expect fail-closed without translations
```

RV: `pipeline translate --all` then build (local LLM). Optional: `pdflatex main.tex`.

## Success / failure

- Success: sync exit 0; frames/overlays preserved; RV build keeps frame envs.
- Failure: broken `\begin{frame}` pairing; overlays destroy placeholders.

## Related

[../HUB_STATUS.md](../HUB_STATUS.md) · [../../CLAIMS.md](../../CLAIMS.md) · gold standard `validation/smoke/article-l1-smoke/`
