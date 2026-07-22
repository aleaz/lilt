"""Shared fixtures for release-gate regression locks (no live LLM)."""

from __future__ import annotations

import os
from collections.abc import Iterator
from pathlib import Path

import pytest
import yaml
from typer.testing import CliRunner

from lilt.models.segment import ReflectionMeta, SegmentStatus, StoredSegment
from lilt.tm.repository import TMRepository

runner = CliRunner(env={"COLUMNS": "200"})


@pytest.fixture
def workspace(tmp_path: Path) -> Iterator[Path]:
    """Initialized-like workspace with cwd switched into it."""
    original = os.getcwd()
    os.chdir(tmp_path)
    try:
        lilt = tmp_path / ".lilt"
        lilt.mkdir()
        (lilt / "lilt.yaml").write_text(
            yaml.dump(
                {
                    "project": {
                        "source_lang": "English",
                        "target_lang": "Spanish",
                    },
                    "llm": {
                        "provider": "openai",
                        "model": "local-model",
                        "base_url": "http://localhost:1234/v1",
                    },
                }
            ),
            encoding="utf-8",
        )
        (lilt / "tm").mkdir()
        yield tmp_path
    finally:
        os.chdir(original)


def save_segments(
    workspace: Path, namespace: str, segments: list[StoredSegment]
) -> None:
    repo = TMRepository(base_dir=str(workspace / ".lilt" / "tm"))
    repo.save_namespace(namespace, segments)


def make_seg(
    seg_id: str,
    status: SegmentStatus,
    *,
    source: str = "Source text for tokens.",
    translation: str = "Texto traducido.",
    reflection_used: bool = False,
    draft_accepted: bool = False,
) -> StoredSegment:
    meta = None
    if reflection_used:
        meta = ReflectionMeta(used=True, draft_accepted=draft_accepted)
    return StoredSegment(
        id=seg_id,
        source_hash=seg_id,
        source_text=source,
        translation=translation if status != SegmentStatus.GENERATED else "",
        status=status,
        reflection_meta=meta,
    )
