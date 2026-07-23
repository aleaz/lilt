# Packages Hub — Status (VE-02E)

**Hub:** `validation/packages/`  
**SSOT** for hub progress.

## Implemented assets

| asset_id | Primary claims | Status |
|----------|----------------|--------|
| `pkg-listings` | CL-100, CL-102 | accepted (VE-02B) |
| `pkg-tikz-pgfplots` | CL-031, CL-090, CL-091, CL-092 | accepted (VE-02B) |
| `pkg-parser-edge` | CL-021, CL-022 | accepted (VE-02C) |
| `pkg-minted` | CL-101 | accepted (VE-02E) — CV opacity verified; RV N/A this run |

### Execution notes — `pkg-minted` (VE-02E)

| Step | Result |
|------|--------|
| init / configure / `--dry-run` | OK (no shell-escape) |
| `opaque_environments: [minted]` | Set in asset `.lilt/lilt.yaml` (config-first) |
| sync | OK — `def add` / `return a` **absent** from TM |
| fail-closed build | OK |
| translate / review | **N/A** (no local Pygments / RV not executed this certification) |
| `pdflatex -shell-escape` | **N/A** (`pygmentize` unavailable on this host) |

CV never required shell-escape. Missing RV prereqs → waiver per policy (CI/`make ci` unaffected).

## Pending assets

None for the 1.x packages catalog.

## Claim coverage

| Scope | Count |
|-------|------:|
| Packages primaries closed | **9 / 9** |
| Global Evidence implemented (as of VE-05) | **64 / 64** (100%) |

Registry: [`../CLAIMS.md`](../CLAIMS.md).

## Known limitations

- Minted PDF/RV remain env-gated (shell-escape + Pygments); not part of T0 CI.
- Opaque `minted` is asset config-first; engine default promotion is a separate product decision.

## Remaining roadmap

None for the 1.x Validation Claim catalog (all hubs COMPLETE as of VE-05).

## Hub certification

**Verdict: COMPLETE**

All four catalog packages assets are present; all nine packages primary claims are
`implemented` in the registry. Soft cap healthy. Minted RV may be re-run on a
maintainer machine with Pygments + `-shell-escape` without changing this verdict
structure (policy allows documented N/A for PDF/translate).
