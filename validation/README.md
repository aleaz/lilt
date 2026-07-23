# Validation repository

Curated **Validation Assets** that evidence product claims (`CL-NNN`) for LILT
(LaTeX Intelligent Localization Tool). Assets co-version with the engine in this
repository.

Operational claim registry: [CLAIMS.md](CLAIMS.md)  
Gold standard asset: [smoke/article-l1-smoke/](smoke/article-l1-smoke/)

Maintainer design notes (governance, catalogs, audits) are **local-only** and
not shipped with this tree.

## Purpose

Prove observable LILT behavior on minimal, maintainable LaTeX fixtures—not to
replace unit tests, not to host an empirical corpus, and not to teach first-time
users (that is `examples/quickstart`).

## Scope

| In scope | Out of scope |
|----------|--------------|
| Claim-driven assets under category dirs | Engine unit/release tests (`tests/`) |
| CV (no external LLM) and documented RV | Cloud LLM in GitHub Actions |
| Small curated set (tens, not hundreds) | Large licensed papers / campaign dumps |
| Shared fragments when ≥2 assets need them | Playground / `misc/` / downloads |

## Directory layout

```text
validation/
  README.md                 # this file
  CLAIMS.md                 # operational claim → asset registry
  smoke/                    # L1 / T1–T2; CV-friendly
  document-types/           # document families; hub SSOT: document-types/HUB_STATUS.md
  document-types/HUB_STATUS.md  # VE-01 hub certification / claim matrix
  packages/                 # package-batch fixtures; hub SSOT: packages/HUB_STATUS.md
  packages/HUB_STATUS.md    # VE-02E packages hub certification (COMPLETE)
  workflow/                 # CLI / TM / sync harnesses; hub SSOT: workflow/HUB_STATUS.md
  workflow/HUB_STATUS.md    # VE-03B workflow hub certification
  recovery/                 # session / lease product claims; hub SSOT: recovery/HUB_STATUS.md
  recovery/HUB_STATUS.md    # VE-04A recovery hub certification
  human-review/             # review queue / import; hub SSOT: human-review/HUB_STATUS.md
  human-review/HUB_STATUS.md  # VE-05 human-review hub certification
  regression/               # locked repros (finding-linked only)
  stress/                   # L4/L5; opt-in for higher tiers
  shared/                   # reusable fragments (empty until needed)
  metadata/                 # coverage index notes (no generated dumps in git)
```

Empty categories keep a `.gitkeep` until the first real asset lands.
**Do not** add placeholder assets.

## Execution model

| Mode | Code | Translate | Typical use |
|------|------|-----------|-------------|
| Continuous Verification | CV | No external LLM | Local / optional CI smoke |
| Release Validation | RV | Local LLM or deterministic stub | Pre-tag product claims |

**Binary rule:** from the repo root, prefer `uv run lilt` (or an activated
`.venv`). Do not assume a stale global `lilt` on `PATH`.

Per-asset steps live in each asset `README.md`. Example (gold standard):

```bash
uv run lilt -C validation/smoke/article-l1-smoke project init
uv run lilt -C validation/smoke/article-l1-smoke project configure .
uv run lilt -C validation/smoke/article-l1-smoke pipeline sync main.tex
```

## Boundaries

| Area | Relationship |
|------|----------------|
| `examples/quickstart` | FTU onboarding only—not a Validation Asset; do not treat as claim evidence |
| `tests/` | Engine correctness; may lock regressions with pytest; claim IDs live here in assets |
| Future empirical corpus | Diversity and scale **outside** this tree (see CONTRIBUTING / corpus strategy) |

## Philosophy

1. **No asset without a claim** — every asset lists primary `CL-NNN` IDs.
2. **Intentionally small** — maximize claim coverage per asset; reject duplicates.
3. **Gold standard first** — copy [smoke/article-l1-smoke/](smoke/article-l1-smoke/) conventions (layout + README shape).
4. **Integrity over fluency** — structural / placeholder contracts matter more than prose quality.
5. **Generated state stays local** — never commit `.lilt/`, PDFs, or LLM logs from asset runs.
