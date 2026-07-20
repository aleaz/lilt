# Workflows

Common operator workflows after your first success. Quick path: [Getting started](../getting-started.md). First deep walkthrough: [First translation](first-translation.md).

Flags encyclopedia: [CLI reference](../reference/cli.md) — this guide is **how**, not every option.

---

## Scenario: Translate a complete LaTeX project

**Goal:** Sync a multi-file project from the root `.tex`, translate all namespaces, build the root output.

**Prerequisites:** Workspace initialized; LLM configured.

**Environment:** Project root that contains the entry `.tex` (example: `main.tex`).

**Steps:**

```bash
lilt project init                    # if not already
lilt project configure .
# Ensure .lilt/lilt.yaml has langs + llm.*

lilt pipeline sync main.tex          # crawls \input{} / \include{}
lilt tm list                         # see namespaces
lilt pipeline translate --all
lilt tm status --all

mkdir -p i18n/build
lilt pipeline build main main.tex i18n/build/main.tex
```

**Expected results:** One JSONL per namespace under `.lilt/tm/`; build writes `i18n/build/main.tex` when statuses are buildable.

**Explanation:** Sync from the **root** file discovers dependencies. Translate `--all` covers every namespace created by sync.

**Common mistakes:** Syncing only a chapter file when you meant the whole book; building before refine/review finishes.

**Next steps:** [Human review](human-review.md); build other namespaces the same way (`build NAMESPACE INPUT OUTPUT`).

---

## Scenario: Translate a single document / namespace

**Goal:** Work on one namespace without `--all`.

**Steps:**

```bash
lilt pipeline sync main.tex
lilt pipeline translate main
lilt tm status main
lilt pipeline build main main.tex i18n/build/main.tex
```

For a chapter namespace after a full sync (example name):

```bash
lilt pipeline translate chapters__intro
```

**Expected results:** Only the named namespace advances.

**Common mistakes:** Namespace string must match TM naming (`chapters/intro.tex` → `chapters__intro`). List with `lilt tm list`.

**Next steps:** `--stage draft|critique|refine` in workflow mode — [Advanced usage](advanced-usage.md).

---

## Scenario: Resume an interrupted translation

**Goal:** Continue after `Ctrl+C` or a crash without losing finished segments.

**Prerequisites:** Sync already done; some segments may already be translated.

**Steps:**

```bash
lilt tm status --all
lilt pipeline translate --all
```

**Expected results:** Completed segments stay in TM (JSONL append/checkpoints). Re-run picks up work that is still eligible (by default segments still needing machine work, e.g. `generated` / `error` — see CLI reference for filters).

**Explanation:** You do not need a special “resume” command — re-invoke `translate`.

**Common mistakes:** Using `--force` when you only meant to continue (force expands re-draft eligibility; see CLI). Running a second translate in parallel (`NamespaceBusyError`).

**Next steps:** Stage-by-stage resume (`--stage critique` then `--stage refine`) in [Advanced usage](advanced-usage.md).

---

## Scenario: Point at a different LLM endpoint

**Goal:** Switch local ↔ cloud (still OpenAI-compatible). Not a plugin marketplace — same `provider: openai` adapter, different `base_url` / keys.

**Steps:**

1. Edit `.lilt/lilt.yaml` `llm.base_url` and `llm.model`.
2. For cloud, set key in `.lilt/.env` (`OPENAI_API_KEY` or your `api_key_env`).
3. Optionally use per-stage endpoints under `llm.stages` — [Configuration guide](configuration.md).

```bash
lilt pipeline translate main --mode workflow   # or sequential
```

**Expected results:** New calls hit the new endpoint; failures show as HTTP/auth errors.

**Common mistakes:** Mixing stage budgets across local/cloud without per-stage limits — [Troubleshooting](../runbooks/troubleshooting.md#mix-local--remote-stages).

**Next steps:** [Advanced usage](advanced-usage.md#translation-modes-and-stages).

---

## Scenario: Debug a failed translation

**Goal:** Find failing segments and recover.

**Steps:**

```bash
lilt --debug pipeline translate main
# inspect .lilt/lilt.log

lilt tm list main --status error
lilt tm list main --status conflict
lilt tm status main
```

Fix config or edit the segment, then re-run translate (or `lilt pipeline edit main <id>`).

**Expected results:** Error/conflict segments are listable; logs show HTTP or validation detail.

**Common mistakes:** Ignoring placeholder tags when editing; parallel writers on one namespace.

**Next steps:** [Troubleshooting](../runbooks/troubleshooting.md); placeholder edits in that runbook.

---

## Scenario: Review generated output

**Goal:** Human-approve or fix machine output before treating it as final.

**Steps:**

```bash
lilt tm status main
lilt pipeline review main
# or one segment:
lilt pipeline edit main <segment_id>
```

External spreadsheet review:

```bash
lilt tm export main review.csv
# edit CSV outside
lilt tm import main review.csv
```

**Expected results:** Interactive review updates statuses; import sets `reviewed` when translations change.

**Explanation:** LLM **Critique** ≠ human **Review**. `refined` is machine-finished, not human-approved — [Human review](human-review.md).

**Next steps:** Lock important segments via review workflow / `tm set-status` when appropriate.

---

## Scenario: Manage Translation Memory

**Goal:** Inspect progress, budget, statuses, and hygiene.

**Environment:** After at least one sync.

**Steps:**

```bash
lilt tm list
lilt tm list main --status conflict
lilt tm status main
lilt tm budget main

lilt tm set-status main <segment_id> reviewed
# destructive / repair (use carefully):
# lilt tm admin repair main
# lilt tm admin prune main
# lilt tm admin reset main
```

**Conflicts after source edits on protected segments:**

```bash
lilt pipeline sync main.tex
lilt tm list main --status conflict
lilt pipeline edit main <segment_id>
```

**Expected results:** Dashboards reflect progress; budget prints capacity guidance vs `model_context_limit`.

**Common mistakes:** `admin reset --force` clearing human work unintentionally; editing translations without preserving `<macro id="N"/>` placeholders.

**Next steps:** [Configuration reference](../reference/config.md) for limits; [Advanced usage](advanced-usage.md) for cost profiles.

---

## AI-oriented index

| Scenario | Key commands | Recovery |
|----------|--------------|----------|
| Full project | `sync` root, `translate --all`, `build` | Fix sync errors; re-sync |
| Single namespace | `translate NAMESPACE` | `tm list` for names |
| Resume | Re-run `translate` | Avoid parallel writers |
| New endpoint | Edit yaml / `.env` | Auth troubleshooting |
| Debug | `--debug`, `tm list --status` | edit / re-translate |
| Review | `review`, `export`/`import` | human-review guide |
| TM | `list`, `status`, `budget`, `set-status` | `admin repair` if corrupt |

## See also

- [Advanced usage](advanced-usage.md)
- [Configuration guide](configuration.md)
- [Troubleshooting](../runbooks/troubleshooting.md)
