"""Empty TM namespace files must not abort pipeline translate / --all."""

from __future__ import annotations

import os
import tempfile

import yaml

from lilt.models.segment import SegmentStatus, StoredSegment
from lilt.services.pipeline_service import TranslationOrchestrator
from lilt.services.workspace_context import WorkspaceContext
from lilt.tm.repository import TMRepository


def test_run_translation_idle_skips_empty_namespace_file() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        lilt = os.path.join(tmpdir, ".lilt")
        tm = os.path.join(lilt, "tm")
        os.makedirs(tm)
        with open(os.path.join(lilt, "lilt.yaml"), "w", encoding="utf-8") as f:
            yaml.dump(
                {
                    "project": {"source_lang": "en", "target_lang": "es"},
                    "llm": {"base_url": "http://127.0.0.1:9", "model": "mock"},
                },
                f,
            )
        repo = TMRepository(tm)
        repo.save_namespace("fig__trap", [])
        repo.save_namespace(
            "chapter",
            [
                StoredSegment(
                    id="a" * 40,
                    source_hash="b" * 64,
                    source_text="Hello",
                    status=SegmentStatus.REFINED,
                    translation="Hola",
                )
            ],
        )
        ctx = WorkspaceContext.from_workspace(tmpdir)
        orch = TranslationOrchestrator(ctx)

        events = list(orch.run_translation("fig__trap"))
        assert len(events) == 1
        _cur, total, seg_id, msg, _adv = events[0]
        assert total == 0
        assert seg_id == "done"
        assert "no translatable segments" in msg.lower()

        # Non-empty idle path still works (already translated).
        done_events = list(orch.run_translation("chapter"))
        assert any("already translated" in e[3].lower() for e in done_events)
