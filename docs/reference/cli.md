# CLI reference

| | |
|---|---|
| **Purpose** | Authoritative catalog of user-facing CLI commands and flags |
| **Scope** | What the Typer surface does — not tutorials, not L1 rationale |
| **Audience** | Operators, contributors, AI agents syncing docs to code |
| **SSOT** | Implementation in `src/lilt/cli/`; this file must match Typer |

Service-layer invariants: [07-cli-application](../architecture/07-cli-application.md).  
Config keys: [Configuration reference](config.md).  
First-time walkthrough: [Getting started](../getting-started.md) · [First translation](../guides/first-translation.md).

## Global options

Apply to all commands:

| Flag | Description |
|------|-------------|
| `-C, --work-dir PATH` | Project directory (default: `.`) |
| `-d, --debug` | Enable debug logging to stdout and `.lilt/lilt.log` |
| `--version` | Print installed package version (`latex-lilt`) and exit |

---

### `lilt project`

#### `project init`

Initialize LILT in the current directory. Creates `.lilt/lilt.yaml`, `.lilt/.env`, and `.lilt/.gitignore`.

```bash
lilt project init
```

#### `project configure`

Scan LaTeX files and register discovered macros/environment aliases in `lilt.yaml`.

```bash
lilt project configure [PATH] [--macros/--no-macros] [--include-aliases] [--dry-run] [--known] [--gaps]
```

| Option | Default | Description |
|--------|---------|-------------|
| `PATH` | `.` | File or directory to scan |
| `--macros/--no-macros` | `--macros` | Register unknown macros |
| `--include-aliases` | off | Register inferred environment aliases |
| `--dry-run` | off | Analyze and report without modifying `lilt.yaml` |
| `--known` | off | With `--dry-run`: also show macros already known to pylatexenc |
| `--gaps` | off | With `--dry-run`: show syntax gaps detected in the source |

---

### `lilt pipeline`

#### `pipeline sync`

Parse a LaTeX file and sync segments to the TM. Auto-discovers `\input{}` dependencies.

```bash
lilt pipeline sync INPUT_FILE
```

#### `pipeline translate`

Run the LLM translation pipeline on one or all namespaces.

```bash
lilt pipeline translate [NAMESPACE] [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--all, -a` | Translate all namespaces |
| `--status, -s STATUS` | Filter by segment status |
| `--force, -f` | Workflow: expands **draft** eligibility only (archives prior translation). Does **not** make critique/refine pick non-`drafted`/`critiqued` segments. Sequential: re-runs full D→C→R on non-immutable segments |
| `--id SEGMENT_ID` | Translate a single segment prefix |
| `--stage STAGE` | Workflow only: `draft`, `critique`, or `refine`. Critique requires `drafted`; refine requires `critiqued`. Use `--stage draft [--force]` then resume stages — do not expect `--force --stage refine` alone to re-draft |
| `--mode MODE` | Override `translation_mode`: `workflow` or `sequential` |

Interrupted runs: **re-invoke** `translate` (no separate resume command). Finished segments stay in the TM. If conflicts/errors remain after an idle run, the CLI exits non-zero and points at `tm list --status conflict` / `build --allow-partial`.

Examples:

```bash
lilt pipeline translate main
lilt pipeline translate --all
lilt pipeline translate main --stage draft
lilt pipeline translate main --status generated --force
lilt pipeline translate main --mode sequential
```

#### `pipeline build`

Reconstruct a translated `.tex` file from the TM.

```bash
lilt pipeline build NAMESPACE INPUT_FILE OUTPUT_FILE [--allow-partial]
```

| Option | Description |
|--------|-------------|
| `--allow-partial` | Emit source text for segments that lack a buildable translation instead of failing |

**Default (fail-closed):** build raises if any translatable segment is missing from the TM, has no translation, or is in a non-buildable status (`generated`, `drafted`, `critiqued`, `conflict`, `error`). Buildable statuses are `refined`, `reviewed`, `approved`, and `locked`.

With `--allow-partial`, those segments fall back to source `raw_text` and the CLI warns with the skipped segment IDs.

#### `pipeline review`

Interactive review queue for segments matching `review.queue_statuses`.

```bash
lilt pipeline review NAMESPACE
```

Prompts: `[a]pprove`, `[e]dit`, `[r]eject`, `[s]kip`, `[q]uit`.

#### `pipeline edit`

Open a segment translation in `$EDITOR`. Saves and approves on success.

```bash
lilt pipeline edit NAMESPACE SEGMENT_ID
```

---

### `lilt tm`

#### `tm list`

List namespaces (no args), list segments in a namespace, search text, or inspect one segment.

```bash
lilt tm list [NAMESPACE] [--status STATUS] [--search QUERY] [--all] [--id SEGMENT_ID]
```

| Option | Description |
|--------|-------------|
| (no args) | List namespaces with summary stats |
| `NAMESPACE` | List segments in that namespace |
| `--all, -a` | List segments across all namespaces |
| `--status` | Filter by segment status |
| `--search` | Filter by substring in source or translation |
| `--id` | Inspect a specific segment (requires `NAMESPACE`) |

#### `tm status`

Translation progress and token/cost metrics per namespace.

```bash
lilt tm status [NAMESPACE] [--all]
```

| Option | Description |
|--------|-------------|
| `NAMESPACE` | Single-namespace dashboard |
| `--all, -a` | Consolidated stats for all namespaces |

#### `tm budget`

Recommend `model_context_limit` from post-sync TM size and StagePolicy context windows (draft / critique / refine).

```bash
lilt tm budget NAMESPACE
```

Prints per-stage `min_bare`, `min_full_neighbors`, `max_useful`, configured vs recommended limits, and a capacity verdict. See [05-llm-layer](../architecture/05-llm-layer.md) and [Configuration reference](config.md) (`model_context_limit`, `stage_policies`).

#### `tm set-status`

Explicitly change a segment lifecycle status.

```bash
lilt tm set-status NAMESPACE SEGMENT_ID STATUS [--force]
```

| Option | Description |
|--------|-------------|
| `--force` | Allow reset to `GENERATED` (clears translation and LLM artifacts) and modifications to `locked` segments |

#### `tm export`

Export active segments to CSV or JSON.

```bash
lilt tm export NAMESPACE OUTPUT_FILE [--format csv|json]
```

| Option | Description |
|--------|-------------|
| `--format` | `csv` or `json` (inferred from extension when omitted) |

#### `tm import`

Import translations from CSV or JSON. Updates segments to `reviewed` on translation change.

```bash
lilt tm import NAMESPACE INPUT_FILE [--format csv|json]
```

| Option | Description |
|--------|-------------|
| `--format` | `csv` or `json` (inferred from extension when omitted) |

#### `tm admin prune`

Permanently remove `deprecated` segments from a namespace.

```bash
lilt tm admin prune NAMESPACE
```

#### `tm admin repair`

Skip corrupt JSONL lines, backup the original file, and compact the namespace.

```bash
lilt tm admin repair NAMESPACE [--dry-run]
```

| Option | Description |
|--------|-------------|
| `--dry-run` | Report corrupt lines without rewriting the namespace file |

#### `tm admin reset`

Reset machine-translated segments to `generated`. With `--force`, also resets `reviewed` and `approved`.

```bash
lilt tm admin reset NAMESPACE [--force]
```

| Option | Description |
|--------|-------------|
| `--force` | Also reset `reviewed` and `approved` (human statuses) |

---

### `lilt telemetry`

#### `telemetry show`

Display LLM inference records (tokens, latency, model, stage).

```bash
lilt telemetry show [--namespace NS]
```

| Option | Description |
|--------|-------------|
| `--namespace` | Filter records to one TM namespace |

---

## See also

| Document | Role |
|----------|------|
| [Configuration reference](config.md) | `lilt.yaml` / env keys |
| [07-cli-application](../architecture/07-cli-application.md) | Services and CLI invariants |
| [Getting started](../getting-started.md) | Tutorial (how to learn) |
| [Glossary](../architecture/00-glossary.md) | Canonical terms |
