# pkg-tikz-pgfplots

| Field | Value |
|-------|-------|
| `asset_id` | `pkg-tikz-pgfplots` |
| Path | `validation/packages/pkg-tikz-pgfplots/` |
| Status | `accepted` |
| Owner | Maintainer of `latex-lilt` |
| Family / level | B-TIKZ · L2 |
| Packages | `tikz`, `pgfplots` |
| Engine | `pdflatex` |
| Sync root | `main.tex` |
| Mode | CV and RV |

Hub status: [../HUB_STATUS.md](../HUB_STATUS.md).

## Purpose

Prove `tikzpicture` and PGFPlots `axis` bodies are opaque / not sent as prose
(CL-031, CL-090, CL-091) and that sync/build preserve opaque regions (CL-092).
Graphics are intentionally minimal — parser/build validation, not visual quality.

## Covered Validation Claims

| Claim | How observed |
|-------|----------------|
| CL-031 | After sync: opaque env bodies are placeholders in TM, not free linguistic segments |
| CL-090 | `tikzpicture` content masked as `<env>` (or equivalent) |
| CL-091 | `axis` content masked; if leakage, asset YAML sets `parser.opaque_environments: [axis]` |
| CL-092 | CV: sync exit 0; fail-closed build; source still contains `tikzpicture` / `axis` |

## Non-goals

Externalization, circuitikz, minted, shell-escape, showcase plots.

## Expected execution

```bash
uv run lilt -C validation/packages/pkg-tikz-pgfplots project init
uv run lilt -C validation/packages/pkg-tikz-pgfplots project configure .
# If axis leaks into TM: set parser.opaque_environments to include axis in .lilt/lilt.yaml
uv run lilt -C validation/packages/pkg-tikz-pgfplots pipeline sync main.tex
mkdir -p validation/packages/pkg-tikz-pgfplots/i18n/build
uv run lilt -C validation/packages/pkg-tikz-pgfplots \
  pipeline build main main.tex i18n/build/main.tex
pdflatex -interaction=nonstopmode -output-directory=validation/packages/pkg-tikz-pgfplots \
  validation/packages/pkg-tikz-pgfplots/main.tex
```

RV: `pipeline translate --all` then build when local LLM is available; else N/A.
Review queue: N/A for these primaries.

## Success / failure

- Success: opaque placeholders for picture/axis; PDF without `-shell-escape`.
- Failure: plot/path markup appears as ordinary translatable prose in TM.

## Related

[../HUB_STATUS.md](../HUB_STATUS.md) · [../../CLAIMS.md](../../CLAIMS.md) · gold standard `validation/smoke/article-l1-smoke/`
