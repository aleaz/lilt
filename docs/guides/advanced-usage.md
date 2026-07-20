# Advanced usage

Customize modes, capacity, and light automation after you can complete [First translation](first-translation.md). Full key list: [Configuration reference](../reference/config.md). Operator topologies: [Configuration guide](configuration.md).

---

## Translation modes and stages

**Goal:** Choose workflow vs sequential translation and run stages deliberately.

**Prerequisites:** Synced TM; LLM configured.

### Modes

In `.lilt/lilt.yaml`:

```yaml
llm:
  translation_mode: workflow   # or sequential
```

Override per invocation:

```bash
lilt pipeline translate main --mode sequential
lilt pipeline translate main --mode workflow
```

| Mode | Practical meaning |
|------|-------------------|
| `workflow` | Stage-aware; can run `--stage draft\|critique\|refine` |
| `sequential` | Full draft→critique→refine pass behavior per CLI rules |

### Stage-by-stage (workflow)

```bash
lilt pipeline translate main --stage draft
lilt pipeline translate main --stage critique
lilt pipeline translate main --stage refine
```

**Expected results:** Statuses advance `drafted` → `critiqued` → `refined` (when reflection is enabled).

**Common mistakes:** Expecting `--force --stage refine` alone to re-draft — in workflow mode `--force` expands **draft** eligibility; critique needs `drafted`, refine needs `critiqued`. See [CLI reference](../reference/cli.md).

**Next steps:** [Human review](human-review.md) after `refined`.

---

## OpenAI-compatible endpoints and per-stage models

**Goal:** Use local and/or cloud OpenAI-compatible HTTP APIs (same factory provider key `openai`).

**Steps:** Start from [Configuration guide](configuration.md) snippets (`llm.stages` for draft/critique/refine models). Keep `provider: openai` unless you have a maintainer-designed adapter.

```bash
lilt pipeline translate main
lilt telemetry show --namespace main   # optional: inspect calls
```

**Expected results:** Each stage hits its configured `base_url` / `model`.

**Common mistakes:** Assuming a separate “Google/Anthropic plugin”; mismatched context limits across hybrid stages — [Troubleshooting](../runbooks/troubleshooting.md#mix-local--remote-stages).

---

## Cost profiles, stage policies, and budget

**Goal:** Tune reflection cost and context capacity.

**Environment:** After sync (budget uses TM size).

```yaml
llm:
  cost_profile: balanced    # balanced | draft_only | strict
  model_context_limit: 32768
  stage_policies:
    draft:    { thinking: off }
    critique: { thinking: off }
    refine:   { thinking: off }
```

```bash
lilt tm budget main
```

**Expected results:** `tm budget` prints recommended limits vs configured; `draft_only` skips critique/refine (reflection forced off).

**Common mistakes:** Leaving a tiny `model_context_limit` with neighbor context — see token-budget section in [Troubleshooting](../runbooks/troubleshooting.md#token-budget--headroom).

**Next steps:** [Performance runbook](../runbooks/performance.md).

---

## Fail-closed build and `--allow-partial`

**Goal:** Understand when build refuses incomplete TM state.

```bash
lilt pipeline build main main.tex i18n/build/main.tex
# escape hatch (emits source for non-buildable segments + warnings):
lilt pipeline build main main.tex i18n/build/main.tex --allow-partial
```

**Expected results:** Default build fails on `generated` / `drafted` / `critiqued` / `conflict` / `error`. Buildable: `refined`, `reviewed`, `approved`, `locked`.

**Common mistakes:** Using `--allow-partial` as the normal happy path (hides unfinished work).

---

## Protected terms and macro discovery

**Goal:** Improve parsing for project-specific macros.

```bash
lilt project configure . --dry-run --gaps
lilt project configure .
```

Edit `parser.protected_terms` / custom macros in yaml when needed — [Configuration guide](configuration.md).

---

## Automation workflows (shell)

**Goal:** Repeat the same CLI pipeline from a script or CI job you own. LILT does **not** ship a product orchestrator — you wrap commands.

**Prerequisites:** Non-interactive LLM credentials available to the environment; avoid interactive `pipeline review` in unattended jobs.

Example sketch:

```bash
#!/usr/bin/env bash
set -euo pipefail
cd /path/to/latex-project

lilt pipeline sync main.tex
lilt pipeline translate --all
mkdir -p i18n/build
lilt pipeline build main main.tex i18n/build/main.tex
# optional: pdflatex from i18n/build — not a lilt command
```

**Expected results:** Exit non-zero on fail-closed build or LLM errors — fix and re-run (resume semantics apply).

**Common mistakes:** Parallel jobs on the same namespace; committing `.lilt/.env` secrets; expecting PDF from `lilt`.

**Next steps:** Export/import for offline human review in CI-adjacent flows — [Human review](human-review.md).

---

## AI-oriented summary

| Task | Commands / config | State |
|------|-------------------|--------|
| Mode override | `translate --mode workflow\|sequential` | Same TM |
| Staged run | `--stage draft\|critique\|refine` | workflow mode |
| Capacity | `tm budget`; `model_context_limit`; `stage_policies` | Post-sync |
| Partial build | `build … --allow-partial` | Warned skips |
| Automate | Shell wrapping sync/translate/build | No interactive review |

## See also

- [Workflows](workflows.md)
- [CLI reference](../reference/cli.md)
- [Configuration reference](../reference/config.md)
