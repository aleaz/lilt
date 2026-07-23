# Document Types Hub — Status (VE-01)

**Hub:** `validation/document-types/`  
**SSOT** for hub progress (not per-asset IMPLEMENTATION_* reports).

## Optimization summary

Catalog document-types assets retained (no merges). Smoke stays under
`validation/smoke/`. CL-122 remains in `workflow/sync-partial-fail` (out of hub).

Unnecessary drops: none — each remaining asset closes distinct class / tree /
engine claims.

## Implemented assets

| asset_id | Primary claims | Status |
|----------|----------------|--------|
| `article-scholarly-l2` | CL-033,034,041,050–053,061,062,070–072,080–082,161,192,210 | accepted (V3-02) — product surface thinned (README + fixture only) |
| `beamer-frames` | CL-110,111,112 | accepted — CV verified; RV translate not executed this run |
| `multifile-input` | CL-120,123 | accepted — CV verified (3 namespaces: `main`, `chapters__intro`, `chapters__methods`) |
| `multifile-subfiles` | CL-121 | accepted — CV verified (`main` + `child` via `\subfile`) |
| `polyglossia-xe` | CL-191,201 | accepted — CV sync + `xelatex` PDF OK |
| `publisher-class` | CL-200 | accepted — IEEEtran + `pdflatex` PDF OK |

## Hub claim coverage (document-types primaries)

| Claim | Asset | Evidence ([CLAIMS.md](../CLAIMS.md)) | CV/RV note |
|-------|-------|--------------------------------------|------------|
| CL-033…210 (scholarly set) | `article-scholarly-l2` | implemented | prior V3-02 |
| CL-110, CL-111 | `beamer-frames` | implemented | CV: sync; frames/overlays intact; fail-closed build |
| CL-112 | `beamer-frames` | implemented | RV: asset documents path; **operator run N/A this certification** |
| CL-120, CL-123 | `multifile-input` | implemented | CV: multi-namespace path encoding |
| CL-121 | `multifile-subfiles` | implemented | CV: master sync discovers child |
| CL-191, CL-201 | `polyglossia-xe` | implemented | CV + Xe PDF |
| CL-200 | `publisher-class` | implemented | CV + IEEEtran PDF |

Out of hub: CL-122 → `workflow/`.

## Product note (same changeset)

`DependencyResolver` now follows `\subfile` / `\subfix` so the subfiles master
workflow discovers children (see `docs/architecture/03-parser-masking.md`).

## Known limitations

- RV translate for beamer (CL-112) was not executed in this hub certification run
  (no model/config mutation for the local LLM). Asset README remains the operator path.
- Soft cap: hub size is healthy (6 assets including scholarly).

## Next priorities

None for document-types catalog completeness (1.x design). All 1.x Validation
Claim hubs are COMPLETE as of VE-05; empty-by-design categories remain
`regression/` and `stress/`.

## Hub certification

**Verdict: COMPLETE**

All catalog document-types assets for 1.x design are present, CV-verified where
applicable, and registered in [validation/CLAIMS.md](../CLAIMS.md). Soft cap remains healthy.
