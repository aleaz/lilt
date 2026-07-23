# pkg-parser-edge

| Field | Value |
|-------|-------|
| `asset_id` | `pkg-parser-edge` |
| Path | `validation/packages/pkg-parser-edge/` |
| Status | `accepted` |
| Owner | Maintainer of `latex-lilt` |
| Family / level | B-PARSE · L2–L3 |
| Packages | stock `article` only |
| Engine | `pdflatex` |
| Sync root | `main.tex` |
| Mode | CV (primary) |

Hub status: [../HUB_STATUS.md](../HUB_STATUS.md).

## Purpose

Exercise parser / configure / sync for **unknown macros** and **`custom_macros`**
registration — not visual rendering. Compact fixture for CL-021 and CL-022.

## Covered Validation Claims

| Claim | How observed |
|-------|----------------|
| CL-021 | `project configure . --dry-run` lists `\edgemacro` under Unknown Macros (not silent corruption). `--gaps` channel: no syntax gaps in this fixture (N/A) — unknown-macro channel is the evidence |
| CL-022 | After `project configure .`, `.lilt/lilt.yaml` contains `parser.custom_macros` entry for `edgemacro` (`args: 1`, `translatable: false`); sync masks the call as `<macro …/>` per config |

## Non-goals

minted, shell-escape, TikZ/PGFPlots, listings, Xe/Lua, publisher classes, inventing extra claims for every nested construct.

## Expected execution

```bash
uv run lilt -C validation/packages/pkg-parser-edge project init
uv run lilt -C validation/packages/pkg-parser-edge project configure . --dry-run
# Expect: Unknown Macros includes \edgemacro
uv run lilt -C validation/packages/pkg-parser-edge project configure . --dry-run --gaps
# Expect: No syntax gaps (optional check)
uv run lilt -C validation/packages/pkg-parser-edge project configure .
# Expect: Registered custom_macros including edgemacro
uv run lilt -C validation/packages/pkg-parser-edge pipeline sync main.tex
mkdir -p validation/packages/pkg-parser-edge/i18n/build
uv run lilt -C validation/packages/pkg-parser-edge \
  pipeline build main main.tex i18n/build/main.tex
# CV: fail-closed
pdflatex -interaction=nonstopmode -output-directory=validation/packages/pkg-parser-edge \
  validation/packages/pkg-parser-edge/main.tex
```

RV translate / review: **N/A** (claims are CV-only).

## Parser observations (VE-02C)

Recorded on TeX Live + current LILT (2026-07-22):

1. **CL-021 channel:** Unknown-macro surfacing via `configure --dry-run`. Syntax
   `--gaps` reported none — intentional (fixture stays compilable). No product
   change recommended.
2. **`\edgemacro`:** Defined with `\newcommand` for PDF legality; still reported
   unknown to `ProjectAnalyzer` until configure (pylatexenc default set does not
   include project macros). Inferred args = 1.
3. **Side registration:** `\maketitle` also appeared as unknown and was registered
   into `custom_macros` (`args: 0`). Harmless for this asset; documents that
   some core macros may be absent from the analyzer’s “known” set. **No redesign**
   in this task — optional future hardening of known-core list (Low priority).
4. **CL-022 sync:** After configure, `\edgemacro{Edge argument}` is masked as
   `<macro id="N"/>` (argument not a free linguistic segment). Comments near the
   call become `<comment id="…"/>`; `$x = 1$` → `<math>`; `\ref` → `<ref>`.
5. **Unexpected corruption:** None observed. Source remains byte-stable aside from
   normal TM creation.

## Success / failure

- Success: dry-run shows `\edgemacro`; configure writes YAML; sync uses macro mask; PDF OK without shell-escape.
- Failure: unknown macro silent; or configure does not register; or sync drops/corrupts the call.

## Related

[../HUB_STATUS.md](../HUB_STATUS.md) · [../../CLAIMS.md](../../CLAIMS.md)
