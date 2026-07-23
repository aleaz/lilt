# Workflow Hub — Status (VE-03B)

**Hub:** `validation/workflow/`  
**SSOT** for hub progress.

## Implemented assets

| asset_id | Primary claims | Status |
|----------|----------------|--------|
| `workspace-cli` | CL-130, CL-131, CL-171 | accepted — CV verified |
| `tm-human-gates` | CL-141, CL-142, CL-143 | accepted — CV verified (seeded translation for CL-142) |
| `sync-partial-fail` | CL-122 | accepted — CV verified (partial sync + collision) |

### Execution notes

| Asset | init/configure/sync | translate / review / refine / build |
|-------|---------------------|--------------------------------------|
| `workspace-cli` | N/A paper sync; CLI probes OK | **N/A** |
| `tm-human-gates` | OK; set-status + seed translation | Translate **N/A** (seed instead); review **N/A** |
| `sync-partial-fail` | Sync fails as expected with Partial sync message; `main`+`ok` TM written | **N/A** |

CV observations:

- **CL-130:** uninitialized `tm status` → Not initialized… `project init`
- **CL-131:** distinct `-C` roots get separate `.lilt/` trees
- **CL-171:** empty TM guidance mentions `pipeline sync`
- **CL-141:** reviewed survives re-sync without source edit
- **CL-142:** minor edit + human translation → `conflict` via identity carryover
- **CL-143:** `tm status` counts align (incl. conflict/deprecated)
- **CL-122:** `Partial sync: already updated namespaces` after mid-tree namespace collision (`parts/x` vs `parts__x.tex`)

## Pending assets

None in the 1.x Workflow catalog.

## Claim coverage

| Scope | Count |
|-------|------:|
| Workflow primaries closed | **7 / 7** |
| Global Evidence implemented (as of VE-05) | **64 / 64** (100%) |

Remaining repository claims: **none** (1.x catalog closed).

## Known limitations

- CL-142 requires a non-empty translation on the prior human-protected segment for carryover (product rule); asset README documents seeding without LLM.
- `sync-partial-fail` uses engineered namespace collision — not a Recovery interrupt.
- Disposable dirs under `workspace-cli/` are gitignored.

## Remaining roadmap

None for the 1.x Validation Claim catalog (Recovery and Human Review COMPLETE as of VE-05).

## Hub certification

**Verdict: COMPLETE**

All three catalog Workflow assets are present; seven primary claims are
`implemented` in [`../CLAIMS.md`](../CLAIMS.md); CV recorded above.
