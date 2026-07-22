# Recovery guides

Multi-step recoveries for common operational failures. Not a first-success tutorial — use [Getting started](../getting-started.md) / [First translation](../guides/first-translation.md) for the happy path. Index: [Troubleshooting](troubleshooting.md). Exceptions: [Error reference](error-reference.md).

Each guide: **Goal** · **Expected state after** · **Steps** · **If still failing**.

---

## Interrupted translation

**Goal:** Continue after `Ctrl+C`, crash, or network drop without losing finished segments.

**Expected state after:** Remaining eligible segments translate; completed TM rows unchanged.

**Behavior notes:**

- `Ctrl+C` / SIGTERM during `pipeline translate` sets a cooperative abort flag.
  Cancel takes effect **between segments** (exit 130). The current in-flight LLM
  call may still finish that one segment; the session lease is released on exit.
- Finished segments stay in the TM; the in-flight segment is rolled back via
  segment unit-of-work when interrupt hits mid-mutation.

**Steps:**

1. `lilt tm status --all` (or one namespace).
2. Re-run:
   ```bash
   lilt pipeline translate --all
   # or: lilt pipeline translate NAMESPACE
   ```
3. Workflow stage resume (if you were mid-stages):
   ```bash
   lilt pipeline translate NAMESPACE --stage critique
   lilt pipeline translate NAMESPACE --stage refine
   ```

**If still failing:** Check `error`/`conflict` via `tm list`; see [Troubleshooting decision tree](troubleshooting.md#my-translation-failed). Do not start a second parallel translate on the same namespace.

**Related:** [Workflows — resume](../guides/workflows.md#scenario-resume-an-interrupted-translation).

---

## Stale session lease (after crash / SIGKILL)

**Goal:** Recover when a previous mutating command died hard and left
`.lilt/tm/<ns>.session.lock` / `.session.lease` behind.

**Expected state after:** The next sync/translate/import/edit acquires the
namespace normally; no manual `rm` of lock files.

**Steps:**

1. Confirm no live `lilt` process is still writing that namespace
   (`ps` / Activity Monitor).
2. Re-run the same command (e.g. `lilt pipeline translate NAMESPACE`).
3. Same-host + dead holder PID → LILT **reclaims** the lease automatically and
   logs a warning. Live holder or other-host lease → wait (see
   [NamespaceBusyError](troubleshooting.md#namespacebusyerror)).

**If still failing:** Do **not** habitually delete lock files while a process may
be alive. If you are certain the holder is dead and reclaim did not run (e.g.
corrupt lease metadata), stop all LILT writers, then remove only that
namespace’s `*.session.lock` / `*.session.lease` pair and retry.

**Related:** [02-persistence — concurrency](../architecture/02-persistence.md#concurrency-invariant).

---

## Failed provider request

**Goal:** Restore LLM connectivity / auth so translate can run.

**Expected state after:** `translate` reaches the model without 401/connection errors.

**Steps:**

1. Confirm server/API is up; `curl` or browser to `base_url` if local.
2. Verify `.lilt/lilt.yaml` `llm.base_url` and `llm.model`.
3. For cloud: set key in `.lilt/.env` matching `api_key_env` (often `OPENAI_API_KEY`).
4. Retry with debug:
   ```bash
   lilt --debug pipeline translate NAMESPACE
   ```

**If still failing:** Hybrid stages — set per-stage keys/limits ([Mix local + remote](troubleshooting.md#mix-local--remote-stages)). Empty thinking output → [starvation](troubleshooting.md#empty-content--reasoning-starvation), not “more retries only”.

---

## Invalid or empty configuration

**Goal:** Obtain a loadable `lilt.yaml` with required fields.

**Expected state after:** Commands past config load; translate can attempt HTTP.

**Steps:**

1. If missing workspace: `lilt project init`.
2. Edit `.lilt/lilt.yaml` — set at least:
   - `project.source_lang` / `project.target_lang`
   - `llm.base_url` / `llm.model`
3. Ensure file is not empty (empty file → `ConfigurationError`).
4. Optional: `lilt project configure .`

**If still failing:** Read `ConfigurationError` text; compare [config reference](../reference/config.md).

---

## Corrupted TM JSONL

**Goal:** Load the namespace again after corrupt lines.

**Expected state after:** Namespace loads; backup of corrupt file retained.

**Steps:**

1. Note path/line from `TMCorruptionError`.
2. ```bash
   lilt tm admin repair NAMESPACE
   # optional: lilt tm admin repair NAMESPACE --dry-run
   ```
3. Confirm with `lilt tm list NAMESPACE` / `tm status`.

**If still failing:** Inspect backup `*.corrupt-<timestamp>`; restore from git if TM was versioned. Avoid hand-merging mid-write.

---

## Partial sync

**Goal:** Finish sync after a mid-tree failure.

**Expected state after:** All namespaces for the root file sync cleanly.

**Steps:**

1. Read which namespaces already updated from the error message.
2. Fix the failing `.tex` (or dependency).
3. Re-run `lilt pipeline sync ROOT.tex` (no automatic rollback of already-written namespaces).

**If still failing:** `project configure --dry-run --gaps`; check path collisions (`__` encoding).

---

## Fail-closed or partial build

**Goal:** Produce output when build refuses incomplete TM, or knowingly emit partial `.tex`.

**Expected state after:** Buildable statuses → clean build; or `--allow-partial` with warnings for skips.

**Steps (preferred):**

1. `lilt tm status NAMESPACE`
2. Finish `translate` / `review` until buildable (`refined`, `reviewed`, `approved`, `locked`).
3. ```bash
   lilt pipeline build NAMESPACE INPUT.tex OUTPUT.tex
   ```

**Escape hatch:**

```bash
lilt pipeline build NAMESPACE INPUT.tex OUTPUT.tex --allow-partial
```

**If still failing:** Missing placeholder maps → re-`sync`. See [Build troubleshooting](troubleshooting.md#build-emits-untranslated-source).

---

## Failed validation / placeholder conflict

**Goal:** Clear `conflict` / validation failures so work can continue.

**Expected state after:** Segment editable/buildable; placeholders intact.

**Steps:**

1. ```bash
   lilt tm list NAMESPACE --status conflict
   lilt --debug …   # if reproducing translate
   ```
2. `lilt pipeline edit NAMESPACE SEGMENT_ID` — keep every `<macro id="N"/>` tag.
3. If maps look stale: `lilt pipeline sync ROOT.tex`.
4. Re-run translate for remaining work if needed.

**If still failing:** Export/import carefully ([Human review](../guides/human-review.md)); do not strip tags in CSV.

---

## Unexpected translation result (quality)

**Goal:** Treat bad prose as an editorial problem, not a structural AccuracyGate failure.

**Expected state after:** Human-improved or approved segments.

**Steps:**

1. Confirm placeholders/structure are valid (`conflict` vs merely disliked wording).
2. `lilt pipeline review NAMESPACE` or `pipeline edit`.
3. Or `tm export` → external edit → `tm import`.

**If still failing:** Try another model/endpoint ([Advanced usage](../guides/advanced-usage.md)); structural issues → validation recovery above. Opening a “bug” for taste alone is usually wrong — [SUPPORT](../../SUPPORT.md) / [FAQ](../faq.md#when-is-something-a-bug-vs-my-setup).

---

## AI-oriented index

| Problem | Commands | Expected state |
|---------|----------|----------------|
| Interrupted translate | `tm status`; re-run `translate` | Eligible segments continue |
| Provider fail | check yaml/`.env`; `--debug translate` | HTTP OK |
| Bad config | `project init`; edit yaml | Config loads |
| Corrupt TM | `tm admin repair` | Namespace loads |
| Partial sync | fix tex; re-`sync` | All namespaces OK |
| Build blocked | finish statuses or `--allow-partial` | Output `.tex` |
| Placeholder conflict | `edit`; preserve tags; maybe `sync` | No conflict |
| Bad prose | `review` / export-import | Human statuses |

## See also

- [Troubleshooting](troubleshooting.md)
- [Error reference](error-reference.md)
- [FAQ](../faq.md)
- [Workflows](../guides/workflows.md)
