"""SIGINT/SIGTERM release lease and exit 130 (R-01-F3 / SM-13..SM-14).

LLM-free subprocess: holds ``namespace_session``, installs the same abort
handlers as ``pipeline translate``, waits on a ready file, then exits 130.
"""

from __future__ import annotations

import os
import signal
import subprocess
import sys
import textwrap
import time
from pathlib import Path

import pytest

from lilt.models.segment import SegmentStatus, StoredSegment
from lilt.tm.repository import TMRepository
from lilt.tm.session_lease import lease_path_for_session_lock

pytestmark = pytest.mark.release

_HOLDER = textwrap.dedent(
    """
    import signal
    import sys
    import time
    from pathlib import Path

    from lilt.core.translation.abort import check_abort, clear_abort, request_abort
    from lilt.tm.repository import TMRepository

    ready = Path(sys.argv[1])
    tm_dir = sys.argv[2]

    clear_abort()

    def _on_abort(_signum, _frame):
        request_abort()

    signal.signal(signal.SIGINT, _on_abort)
    signal.signal(signal.SIGTERM, _on_abort)

    repo = TMRepository(tm_dir)
    try:
        with repo.namespace_session("main"):
            ready.write_text("ready", encoding="utf-8")
            while True:
                check_abort()
                time.sleep(0.02)
    except KeyboardInterrupt:
        sys.exit(130)
    """
)


def _wait_ready(
    path: Path, proc: subprocess.Popen[str], timeout_s: float = 5.0
) -> None:
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        if path.exists():
            return
        if proc.poll() is not None:
            raise AssertionError(
                f"holder exited early code={proc.returncode} stderr={proc.stderr}"
            )
        time.sleep(0.02)
    raise AssertionError("ready file not created before timeout")


@pytest.mark.parametrize(
    "sig", [signal.SIGINT, signal.SIGTERM], ids=["SIGINT", "SIGTERM"]
)
def test_signal_aborts_session_exit_130(tmp_path: Path, sig: signal.Signals) -> None:
    if not hasattr(os, "kill"):
        pytest.skip("os.kill unavailable")

    tm_root = tmp_path / "ws"
    tm_root.mkdir()
    repo = TMRepository(str(tm_root))
    repo.save_namespace(
        "main",
        [
            StoredSegment(
                id="dddddddddddd",
                source_hash="dddddddddddd",
                source_text="Signal hold",
                status=SegmentStatus.GENERATED,
            )
        ],
    )
    lock_path = repo._get_session_lock_path("main")
    meta_path = lease_path_for_session_lock(lock_path)
    before = Path(repo._get_filepath("main")).read_bytes()

    ready = tmp_path / "ready"
    script = tmp_path / "holder.py"
    script.write_text(_HOLDER, encoding="utf-8")

    proc = subprocess.Popen(
        [sys.executable, str(script), str(ready), str(tm_root)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        _wait_ready(ready, proc)
        assert os.path.exists(meta_path)
        os.kill(proc.pid, sig)
        code = proc.wait(timeout=5)
        assert code == 130, (
            f"expected 130 got {code}; stderr={proc.stderr.read() if proc.stderr else ''}"
        )
    finally:
        if proc.poll() is None:
            proc.kill()
            proc.wait(timeout=2)

    assert not os.path.exists(meta_path)
    assert Path(repo._get_filepath("main")).read_bytes() == before
