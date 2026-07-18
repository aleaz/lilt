"""Automated coverage for validation edge scenarios (VAL-TM-003, VAL-TM-005)."""

import json
import os
import tempfile

import yaml

from lilt.models.segment import FileFormat, SegmentStatus, StoredSegment
from lilt.services.tm_service import TMService
from lilt.tm.checkpoint import TranslationCheckpoint
from lilt.tm.repository import TMRepository


def _segment(seg_id: str, text: str, translation: str = "") -> StoredSegment:
    return StoredSegment(
        id=seg_id,
        source_hash=f"hash-{seg_id}",
        source_text=text,
        status=SegmentStatus.GENERATED,
        translation=translation,
    )


def test_val_tm_003_checkpoint_survives_interrupted_finalize():
    """VAL-TM-003: progress persists when finalize_stage has not run yet."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo = TMRepository(base_dir=tmpdir)
        checkpoint = TranslationCheckpoint(repo)
        namespace = "partial"
        seg = _segment("a", "Hello")

        repo.save_namespace(namespace, [seg])
        seg.translation = "Partial"
        checkpoint.record_segment(namespace, seg)

        loaded = repo.load_namespace(namespace)
        assert loaded["a"].translation == "Partial"


def test_val_tm_005_tm_export_import_roundtrip():
    """VAL-TM-005: export/import preserves segment translations."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_dir = os.path.join(tmpdir, ".lilt")
        os.makedirs(config_dir, exist_ok=True)
        with open(
            os.path.join(config_dir, "lilt.yaml"), "w", encoding="utf-8"
        ) as handle:
            yaml.dump({"project": {"source_lang": "en", "target_lang": "es"}}, handle)

        repo = TMRepository(base_dir=os.path.join(config_dir, "tm"))
        repo.save_namespace(
            "intro",
            [
                StoredSegment(
                    id="seg1",
                    source_hash="hash-seg1",
                    source_text="Hello world",
                    status=SegmentStatus.REFINED,
                    translation="Hola mundo",
                )
            ],
        )

        service = TMService(tmpdir)
        export_path = os.path.join(tmpdir, "export.json")
        service.export_tm("intro", export_path)

        with open(export_path, encoding="utf-8") as handle:
            data = json.load(handle)
        data[0]["translation"] = "Hola importada"
        with open(export_path, "w", encoding="utf-8") as handle:
            json.dump(data, handle, ensure_ascii=False)

        updated, skipped = repo.import_data("intro", export_path, FileFormat.JSON)
        assert updated == 1
        assert skipped == 0
        loaded = repo.load_namespace("intro")["seg1"]
        assert loaded.translation == "Hola importada"
        assert loaded.status == SegmentStatus.REVIEWED
