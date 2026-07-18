# CLI reference

Canonical user-facing CLI surface. Service-layer invariants: [07-cli-application](../architecture/07-cli-application.md).

Global options (all commands):

| Flag | Description |
|------|-------------|
| `-C, --work-dir PATH` | Project directory (default: `.`) |
| `-d, --debug` | Enable debug logging to stdout and `.lilt/lilt.log` |

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
| `--force, -f` | Re-translate eligible segments (archives prior translation) |
| `--id SEGMENT_ID` | Translate a single segment prefix |
| `--stage STAGE` | Workflow only: `draft`, `critique`, or `refine` |
| `--mode MODE` | Override `translation_mode`: `workflow` or `sequential` |

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
lilt pipeline build NAMESPACE INPUT_FILE OUTPUT_FILE
```

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

#### `tm set-status`

Explicitly change a segment lifecycle status.

```bash
lilt tm set-status NAMESPACE SEGMENT_ID STATUS [--force]
```

`--force` allows reset to `GENERATED` (clears translation and LLM artifacts) and modifications to `locked` segments.

#### `tm export`

Export active segments to CSV or JSON.

```bash
lilt tm export NAMESPACE OUTPUT_FILE [--format csv|json]
```

#### `tm import`

Import translations from CSV or JSON. Updates segments to `reviewed` on translation change.

```bash
lilt tm import NAMESPACE INPUT_FILE [--format csv|json]
```

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

#### `tm admin reset`

Reset machine-translated segments to `generated`. With `--force`, also resets `reviewed` and `approved`.

```bash
lilt tm admin reset NAMESPACE [--force]
```

---

### `lilt telemetry`

#### `telemetry show`

Display LLM inference records (tokens, latency, model, stage).

```bash
lilt telemetry show [--namespace NS]
```

---
