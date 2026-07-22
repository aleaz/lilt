# Troubleshooting

Symptom → diagnose → fix. Conceptual questions: [FAQ](../faq.md). Exception catalog: [Error reference](error-reference.md). Multi-step recoveries: [Recovery](recovery.md). Onboarding: [Getting started](../getting-started.md). Commands: [CLI reference](../reference/cli.md).

## Onboarding recovery (stuck on first run?)

| Where you are | Symptom | Go to |
|---------------|---------|--------|
| Install | Wrong package / command not found | [Installation](#installation) |
| Init | `Not initialized… lacks a .lilt/lilt.yaml` | [Workspace Not Initialized](#workspace-not-initialized) |
| Config / translate | 401 / connection errors | [Missing API Key](#missing-api-key) |
| Translate | Empty drafts / thinking models | [Empty content / reasoning starvation](#empty-content--reasoning-starvation) |
| Translate | Context / budget errors | [Token budget / headroom](#token-budget--headroom) |
| Build | Fails or still English | [Build Emits Untranslated Source](#build-emits-untranslated-source) · [Recovery](recovery.md#fail-closed-or-partial-build) |
| Parallel runs | `NamespaceBusyError` | [NamespaceBusyError](#namespacebusyerror) |
| TM file damaged | `TMCorruptionError` | [TMCorruptionError on Load](#tmcorruptionerror-on-load) |

Quick debug:

```bash
lilt --debug pipeline translate main
lilt tm list main --status error
lilt tm list main --status conflict
```

---

## Decision trees

### My translation failed

1. Is the workspace initialized? → If `Not initialized…` → [Workspace Not Initialized](#workspace-not-initialized).
2. Is config non-empty with `base_url` / `model` / langs? → Else [Configuration](#configuration) / [Recovery — invalid config](recovery.md#invalid-or-empty-configuration).
3. HTTP 401 / connection refused? → [Missing API Key](#missing-api-key) / [Recovery — provider](recovery.md#failed-provider-request).
4. `BudgetPreflightError` / `ContextLengthExceededError`? → [Token budget](#token-budget--headroom).
5. `OutputTokenStarvationError` / empty content? → [Empty content](#empty-content--reasoning-starvation).
6. `NamespaceBusyError`? → [NamespaceBusyError](#namespacebusyerror).
7. Segments in `error` / `conflict`? → `tm list --status …` then [Placeholder mismatch](#placeholder-mismatch--validation-failure) or [Recovery — validation](recovery.md#failed-validation--placeholder-conflict).
8. Still stuck with a clear domain message? → [Error reference](error-reference.md). Looks like a crash / wrong Behavior after correct setup? → [SUPPORT.md](../../SUPPORT.md).

### Build failed or output still English

1. Did `build` raise / exit non-zero? → Check fail-closed: unfinished statuses — [Build Emits Untranslated Source](#build-emits-untranslated-source).
2. `tm status` — still `generated` / `drafted` / `critiqued` / `conflict` / `error`? → Finish translate/review first.
3. Need a draft file anyway? → `--allow-partial` (escape hatch) — [Recovery](recovery.md#fail-closed-or-partial-build).
4. Built file has source language prose? → Same causes; re-sync if source moved; check placeholder maps.
5. PDF `???`? → Not a LILT build bug — [PDF references](#pdf-shows---for-references).

### Workspace / TM looks broken

1. `Corrupt TM line…` → [TMCorruptionError](#tmcorruptionerror-on-load) · [Recovery](recovery.md#corrupted-tm-jsonl).
2. Partial sync message → [Partial Sync](#partial-sync) · [Recovery](recovery.md#partial-sync).
3. Namespace not found → wrong name; `lilt tm list` — [Error reference](error-reference.md#namespacenotfounderror).
4. Path traversal / sandbox → [Error reference](error-reference.md#workspacepatherror).

---

## Installation

### Wrong package / `lilt` command missing

| | |
|--|--|
| **Symptom** | `pip install lilt` installs unrelated project; or `lilt` not on PATH |
| **Cause** | Dist name is `latex-lilt`; install is from Git |
| **Diagnose** | `lilt --version` / `uv tool list` |
| **Resolution** | Follow [Getting started — install](../getting-started.md#1-install) |
| **Prevention** | Never document `pip install lilt` for this repo |
| **Related** | [FAQ](../faq.md#how-do-i-install-it-pip-install-lilt) |

---

## Configuration

### Missing API Key

| | |
|--|--|
| **Symptom** | LLM connection errors or 401 responses |
| **Cause** | Cloud endpoint needs a key; or `base_url` wrong |
| **Diagnose** | `lilt --debug pipeline translate …`; check `.lilt/.env` and yaml `api_key_env` |
| **Resolution** | Set `OPENAI_API_KEY` in `.lilt/.env` or per-stage `api_key`; verify `base_url` |
| **Prevention** | Configure LLM before first translate |
| **Related** | [Configuration guide](../guides/configuration.md), [Recovery](recovery.md#failed-provider-request) |

### Empty or invalid configuration

| | |
|--|--|
| **Symptom** | `ConfigurationError`; empty `lilt.yaml` rejected |
| **Cause** | No silent defaults for langs/LLM |
| **Diagnose** | Open `.lilt/lilt.yaml`; ensure `project.source_lang` / `target_lang`, `llm.base_url` / `model` |
| **Resolution** | [Recovery — invalid config](recovery.md#invalid-or-empty-configuration) |
| **Prevention** | Complete config right after `project init` |
| **Related** | [config reference](../reference/config.md), [Error reference](error-reference.md#configurationerror) |

---

## CLI usage

### Workspace Not Initialized

| | |
|--|--|
| **Symptom** | `Not initialized. Workspace '...' lacks a .lilt/lilt.yaml config.` |
| **Cause** | No init, or wrong `-C` / cwd |
| **Diagnose** | `ls .lilt/lilt.yaml`; confirm work dir |
| **Resolution** | `lilt project init` from the LaTeX project root |
| **Prevention** | Init once per project |
| **Related** | [Error reference](error-reference.md#projectnotinitializederror) |

### `NamespaceBusyError`

| | |
|--|--|
| **Symptom** | `Namespace '...' is in use by another operation.` (may include `pid=` / `host=` / lock path) |
| **Cause** | Live second writer (e.g. sync ∥ translate) on same namespace; or other-host lease |
| **Diagnose** | Match `pid=` to a running process; if PID is dead on this host, next acquire should auto-reclaim |
| **Resolution** | Wait for the live holder; retry. Stale same-host lease after SIGKILL → just retry ([Recovery — stale lease](recovery.md#stale-session-lease-after-crash--sigkill)) |
| **Prevention** | One mutating op per namespace |
| **Related** | [Error reference](error-reference.md#namespacebusyerror) |

---

## Input files / LaTeX parsing

### Partial Sync

| | |
|--|--|
| **Symptom** | `Partial sync: already updated namespaces: [...]` |
| **Cause** | Multi-file sync failed mid-way |
| **Diagnose** | Read which namespaces already updated; inspect failing `.tex` |
| **Resolution** | Fix source; re-run `lilt pipeline sync` on the root file (no auto-rollback) |
| **Prevention** | Sync from a known-good root; fix parse issues early (`project configure --dry-run --gaps`) |
| **Related** | [Recovery](recovery.md#partial-sync) |

### Namespace path collisions

| | |
|--|--|
| **Symptom** | Sync fails loud on `__` encoding collisions |
| **Cause** | Filenames that collide when `/` → `__` (e.g. `chapters/intro.tex` vs `chapters__intro.tex`) |
| **Diagnose** | Compare paths under project |
| **Resolution** | Rename sources to avoid collision |
| **Prevention** | Avoid ambiguous path encodings |
| **Related** | Checklist below |

---

## Translation workflow

### Resume / unexpected “nothing to do”

| | |
|--|--|
| **Symptom** | Re-run translate seems to skip work |
| **Cause** | Segments already past eligibility; or wrong `--stage` / `--force` expectations |
| **Diagnose** | `lilt tm status`; read CLI notes on `--force` / stages |
| **Resolution** | [Recovery — interrupted](recovery.md#interrupted-translation); [Advanced usage](../guides/advanced-usage.md) |
| **Prevention** | Prefer workflow stage resume over blind `--force` |
| **Related** | [Workflows — resume](../guides/workflows.md#scenario-resume-an-interrupted-translation) |

---

## LLM providers / capacity

### Token budget / headroom

| | |
|--|--|
| **Symptom** | `ContextLengthExceededError` or `BudgetPreflightError` |
| **Cause** | Prompt + reserved output exceeds `model_context_limit` |
| **Diagnose** | `lilt tm budget NAMESPACE`; `--debug` preflight logs |
| **Resolution** | Raise `model_context_limit` to real serving context; adjust `max_tokens` / neighbors / `domain_context` |
| **Prevention** | Run `tm budget` after sync before large jobs |
| **Related** | [performance.md](performance.md), [Error reference](error-reference.md) |

### Empty content / reasoning starvation

| | |
|--|--|
| **Symptom** | `OutputTokenStarvationError` — empty `content` after completion tokens |
| **Cause** | Thinking models spent budget on reasoning |
| **Diagnose** | Telemetry / debug; confirm server thinking toggle |
| **Resolution** | Raise `max_tokens`; `split_budget` + `reasoning_reserve`; `stage_policies.*.thinking: off`; disable server thinking |
| **Prevention** | Default thinking off; smoke-test local models |
| **Related** | [performance.md](performance.md) |

### Mix local + remote stages

| | |
|--|--|
| **Symptom** | One stage works; another fails on context/starvation |
| **Cause** | Per-stage budgets not shared |
| **Diagnose** | Compare `llm.stages.*` limits |
| **Resolution** | Set per-stage `model_context_limit` / `max_tokens` |
| **Prevention** | Preflight every stage that will run |
| **Related** | [Configuration guide](../guides/configuration.md) |

---

## Output validation / build

### Placeholder Mismatch / Validation Failure

| | |
|--|--|
| **Symptom** | Segment `conflict`; placeholder mismatch in logs |
| **Cause** | MT or edit dropped/changed `<macro id="N"/>` tags |
| **Diagnose** | `tm list NS --status conflict`; `--debug` |
| **Resolution** | `lilt pipeline edit` preserving tags; re-sync if maps stale |
| **Prevention** | Do not strip placeholders in external CSV without care |
| **Related** | [Recovery](recovery.md#failed-validation--placeholder-conflict) |

### Build Emits Untranslated Source

| | |
|--|--|
| **Symptom** | Build fails or output still in source language |
| **Cause** | Non-buildable statuses; stale sync; fail-closed default |
| **Diagnose** | `lilt tm status`; list `error`/`conflict` |
| **Resolution** | Finish translate/review; or `--allow-partial` knowingly |
| **Prevention** | Build only when statuses are buildable (`refined` / human gates) |
| **Related** | [Advanced usage — build](../guides/advanced-usage.md#fail-closed-build-and---allow-partial) |

### PDF Shows `???` for References

| | |
|--|--|
| **Symptom** | Unresolved refs/citations in PDF |
| **Cause** | Normal LaTeX multi-pass / path to bib |
| **Diagnose** | Compile from `i18n/build` with TEXINPUTS |
| **Resolution** | Multi-pass `pdflatex` / `bibtex` as below |
| **Prevention** | Document compile recipe for your tree |
| **Related** | Not a TM bug |

```bash
cd i18n/build/
TEXINPUTS=".:../../:" pdflatex main.tex
BSTINPUTS=".:../../:" BIBINPUTS=".:../../:" bibtex main
TEXINPUTS=".:../../:" pdflatex main.tex
TEXINPUTS=".:../../:" pdflatex main.tex
```

---

## Translation memory

### Inspect and filter

```bash
lilt tm list
lilt tm list main --status error
lilt tm status main
```

See [Workflows — TM](../guides/workflows.md#scenario-manage-translation-memory). Destructive admin: repair / prune / reset — [Recovery](recovery.md) and [CLI reference](../reference/cli.md).

---

## Persistence

### `TMCorruptionError` on Load

| | |
|--|--|
| **Symptom** | `Corrupt TM line N in '...'` |
| **Cause** | Damaged JSONL line |
| **Diagnose** | Message includes path + line |
| **Resolution** | `lilt tm admin repair NAMESPACE` (backup `*.corrupt-<timestamp>`) |
| **Prevention** | Avoid manual half-edits of JSONL; one writer |
| **Related** | [Recovery](recovery.md#corrupted-tm-jsonl), [Error reference](error-reference.md#tmcorruptionerror) |

---

## Recovery and performance (pointers)

- Step-by-step recoveries: [recovery.md](recovery.md)
- Cost / context / thinking ops: [performance.md](performance.md)

---

## Before real testing

Checklist for a careful first run on a real project (single writer, explicit config):

1. **Config** — Non-empty `.lilt/lilt.yaml` with langs + `llm.base_url` / `llm.model`. Keep `model_context_limit > max_tokens`. Set `project.domain_context` before serious runs (empty warns but does not block).
2. **One writer per namespace** — No parallel `sync` + `translate`.
3. **Resume mid-pipeline** — `--stage draft` then `critique` then `refine`. Workflow `--force` expands **draft** eligibility only.
4. **Sequential vs workflow** — Sequential `--force` re-runs full D→C→R on non-immutable segments; workflow stage resume is safer for partial progress.
5. **Namespace paths** — Avoid `__` encoding collisions.
6. **Flaky local LLMs** — Raise `draft_empty_retries` if needed; garbage critique JSON → `conflict`. Thinking empty content → fix token budget, not blind retries.
7. **Partial sync** — Fix failing `.tex` and re-sync; no automatic rollback.

---

## See also

- [FAQ](../faq.md)
- [Error reference](error-reference.md)
- [Recovery](recovery.md)
- [First translation](../guides/first-translation.md)
- [Workflows](../guides/workflows.md)
- [Advanced usage](../guides/advanced-usage.md)
- [Performance](performance.md)
- [SUPPORT.md](../../SUPPORT.md)
