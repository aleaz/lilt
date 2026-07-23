# workspace-cli

| Field | Value |
|-------|-------|
| `asset_id` | `workspace-cli` |
| Path | `validation/workflow/workspace-cli/` |
| Status | `accepted` |
| Owner | Maintainer of `latex-lilt` |
| Family / level | W-CLI · L1 |
| Engine | n/a (CLI harness) |
| Mode | CV |

Hub: [../HUB_STATUS.md](../HUB_STATUS.md)

## Purpose

Prove workspace bootstrap contracts: init required (CL-130), `-C` / `--work-dir`
selects project root (CL-131), empty TM gives sync guidance (CL-171).

## Covered Validation Claims

| Claim | How observed |
|-------|----------------|
| CL-130 | Command against uninitialized dir shows clear “Not initialized… Run `lilt project init`” |
| CL-131 | `lilt -C proj-a …` vs `lilt -C proj-b …` operate on distinct roots |
| CL-171 | After init with no sync: `tm status` prints actionable `pipeline sync` guidance |

## Expected execution (CV)

From repository root (creates disposable dirs under this asset; gitignored):

```bash
ASSET=validation/workflow/workspace-cli
rm -rf "$ASSET/scratch-uninit" "$ASSET/proj-a" "$ASSET/proj-b"
mkdir -p "$ASSET/scratch-uninit" "$ASSET/proj-a" "$ASSET/proj-b"

# CL-130
uv run lilt -C "$ASSET/scratch-uninit" tm status
# Expect: Not initialized … Run 'lilt project init'

# CL-131
uv run lilt -C "$ASSET/proj-a" project init
uv run lilt -C "$ASSET/proj-b" project init
uv run lilt -C "$ASSET/proj-a" tm status   # guidance for proj-a
test -f "$ASSET/proj-a/.lilt/lilt.yaml"
test -f "$ASSET/proj-b/.lilt/lilt.yaml"

# CL-171 (empty TM after init)
uv run lilt -C "$ASSET/proj-a" tm status
# Expect: no TM namespaces yet … Run `lilt pipeline sync`
```

Translate / review / build / PDF: **N/A** (CLI contracts only).

## Non-goals

Smoke happy-path translate/build; Recovery leases; Human Review queue.

## Related

[../HUB_STATUS.md](../HUB_STATUS.md) · [../../CLAIMS.md](../../CLAIMS.md)
