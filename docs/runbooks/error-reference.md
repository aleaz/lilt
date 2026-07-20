# Error reference

Domain exceptions users may see from the CLI (from `src/lilt/exceptions.py`). Symptom runbook: [Troubleshooting](troubleshooting.md). Procedures: [Recovery](recovery.md).

Template per error: **When** · **Diagnose** · **Resolve** · **Prevent** · **Related**.

---

## ProjectNotInitializedError

**Message pattern:** `Not initialized. Workspace '…' lacks a .lilt/lilt.yaml config.`

| | |
|--|--|
| **When** | Commands run without an initialized workspace |
| **Diagnose** | Check cwd / `-C`; look for `.lilt/lilt.yaml` |
| **Resolve** | `lilt project init` |
| **Prevent** | Init once per project |
| **Related** | [Troubleshooting](troubleshooting.md#workspace-not-initialized) |

## ConfigurationError

**When:** Config load/validation fails (e.g. empty or invalid `lilt.yaml`).

| | |
|--|--|
| **Diagnose** | Read the exception message; open `.lilt/lilt.yaml` |
| **Resolve** | Set required `project.*` langs and `llm.base_url` / `model` |
| **Prevent** | Do not rely on silent defaults |
| **Related** | [Recovery — config](recovery.md#invalid-or-empty-configuration), [config reference](../reference/config.md) |

## NamespaceNotFoundError

**Message pattern:** `Namespace '…' not found in TM.`

| | |
|--|--|
| **When** | Typo or namespace never synced |
| **Diagnose** | `lilt tm list` |
| **Resolve** | Sync root `.tex` or use the listed namespace name (`chapters/intro.tex` → `chapters__intro`) |
| **Prevent** | Copy names from `tm list` |
| **Related** | [Workflows](../guides/workflows.md) |

## SegmentNotFoundError

**Message pattern:** `No segment found matching '…' in namespace '…'.`

| | |
|--|--|
| **When** | Bad id / prefix for `edit`, `set-status`, etc. |
| **Diagnose** | `lilt tm list NS` / `--id` |
| **Resolve** | Use a longer unique prefix or full id |
| **Prevent** | Copy ids from `tm list` |
| **Related** | [CLI reference](../reference/cli.md) |

## MultipleSegmentsFoundError

**Message pattern:** `Multiple segments match prefix '…'. Please be more specific.`

| | |
|--|--|
| **When** | Ambiguous segment id prefix |
| **Diagnose** | List matches via `tm list` |
| **Resolve** | Pass a longer prefix |
| **Prevent** | Prefer full ids in scripts |
| **Related** | — |

## InvalidStatusError

**Message pattern:** `Invalid status '…'. Valid options are: …`

| | |
|--|--|
| **When** | `tm set-status` (or similar) with unknown status |
| **Diagnose** | Read valid options in the message |
| **Resolve** | Use a listed status name |
| **Prevent** | Glossary / L1-02 for status vocabulary |
| **Related** | [Human review](../guides/human-review.md) |

## InvalidTransitionError

**Message pattern:** `Invalid status transition: A -> B`

| | |
|--|--|
| **When** | Status change not allowed by lifecycle |
| **Diagnose** | Current status via `tm list --id` |
| **Resolve** | Choose an allowed transition; see persistence docs for machine |
| **Prevent** | Prefer `pipeline review` / documented flows over ad-hoc jumps |
| **Related** | [02-persistence](../architecture/02-persistence.md) |

## BuildError

**When:** Document build fails (including fail-closed incomplete TM / missing maps).

| | |
|--|--|
| **Diagnose** | Read message; `tm status`; check buildable statuses |
| **Resolve** | Finish translate/review; re-sync if maps missing; or `--allow-partial` knowingly |
| **Prevent** | Build only when segments are buildable |
| **Related** | [Troubleshooting — build](troubleshooting.md#build-emits-untranslated-source), [Recovery](recovery.md#fail-closed-or-partial-build) |

## TMImportError

**When:** `tm import` fails (format/content).

| | |
|--|--|
| **Diagnose** | Message + file format (`csv`/`json`) |
| **Resolve** | Fix file; re-export a template via `tm export` |
| **Prevent** | Keep segment ids; preserve placeholders in translations |
| **Related** | [Human review](../guides/human-review.md) |

## TranslationValidationError

**When:** Structural/placeholder validation rejects a translation (may surface as conflict / blocked persist).

| | |
|--|--|
| **Diagnose** | `--debug`; `tm list --status conflict` |
| **Resolve** | Edit preserving `<macro id="N"/>`; re-sync if needed |
| **Prevent** | Do not strip placeholders |
| **Related** | [Recovery — validation](recovery.md#failed-validation--placeholder-conflict) |

## PreconditionError

**When:** Workflow stage lacks required prior artifacts (e.g. refine without critique artifacts).

| | |
|--|--|
| **Diagnose** | Which `--stage` was requested vs segment status |
| **Resolve** | Run prior stages (`draft` → `critique` → `refine`) |
| **Prevent** | Do not expect `--force --stage refine` alone to invent priors |
| **Related** | [Advanced usage](../guides/advanced-usage.md), CLI translate notes |

## TMConcurrencyError

**When:** TM file lock not acquired after retries.

| | |
|--|--|
| **Diagnose** | Concurrent writers / stale locks |
| **Resolve** | Wait; ensure no parallel writers; retry |
| **Prevent** | One writer per namespace file |
| **Related** | [NamespaceBusyError](#namespacebusyerror) |

## NamespaceBusyError

**Message pattern:** `Namespace '…' is in use by another operation.`

| | |
|--|--|
| **Diagnose** | Another `lilt` mutating the namespace |
| **Resolve** | Wait and retry |
| **Prevent** | No parallel sync/translate on same namespace |
| **Related** | [Troubleshooting](troubleshooting.md#namespacebusyerror) |

## TMCorruptionError

**Message pattern:** `Corrupt TM line N in '…': …`

| | |
|--|--|
| **Diagnose** | Path + line in message |
| **Resolve** | `lilt tm admin repair NAMESPACE` |
| **Prevent** | Avoid hand-editing JSONL mid-write |
| **Related** | [Recovery](recovery.md#corrupted-tm-jsonl) |

## TelemetryCorruptionError

**When:** Telemetry SQLite cannot be read.

| | |
|--|--|
| **Diagnose** | `.lilt/telemetry.db` integrity |
| **Resolve** | Remove/rebuild db if disposable (telemetry is observational); re-run work |
| **Prevent** | Do not share half-written db copies |
| **Related** | [08-observability](../architecture/08-observability.md) |

## OutputTokenStarvationError

**When:** Model used completion tokens but `message.content` empty (thinking models).

| | |
|--|--|
| **Diagnose** | Message includes completion token count / stage |
| **Resolve** | Raise `max_tokens`; `split_budget` + `reasoning_reserve`; turn thinking off |
| **Prevent** | Smoke-test thinking models; default policies thinking off |
| **Related** | [Troubleshooting](troubleshooting.md#empty-content--reasoning-starvation) |

## EmptyLLMOutputError

**Message pattern:** `LLM returned empty output during '…' for translatable content.`

| | |
|--|--|
| **Diagnose** | Stage name in message; endpoint health |
| **Resolve** | Retry after fixing model/server; adjust `draft_empty_retries` if drafts flake |
| **Prevent** | Stable local server; adequate tokens |
| **Related** | [Troubleshooting](troubleshooting.md) |

## BudgetPreflightError

**When:** Token budget preflight proves a batch infeasible before segments run.

| | |
|--|--|
| **Diagnose** | `lilt tm budget NS`; debug preflight |
| **Resolve** | Raise context limit / lower reserved output / shrink context |
| **Prevent** | Budget after sync |
| **Related** | [Token budget](troubleshooting.md#token-budget--headroom) |

## ContextLengthExceededError

**When:** Prompt + reserved output exceeds `model_context_limit` at runtime.

| | |
|--|--|
| **Diagnose** | Message fields (`reserved_output`, etc.) |
| **Resolve** | Same as budget/headroom fixes |
| **Prevent** | Align limit with serving stack |
| **Related** | [Token budget](troubleshooting.md#token-budget--headroom) |

## WorkspacePathError

**Message pattern:** `Security Error: Path '…' attempts to traverse outside the workspace sandbox.`

| | |
|--|--|
| **When** | Path escapes work dir sandbox |
| **Diagnose** | Paths with `..` or absolute escape |
| **Resolve** | Use paths inside `-C` workspace |
| **Prevent** | Keep inputs under the project root |
| **Related** | — |

---

## HTTP / provider errors (not domain types)

401, connection refused, timeouts: treat as environment — [Missing API Key](troubleshooting.md#missing-api-key), [Recovery — provider](recovery.md#failed-provider-request).

## See also

- [Troubleshooting](troubleshooting.md)
- [Recovery](recovery.md)
- [FAQ](../faq.md)
