# article-l1-smoke

**Gold standard Validation Asset** for LILT. Every future asset should follow
the same file layout and README shape as this directory.

**Frozen pattern (V2-03):** certified for inheritance as the gold-standard layout.

| Field | Value |
|-------|-------|
| `asset_id` | `article-l1-smoke` |
| Path | `validation/smoke/article-l1-smoke/` |
| Status | `accepted` — **Gold Standard Certified (V2-03)** |
| Owner | Maintainer of `latex-lilt` |
| Family / level | D-ART · L1 |
| Packages / batches | `babel`, `amsmath` (stock; not a B* stress) |
| Engine | `pdflatex` |
| Sync root | `main.tex` |
| Execution mode | CV and RV |

CV pass/fail is fully decided from this README (Purpose → Failure indicators).
RV needs a local LLM/stub as documented below; claim observation steps are in
the claims table and Expected outputs.

## Purpose

Prove the minimal continuous-localization path on a tiny article: sync without
an LLM (CV), optional translate + build (RV), while preserving document class,
sectioning, environment pairing, labels/refs, inline math masking, namespace
creation, fail-closed build, and babel preamble stability.

## Covered Validation Claims

Primary claims (see also [validation/CLAIMS.md](../../CLAIMS.md)):

| Claim | How observed |
|-------|----------------|
| CL-001 | CV: init → configure → sync exit 0; workspace ready for later build |
| CL-002 | RV: after `pipeline translate --all`, `pipeline build` **exits 0** and writes `i18n/build/main.tex` for buildable segments (fail-closed is **not** RV success) |
| CL-010 | After sync (/localize): `\section{…}` commands still present and well-formed in source / restored output |
| CL-011 | `\begin{itemize}` / `\end{itemize}` pairing intact after sync/mask roundtrip |
| CL-012 | `\documentclass` and required preamble packages (`babel`, `amsmath`) survive sync |
| CL-020 | After sync: `main.tex` still contains `\label{sec:structure}`, `\label{sec:math}`, `\label{eq:toy}`; sample rows in `.lilt/tm/main.jsonl` have non-empty `source_text` (not garbled) |
| CL-030 | CV: in `.lilt/tm/main.jsonl`, segments that contain math/refs show placeholder tokens in masked fields. RV: after accept/buildable status, placeholder **multiset** still matches source for those segments |
| CL-032 | RV: `i18n/build/main.tex` restores structure; math/ref/label tokens reappear (see CL-040/060/162) |
| CL-040 | After RV build: `Section~\ref{sec:math}` / `Equation~\eqref{eq:toy}` (or equivalent restored forms) present; not rewritten as prose |
| CL-042 | `\label{sec:structure}`, `\label{sec:math}`, `\label{eq:toy}` keys unchanged after translate/build |
| CL-060 | Inline `$E = mc^{2}$` masked in TM and restored in `i18n/build/main.tex` after RV |
| CL-140 | After sync: `.lilt/tm/main.jsonl` exists (one namespace for `main.tex`) |
| CL-160 | CV: default build **refuses** (exit ≠ 0) when segments are only `generated` |
| CL-162 | RV: build output matches persisted placeholder restore (math/refs intact); do not rely on re-parsing source alone for pass |
| CL-170 | RV: sync → translate `--all` → build sequence completes with exit 0 on build |
| CL-190 | After sync: `\usepackage[english]{babel}` (or equivalent babel line) still in `main.tex` |

**Claim boundary:** the `equation` environment exists only to exercise `\eqref`
(CL-040). This asset does **not** evidence CL-061 (display math).

## Non-goals

- Scholarly stacks (biblatex, cleveref, TikZ, listings, longtable, …) — other assets.
- Display-math claim CL-061 (despite the small `equation` used for `\eqref`).
- Human review queue, session lease reclaim, multifile trees.
- Prose quality / fluency judgments.
- Compiling PDF with `pdflatex` (optional operator check; not required for claim pass).

## Expected execution

Work from the **repository root**. Prefer `uv run lilt` (or an activated `.venv`).

### Continuous Verification (CV) — no external LLM

Commands below assume the work directory is the asset (via `-C`). Namespace for
this asset is `main` (encoded from `main.tex`).

```bash
uv run lilt -C validation/smoke/article-l1-smoke project init
uv run lilt -C validation/smoke/article-l1-smoke project configure .
# Expect: configure completes without error (may report 0 macros for this asset)
# Set source_lang / target_lang in .lilt/lilt.yaml as needed
uv run lilt -C validation/smoke/article-l1-smoke pipeline sync main.tex
uv run lilt -C validation/smoke/article-l1-smoke tm status
# Expect fail-closed (non-zero) when no buildable translations exist:
mkdir -p validation/smoke/article-l1-smoke/i18n/build
uv run lilt -C validation/smoke/article-l1-smoke \
  pipeline build main main.tex i18n/build/main.tex
```

Do **not** run `pipeline translate` for a pure CV pass.

### Release Validation (RV) — local LLM or stub

Configure `.lilt/lilt.yaml` / `.lilt/.env` for a local OpenAI-compatible endpoint
(or an approved deterministic stub). Then:

```bash
uv run lilt -C validation/smoke/article-l1-smoke pipeline sync main.tex
uv run lilt -C validation/smoke/article-l1-smoke pipeline translate --all
mkdir -p validation/smoke/article-l1-smoke/i18n/build
uv run lilt -C validation/smoke/article-l1-smoke \
  pipeline build main main.tex i18n/build/main.tex
```

Ensure no stuck session lease remains after the run (`tm status` / session clean).

## Expected outputs

| Step | Expect |
|------|--------|
| `project init` | Creates `.lilt/` (gitignored) |
| `project configure .` | Exit 0; no fatal error (0 macros is normal here) |
| `pipeline sync main.tex` | Exit 0; `.lilt/tm/main.jsonl` present |
| Spot-check (CL-020/190) | Labels and babel line still in `main.tex`; sample TM `source_text` non-empty |
| `tm status` | Non-empty segment inventory |
| `pipeline build …` (CV, no translate) | Exit ≠ 0; message like `Build blocked` / segments lack a buildable translation (CL-160) |
| `pipeline translate --all` (RV) | Segments reach buildable statuses (e.g. `refined`) |
| TM placeholders (CL-030) | Math/ref segments show placeholders in `.lilt/tm/main.jsonl` |
| `pipeline build …` (RV) | Exit 0; `i18n/build/main.tex` written |
| Restored tokens (CL-032/040/042/060/162) | Built file retains `$E = mc^{2}$`, `\label{eq:toy}`, `\ref`/`\eqref` (not prose substitutions) |

## Success criteria

- All CV steps match Expected outputs for CL-001,010–012,020,140,160,190.
- RV: CL-002 requires **successful** build after translate; plus CL-030,032,040,042,060,162,170 with token checks above.
- Operator can decide CV pass/fail from this README alone; RV needs configured LLM/stub only.

## Failure indicators

- Sync corrupts `\documentclass`, drops `babel`, or breaks `\begin`/`\end`.
- Labels rewritten; refs/math missing or turned into prose after restore.
- Build succeeds with empty/untranslated TM when fail-closed is expected (CV).
- RV build fails or omits `i18n/build/main.tex` when segments are buildable (CL-002).
- No namespace file after successful sync.
- Stuck busy lease after RV translate.

## Maintenance notes

- Keep this asset **L1 and thin** — do not absorb scholarly packages here.
- Prefer fixing the engine over widening the fixture when claims fail.
- Update `validation/CLAIMS.md` if primary ownership of a claim moves.
- Never commit `.lilt/`, PDFs, or aux files (see `.gitignore`).
- This pattern is **frozen** (V2-03); do not casually rewrite the README skeleton.

## Future evolution

- Split only if diagnosis suffers (unlikely for L1 smoke).
- New smoke assets require governance justification (cap 1–3 under `smoke/`).
- Claim additions to this asset need `validation/CLAIMS.md` updates in the same change.
- Do not use this asset to evidence CL-061 or other scholarly claims.

## Related

- Parent: [validation/README.md](../../README.md)
- Claims registry: [validation/CLAIMS.md](../../CLAIMS.md)
