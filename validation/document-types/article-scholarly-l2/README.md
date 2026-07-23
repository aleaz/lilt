# article-scholarly-l2

L2 scholarly-article Validation Asset for LILT. Follows the certified gold-standard
README shape (`validation/smoke/article-l1-smoke/`).

| Field | Value |
|-------|-------|
| `asset_id` | `article-scholarly-l2` |
| Path | `validation/document-types/article-scholarly-l2/` |
| Status | `accepted` |
| Owner | Maintainer of `latex-lilt` |
| Family / level | D-ART · L2 |
| Engine | `pdflatex` (+ `biber`) |
| Sync root | `main.tex` |
| Execution mode | CV and RV |

Hub: [../HUB_STATUS.md](../HUB_STATUS.md)

## Packages (12 essentials)

| Package | Claims / role |
|---------|----------------|
| `amsmath` | CL-061, CL-062 |
| `cleveref` | CL-041 |
| `biblatex` (+ `references.bib`) | CL-050–053 |
| `graphicx` | CL-080, CL-081 |
| `subcaption` | CL-082 |
| `longtable` | CL-072 |
| `booktabs` | table readability (supports CL-070/071) |
| `siunitx` | CL-210 |
| `csquotes` | CL-192 |
| `hyperref` | CL-034; load before `cleveref` |
| `xcolor` | CL-034 |
| `babel` (english) | localization surface with csquotes |

Supporting fixture files: `references.bib`, `figures/schema.png`.  
Config (not a package): `parser.protected_terms: ["LILT"]` for CL-033.

**Not loaded:** natbib, TikZ, listings, minted, beamer, publisher classes, polyglossia.

## Purpose

Prove LILT preserves scholarly constructs on one compact hub: protected terms,
arg-level macros, cleveref, biblatex cites and an untouched `.bib`, display math,
tables/longtable, figures/subcaption, csquotes, siunitx, and `--allow-partial`
build.

## Covered Validation Claims

Primary claims (registry: [validation/CLAIMS.md](../../CLAIMS.md)):

| Claim | How observed |
|-------|----------------|
| CL-033 | After RV: string `LILT` from `\toolname` / `protected_terms` remains untranslated |
| CL-034 | `\href` URL and `\textcolor` color args intact in TM / `i18n/build/main.tex` |
| CL-041 | `\cref`/`\Cref` appear as placeholders in TM and restore (not prose) |
| CL-050 | Cite commands masked/restored; keys `integrity2024`, `workflow2025`, `units2023` intact |
| CL-051 | biblatex cite commands behave as above |
| CL-052 | CV: `shasum references.bib` unchanged across sync (and translate) |
| CL-053 | `\cite[see][§2]{workflow2025}` optional args handled; key intact |
| CL-061 | Display math in TM uses placeholders; restored `$`/`equation`/`align` tokens |
| CL-062 | RV: display math not replaced by natural-language equations |
| CL-070 | Table caption may translate; `tabular` structure remains valid |
| CL-071 | `&` / `\\` still present in tabular body after localize |
| CL-072 | `longtable` environment survives sync/mask/build |
| CL-080 | Figure caption may translate; includegraphics still valid |
| CL-081 | Path `figures/schema.png` unchanged after sync/translate/build |
| CL-082 | Two `subfigure`/`subcaption` structures remain valid |
| CL-161 | Default build fail-closed without translations; `--allow-partial` emits + warns |
| CL-192 | `\enquote{…}` restores without broken mask/quotes |
| CL-210 | `\SI{…}{…}` / `\si{…}` remain syntactically valid after RV |

Secondary (primary on smoke): CL-030, CL-032.

## Non-goals

- Smoke path, TikZ/listings/minted, beamer, multifile, session lease, review queue.
- Natbib dual stack; publisher class; polyglossia/Xe.
- Prose quality judgments; PDF is optional for claim pass (but source must compile).
- Design/implementation process reports (maintainer archive only).

## Expected execution

Work from the **repository root**. Prefer `uv run lilt`.

After `project init`, set in `.lilt/lilt.yaml`:

- `project.source_lang` / `target_lang` as needed
- `parser.protected_terms: ["LILT"]` (matches `\toolname`)

### Continuous Verification (CV) — no external LLM

```bash
uv run lilt -C validation/document-types/article-scholarly-l2 project init
uv run lilt -C validation/document-types/article-scholarly-l2 project configure .
# Edit .lilt/lilt.yaml: langs + parser.protected_terms: ["LILT"]
SHA=$(shasum validation/document-types/article-scholarly-l2/references.bib)
uv run lilt -C validation/document-types/article-scholarly-l2 pipeline sync main.tex
shasum validation/document-types/article-scholarly-l2/references.bib   # must match $SHA
uv run lilt -C validation/document-types/article-scholarly-l2 tm status
mkdir -p validation/document-types/article-scholarly-l2/i18n/build
uv run lilt -C validation/document-types/article-scholarly-l2 \
  pipeline build main main.tex i18n/build/main.tex
# expect exit ≠ 0, Build blocked
uv run lilt -C validation/document-types/article-scholarly-l2 \
  pipeline build main main.tex i18n/build/main.tex --allow-partial
# expect exit 0 (CL-161)
```

### Release Validation (RV) — local LLM or stub

```bash
uv run lilt -C validation/document-types/article-scholarly-l2 pipeline sync main.tex
uv run lilt -C validation/document-types/article-scholarly-l2 pipeline translate --all
uv run lilt -C validation/document-types/article-scholarly-l2 \
  pipeline build main main.tex i18n/build/main.tex
```

Inspect restored math/cites/cleveref/siunitx/paths; ensure lease clean.

### Optional PDF (source)

```bash
cd validation/document-types/article-scholarly-l2
pdflatex main.tex && biber main && pdflatex main.tex && pdflatex main.tex
```

## Expected outputs

| Step | Expect |
|------|--------|
| sync | Exit 0; `.lilt/tm/main.jsonl`; bib checksum unchanged |
| build (no translate) | Exit ≠ 0; `Build blocked` |
| build `--allow-partial` | Exit 0; `i18n/build/main.tex` written |
| RV build | Exit 0; tokens for math/cites/cleveref/siunitx/path intact |
| pdflatex+biber | `main.pdf` builds (≤4 pages target) |

## Success criteria

- CV matches Expected outputs for CL-052, CL-161, and structural sync of scholarly constructs.
- RV satisfies CL-033–034, 041, 050–053, 061–062, 070–072, 080–082, 192, 210 with falsifiable inspections above.
- Asset stays within complexity budget (compact article; 12 packages; no TikZ/smoke absorption).

## Failure indicators

- `references.bib` rewritten; graphics path changed; math/cites → prose.
- Protected term `LILT` translated; siunitx mangled; longtable/subcaption broken.
- Default build succeeds with only `generated` segments; `--allow-partial` fails to emit.

## Maintenance notes

- Keep L2 hub thin — no TikZ/smoke absorption.
- Prefer engine fixes over fixture growth.
- Never commit `.lilt/`, PDFs, or aux (see `.gitignore`).
- Do not reintroduce DESIGN / IMPLEMENTATION_* packs under this asset.

## Future evolution

- Split only if diagnosis suffers; cut prose before adding packages.
- Claim ownership changes require `validation/CLAIMS.md` + this README in the same change.

## Related

- Hub: [../HUB_STATUS.md](../HUB_STATUS.md)
- Registry: [validation/CLAIMS.md](../../CLAIMS.md) · [validation/README.md](../../README.md)
- Gold standard: [`validation/smoke/article-l1-smoke/`](../../smoke/article-l1-smoke/)
