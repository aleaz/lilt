# pkg-listings

| Field | Value |
|-------|-------|
| `asset_id` | `pkg-listings` |
| Path | `validation/packages/pkg-listings/` |
| Status | `accepted` |
| Owner | Maintainer of `latex-lilt` |
| Family / level | B-LIST · L2 |
| Packages | `listings` |
| Engine | `pdflatex` |
| Sync root | `main.tex` |
| Mode | CV and RV |

Hub status: [../HUB_STATUS.md](../HUB_STATUS.md).

## Purpose

Prove `lstlisting` body is opaque to the LLM path (CL-100) and that listing
**captions** remain translatable under RV (CL-102). No shell-escape.

## Covered Validation Claims

| Claim | How observed |
|-------|----------------|
| CL-100 | After sync: listing body appears as opaque `<env>` (or equivalent) in TM — not raw `def add` prose sent as a free segment |
| CL-102 | RV: figure `\caption` outside `lstlisting` translates; listing env/code body remain intact after build |

## Non-goals

minted, TikZ, scholarly stack, shell-escape.

## Expected execution

```bash
uv run lilt -C validation/packages/pkg-listings project init
uv run lilt -C validation/packages/pkg-listings project configure .
uv run lilt -C validation/packages/pkg-listings pipeline sync main.tex
mkdir -p validation/packages/pkg-listings/i18n/build
uv run lilt -C validation/packages/pkg-listings \
  pipeline build main main.tex i18n/build/main.tex
# CV: expect fail-closed without translations
pdflatex -interaction=nonstopmode -output-directory=validation/packages/pkg-listings \
  validation/packages/pkg-listings/main.tex
```

RV: `pipeline translate --all` then build (local LLM). Review queue: N/A for these primaries.

## Success / failure

- Success: sync exit 0; code body opaque; PDF compiles without `-shell-escape`.
- Failure: listing body appears as ordinary translatable prose in TM; caption lost after RV.

## Related

[../HUB_STATUS.md](../HUB_STATUS.md) · [../../CLAIMS.md](../../CLAIMS.md) · gold standard `validation/smoke/article-l1-smoke/`
