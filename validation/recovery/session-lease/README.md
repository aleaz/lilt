# session-lease

| Field | Value |
|-------|-------|
| `asset_id` | `session-lease` |
| Path | `validation/recovery/session-lease/` |
| Status | `accepted` |
| Owner | Maintainer of `latex-lilt` |
| Family / level | R-LEASE · L1 |
| Engine | pdflatex (optional) |
| Mode | CV (+ RV for CL-150) |

Hub: [../HUB_STATUS.md](../HUB_STATUS.md)

## Purpose

Evidence namespace session-lease recovery: stale same-host reclaim without
manual lock deletion (CL-151), busy holder identity (CL-152), and cooperative
translate interrupt → resume (CL-150, RV / LLM-gated).

Product APIs: `TMRepository.namespace_session`, `lilt.tm.session_lease`,
`pipeline translate` SIGINT/SIGTERM abort message.

## Covered Validation Claims

| Claim | Mode | How observed |
|-------|------|----------------|
| CL-151 | CV | Dead-PID same-host lease + forced Timeout → reclaim; session acquires; TM intact |
| CL-152 | CV | Live holder → second `namespace_session` raises `NamespaceBusyError` with pid/host/since |
| CL-150 | RV | Ctrl+C / SIGINT during translate → progress saved message; re-run resumes (no `rm` of lock) |

## Bootstrap (once)

From repository root:

```bash
ASSET=validation/recovery/session-lease
uv run lilt -C "$ASSET" project init
uv run lilt -C "$ASSET" project configure .
uv run lilt -C "$ASSET" pipeline sync main.tex
uv run lilt -C "$ASSET" tm status main
# Expect: readable `.lilt/tm/main.jsonl`; fail-closed build OK if attempted
```

## Expected execution (CV) — CL-151 / CL-152

Deterministic probes call `TMRepository` (no LLM). First acquire is patched
once so the Timeout → reclaim branch runs on Unix flock hosts (same idea as
`tests/test_session_reclaim_contracts.py`).

```bash
ASSET=validation/recovery/session-lease
uv run python <<'PY'
from __future__ import annotations

import os
import socket
import threading
from pathlib import Path

from filelock import FileLock, Timeout

from lilt.exceptions import NamespaceBusyError
from lilt.tm.repository import TMRepository
from lilt.tm.session_lease import SessionLease, lease_path_for_session_lock, write_lease

asset = Path("validation/recovery/session-lease").resolve()
tm_dir = asset / ".lilt" / "tm"
assert (tm_dir / "main.jsonl").is_file(), "run bootstrap sync first"
repo = TMRepository(str(tm_dir))

# --- CL-151: stale same-host reclaim ---
lock_path = repo._get_session_lock_path("main")
meta_path = lease_path_for_session_lock(lock_path)
Path(lock_path).write_text("", encoding="utf-8")
write_lease(
    meta_path,
    SessionLease(
        pid=2_147_483_646,
        hostname=socket.gethostname(),
        started_at="2020-01-01T00:00:00+00:00",
        lease_id="stale-cv",
        operation="translate",
    ),
)
_orig = FileLock.acquire
_n = {"i": 0}

def _acquire(self, timeout=None, poll_interval=0.05):
    _n["i"] += 1
    if _n["i"] == 1:
        raise Timeout(str(self.lock_file))
    return _orig(self, timeout=timeout, poll_interval=poll_interval)

FileLock.acquire = _acquire  # type: ignore[method-assign]
try:
    with repo.namespace_session("main", operation="sync"):
        assert Path(meta_path).is_file()
        assert str(os.getpid()) in Path(meta_path).read_text(encoding="utf-8")
finally:
    FileLock.acquire = _orig  # type: ignore[method-assign]
assert not Path(meta_path).exists()
assert (tm_dir / "main.jsonl").is_file()
print("CL-151 OK: stale lease reclaimed; TM intact")

# --- CL-152: busy identity ---
acquired = threading.Event()
release = threading.Event()

def hold() -> None:
    with repo.namespace_session("main", operation="translate"):
        acquired.set()
        release.wait(timeout=10)

t = threading.Thread(target=hold)
t.start()
assert acquired.wait(timeout=5)
try:
    raised = False
    try:
        with repo.namespace_session("main"):
            pass
    except NamespaceBusyError as err:
        raised = True
        assert err.pid == os.getpid()
        assert err.hostname == socket.gethostname()
        assert err.started_at
        assert err.lock_path
        msg = str(err)
        assert "pid=" in msg and "host=" in msg
        print(f"CL-152 OK: {msg}")
    assert raised, "expected NamespaceBusyError"
finally:
    release.set()
    t.join(timeout=5)
PY
```

Do **not** delete `.session.lock` / `.session.lease` by hand in happy recovery paths.

## Expected execution (RV) — CL-150

Requires a configured local (or cloud) OpenAI-compatible LLM.

```bash
ASSET=validation/recovery/session-lease
# Ensure LLM in .lilt/lilt.yaml, then:
uv run lilt -C "$ASSET" pipeline translate main
# While running: send SIGINT (Ctrl+C)
# Expect: "Translation interrupted. Progress has been saved; re-run translate to resume."
# Expect exit 130; session lease cleared by product (no manual rm)
uv run lilt -C "$ASSET" pipeline translate main
# Expect: resumes remaining work / no NamespaceBusyError from a stale self-lock
```

If no LLM is available: mark **N/A** in hub status; Evidence remains `implemented`
when this path is documented (same posture as other RV-gated hubs).

## Integrity

- `.lilt/tm/main.jsonl` remains readable after CV probes
- Review / Human Review queue: **N/A** (other hub)
- Build fail-closed: optional smoke; not required for lease claims

## Non-goals

Human Review assets; stress/chaos; inventing claims beyond CL-150–152;
Workflow partial-sync messaging (CL-122).

## Related

[../HUB_STATUS.md](../HUB_STATUS.md) · [../../CLAIMS.md](../../CLAIMS.md) ·
`tests/release/test_session_lock_stale.py` · `tests/test_session_reclaim_contracts.py`
