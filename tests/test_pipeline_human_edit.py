import os
import tempfile

import yaml

from lilt.exceptions import TranslationValidationError
from lilt.models.segment import SegmentStatus, StoredSegment
from lilt.services.pipeline_service import PipelineService
from lilt.tm.repository import TMRepository


def _setup_workspace(tmpdir: str) -> PipelineService:
    config_dir = os.path.join(tmpdir, ".lilt")
    os.makedirs(config_dir, exist_ok=True)
    with open(os.path.join(config_dir, "lilt.yaml"), "w", encoding="utf-8") as f:
        yaml.dump({"project": {"source_lang": "en", "target_lang": "es"}}, f)

    repo = TMRepository(base_dir=os.path.join(config_dir, "tm"))
    repo.save_namespace(
        "mock",
        [
            StoredSegment(
                id="abcd1234efgh",
                source_hash="abcd1234efgh",
                source_text='Text with <macro id="1"/> here.',
                status=SegmentStatus.REVIEWED,
                translation='Texto con <macro id="1"/> aqui.',
            )
        ],
    )
    return PipelineService(tmpdir)


def test_submit_human_translation_valid():
    with tempfile.TemporaryDirectory() as tmpdir:
        service = _setup_workspace(tmpdir)
        service.submit_human_translation(
            "mock",
            "abcd1234",
            'Texto con <macro id="1"/> aqui.',
        )
        seg = service.get_segment("mock", "abcd1234")
        assert seg.status == SegmentStatus.APPROVED


def test_submit_human_translation_rejects_bad_placeholder():
    with tempfile.TemporaryDirectory() as tmpdir:
        service = _setup_workspace(tmpdir)
        try:
            service.submit_human_translation(
                "mock",
                "abcd1234",
                "Texto sin placeholder.",
            )
            raise AssertionError("Expected TranslationValidationError")
        except TranslationValidationError as exc:
            assert "Placeholder mismatch" in str(exc)

        seg = service.get_segment("mock", "abcd1234")
        assert seg.status == SegmentStatus.REVIEWED


def test_update_segment_translation_rejects_bad_placeholder():
    with tempfile.TemporaryDirectory() as tmpdir:
        service = _setup_workspace(tmpdir)
        try:
            service.update_segment_translation(
                "mock",
                "abcd1234",
                "Texto sin placeholder.",
                SegmentStatus.CONFLICT,
            )
            raise AssertionError("Expected TranslationValidationError")
        except TranslationValidationError:
            pass
        seg = service.get_segment("mock", "abcd1234")
        assert seg.translation == 'Texto con <macro id="1"/> aqui.'
        assert seg.status == SegmentStatus.REVIEWED


def test_update_segment_translation_same_text_reject_ok():
    with tempfile.TemporaryDirectory() as tmpdir:
        service = _setup_workspace(tmpdir)
        service.update_segment_translation(
            "mock",
            "abcd1234",
            'Texto con <macro id="1"/> aqui.',
            SegmentStatus.CONFLICT,
        )
        seg = service.get_segment("mock", "abcd1234")
        assert seg.status == SegmentStatus.CONFLICT
    with tempfile.TemporaryDirectory() as tmpdir:
        service = _setup_workspace(tmpdir)
        repo = TMRepository(base_dir=os.path.join(tmpdir, ".lilt", "tm"))
        repo.save_namespace(
            "done_ns",
            [
                StoredSegment(
                    id="seg1",
                    source_hash="hash-seg1",
                    source_text="Hello",
                    status=SegmentStatus.REFINED,
                    translation="Hola",
                )
            ],
        )

        messages = list(service.run_translation("done_ns", force=False))
        done_msg = next(msg for msg in messages if msg[2] == "done")
        assert "already translated" in done_msg[3].lower()


def test_submit_human_translation_from_generated():
    with tempfile.TemporaryDirectory() as tmpdir:
        config_dir = os.path.join(tmpdir, ".lilt")
        os.makedirs(config_dir, exist_ok=True)
        with open(os.path.join(config_dir, "lilt.yaml"), "w", encoding="utf-8") as f:
            yaml.dump({"project": {"source_lang": "en", "target_lang": "es"}}, f)

        repo = TMRepository(base_dir=os.path.join(config_dir, "tm"))
        repo.save_namespace(
            "mock",
            [
                StoredSegment(
                    id="gen1234abcd",
                    source_hash="gen1234abcd",
                    source_text='Text with <macro id="1"/> here.',
                    status=SegmentStatus.GENERATED,
                    translation="",
                )
            ],
        )
        service = PipelineService(tmpdir)
        service.submit_human_translation(
            "mock",
            "gen1234",
            'Texto con <macro id="1"/> aqui.',
        )
        seg = service.get_segment("mock", "gen1234")
        assert seg.status == SegmentStatus.APPROVED
        assert seg.translation == 'Texto con <macro id="1"/> aqui.'
