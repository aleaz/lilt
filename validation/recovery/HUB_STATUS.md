# Recovery Hub — Status (VE-04A)

**Hub:** `validation/recovery/`  
**SSOT** for hub progress. Catalog: one asset → CL-150, CL-151, CL-152.

## Implemented assets

| asset_id | Primary claims | Status |
|----------|----------------|--------|
| `session-lease` | CL-150, CL-151, CL-152 | accepted — CV verified (151/152); RV interrupt verified (150) |

### Execution notes — `session-lease`

| Step | Result |
|------|--------|
| init / configure / sync | OK — 6 segments in `main` |
| CL-151 (CV) | Dead-PID same-host lease + Timeout → reclaim log; session acquires; TM intact; no manual `rm` |
| CL-152 (CV) | Live holder → `NamespaceBusyError` with pid/host/since/lock |
| CL-150 (RV) | SIGINT during `pipeline translate` → exit 130 + saved-progress message; re-run resumes (drafted count advances); lease cleared |
| review | **N/A** (Human Review hub) |
| build fail-closed | Optional; not required for lease claims |

## Pending assets

None in the 1.x Recovery catalog.

## Claim coverage

| Scope | Count |
|-------|------:|
| Recovery primaries closed | **3 / 3** |
| Global Evidence implemented (as of VE-05) | **64 / 64** (100%) |

Remaining repository claims: **none** (1.x catalog closed).

Registry: [`../CLAIMS.md`](../CLAIMS.md).

## Known limitations

- CL-150 is LLM-dependent; documented path always, live RV when endpoint available.
- CL-151 busy→reclaim branch is forced with a one-shot `FileLock.acquire` Timeout patch on Unix flock hosts (same contract as engine reclaim tests).
- CL-152 uses controlled in-process concurrency (thread holder), not chaos/stress.

## Remaining roadmap

None for the 1.x Validation Claim catalog (Human Review COMPLETE as of VE-05).

## Hub certification

**Verdict: COMPLETE**

Catalog Recovery asset is present; three primary claims are `implemented` in
[`../CLAIMS.md`](../CLAIMS.md); CV for CL-151/152 and RV for CL-150 recorded above.
