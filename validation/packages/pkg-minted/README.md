# pkg-minted

| Field | Value |
|-------|-------|
| `asset_id` | `pkg-minted` |
| Path | `validation/packages/pkg-minted/` |
| Status | `accepted` |
| Owner | Maintainer of `latex-lilt` |
| Family / level | B-MINT · L2 |
| Packages | `minted` |
| Engine | `pdflatex` (PDF only with `-shell-escape`) |
| Sync root | `main.tex` |
| Support tier | **Supported during Release Validation only** |
| Mode | CV sync (no shell-escape); RV env-gated |

Hub: [../HUB_STATUS.md](../HUB_STATUS.md) · Registry: [../../CLAIMS.md](../../CLAIMS.md)

**Support policy (inlined):** Supported during **Release Validation only**. CV
sync must not require `-shell-escape` or Pygments. Missing TeX/Pygments for PDF
→ record N/A in hub status; never fail `make ci` / GitHub Actions T0 for that.

## Purpose

Prove `minted` **bodies are opaque** / not sent as free prose to the LLM path
(CL-101). This asset does **not** validate Python, Pygments, or shell-escape
themselves.

## Prerequisites (Release Validation / PDF)

LILT does **not** install these automatically:

1. TeX Live package `minted`
2. Python 3 on `PATH`
3. Pygments (`pygmentize` or equivalent)
4. Operator willingness to run `pdflatex -shell-escape` (operator-owned risk)

Missing any item → record **N/A / waiver** in hub status. **Never** fail
Continuous Verification or `make ci` / GitHub Actions T0 for that reason.

## Covered Validation Claims

| Claim | How observed |
|-------|----------------|
| CL-101 | CV: sync with opaque `minted`; TM must not contain raw minted body tokens as prose. RV: optional translate when env + LLM available |

## Continuous Verification (no shell-escape)

```bash
uv run lilt -C validation/packages/pkg-minted project init
uv run lilt -C validation/packages/pkg-minted project configure .
# Ensure .lilt/lilt.yaml has parser.opaque_environments including minted
uv run lilt -C validation/packages/pkg-minted project configure . --dry-run
uv run lilt -C validation/packages/pkg-minted pipeline sync main.tex
# Inspect .lilt/tm/main.jsonl — no "def add" / "return a" as free source_text
mkdir -p validation/packages/pkg-minted/i18n/build
uv run lilt -C validation/packages/pkg-minted \
  pipeline build main main.tex i18n/build/main.tex
# Expect fail-closed without translations
```

Do **not** require `pdflatex -shell-escape` for CV pass.

## Release Validation (env-gated)

When prerequisites are present:

```bash
uv run lilt -C validation/packages/pkg-minted pipeline translate --all   # if local LLM
# review queue: N/A for CL-101 per policy
uv run lilt -C validation/packages/pkg-minted \
  pipeline build main main.tex i18n/build/main.tex
pdflatex -shell-escape -interaction=nonstopmode \
  -output-directory=validation/packages/pkg-minted \
  validation/packages/pkg-minted/main.tex
```

If prerequisites or LLM unavailable → **N/A** in [../HUB_STATUS.md](../HUB_STATUS.md).

## Non-goals

listings (see `pkg-listings`), TikZ, CI shell-escape, auto-install of Pygments.

## Success / failure

- Success (CV): sync exit 0; minted body opaque / not free TM prose; no shell-escape needed.
- Failure (CV): minted body leaks into TM as ordinary segments when opaque config is set.
- Waiver: env missing for RV/PDF — documented N/A, CI remains green.

## Related

[../HUB_STATUS.md](../HUB_STATUS.md) · [../../CLAIMS.md](../../CLAIMS.md) ·
gold standard `validation/smoke/article-l1-smoke/`
