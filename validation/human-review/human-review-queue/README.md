# human-review-queue

| Field | Value |
|-------|-------|
| `asset_id` | `human-review-queue` |
| Path | `validation/human-review/human-review-queue/` |
| Status | `accepted` |
| Owner | Maintainer of `latex-lilt` |
| Family / level | HR-QUEUE · L2 |
| Engine | `pdflatex` (optional) |
| Sync root | `main.tex` |
| Mode | CV (primary); translate optional |

Hub: [../HUB_STATUS.md](../HUB_STATUS.md)

## Purpose

Prove the human review stage contracts: the interactive review queue respects
configured `review.queue_statuses` (CL-180), and `tm import` rejects translations
that break placeholder structure (CL-181).

## Covered Validation Claims

| Claim | How observed |
|-------|----------------|
| CL-180 | After seeding a `refined` translation, narrow `review.queue_statuses` → `get_segments_to_review` includes that segment; set queue to `approved` only → refined segment **absent** |
| CL-181 | Bad CSV drops placeholders → import updates **0**; TM unchanged. Optional valid import → `reviewed` |

## Non-goals

TM human-status protection / conflict (Workflow `tm-human-gates`); session leases;
parser/packages; scholarly stacks; inventing claims beyond CL-180/181.

## Expected execution (CV)

From repository root:

```bash
ASSET=validation/human-review/human-review-queue
uv run lilt -C "$ASSET" project init
uv run lilt -C "$ASSET" project configure .
uv run lilt -C "$ASSET" pipeline sync main.tex
```

### Seed (no LLM required)

After sync, seed:

- Plain prose segment (`review-queue membership…`) → `refined` + non-empty translation
- Placeholder segment (`Section~<ref id="1"/>…`) → `refined` + translation that **keeps** the `<ref …/>` token
- Leave other segments `generated`

Edit `.lilt/tm/main.jsonl` or use a valid one-row `tm import`.  
`pipeline translate`: **N/A** when seeding (optional if a local LLM is configured).

### CL-180 — queue respects config

```bash
ASSET=validation/human-review/human-review-queue
uv run python <<'PY'
import re
from pathlib import Path

from lilt.services.pipeline_service import PipelineService
from lilt.services.workspace_context import WorkspaceContext

asset = Path("validation/human-review/human-review-queue").resolve()
cfg_path = asset / ".lilt" / "lilt.yaml"


def set_queue(statuses: list[str]) -> None:
    body = "review:\n  queue_statuses:\n" + "".join(f"  - {s}\n" for s in statuses)
    text = cfg_path.read_text(encoding="utf-8")
    if re.search(r"^review:\n", text, re.M):
        text = re.sub(r"^review:\n(?:  .*\n)*", body, text, count=1, flags=re.M)
    else:
        text = text.rstrip() + "\n\n" + body
    cfg_path.write_text(text, encoding="utf-8")


set_queue(["refined"])
svc = PipelineService(str(asset), workspace_ctx=WorkspaceContext.from_workspace(str(asset)))
q = svc.get_segments_to_review("main")
assert q and all(s.status.value == "refined" for s in q)
print(f"CL-180 narrow OK: {len(q)} in queue")

set_queue(["approved"])
svc = PipelineService(str(asset), workspace_ctx=WorkspaceContext.from_workspace(str(asset)))
assert not svc.get_segments_to_review("main")
print("CL-180 exclude OK: refined not queued under approved-only")

set_queue(["refined", "reviewed"])
PY
```

Interactive `pipeline review` approve/reject is optional (prompts); claim pass uses
the service probe above.

### CL-181 — import validates placeholders

```bash
ASSET=validation/human-review/human-review-queue
uv run python <<'PY'
import csv
from pathlib import Path

from lilt.models.segment import FileFormat, SegmentStatus
from lilt.tm.repository import TMRepository

asset = Path("validation/human-review/human-review-queue").resolve()
repo = TMRepository(str(asset / ".lilt" / "tm"))
segs = repo.load_namespace("main")
ph = next(
    s
    for s in segs.values()
    if s.translation
    and "<" in (s.source_text or "")
    and s.status in (SegmentStatus.REFINED, SegmentStatus.REVIEWED)
)
before_t, before_s = ph.translation, ph.status
bad = asset / "bad.csv"
with bad.open("w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["ID", "Status", "Source", "Translation"])
    w.writerow([ph.id, "reviewed", ph.source_text, "Broken translation without tags"])
updated, skipped = repo.import_data("main", str(bad), FileFormat.CSV)
assert updated == 0 and skipped >= 1
loaded = repo.load_namespace("main")[ph.id]
assert loaded.translation == before_t and loaded.status == before_s
print("CL-181 OK: bad import skipped; TM unchanged")
PY
```

Equivalent CLI: `tm export` → corrupt Translation → `tm import` (updated 0).  
Optional positive: import with placeholders preserved → status `reviewed`.

### Other steps

| Step | Result |
|------|--------|
| machine refine | **N/A** (not CL-180/181) |
| fail-closed build | OK while other segments remain `generated` |
| Recovery / parser / packages | **N/A** |

## Related

[../HUB_STATUS.md](../HUB_STATUS.md) · [../../CLAIMS.md](../../CLAIMS.md) ·
[`docs/guides/human-review.md`](../../../docs/guides/human-review.md)
