import csv
import json
import os
import tempfile

from lilt.models.segment import (
    FileFormat,
    SegmentStatus,
    StageArtifact,
    StoredSegment,
)
from lilt.tm.repository import TMRepository


def setup_mock_repo(tmpdir: str) -> TMRepository:
    repo = TMRepository(base_dir=tmpdir)
    segments = [
        StoredSegment(
            id="seg1",
            source_hash="seg1",
            source_text="Source 1",
            status=SegmentStatus.GENERATED,
            translation="",
        ),
        StoredSegment(
            id="seg2",
            source_hash="seg2",
            source_text="Source 2",
            status=SegmentStatus.REVIEWED,
            translation="Traduccion 2",
        ),
        StoredSegment(
            id="seg3",
            source_hash="seg3",
            source_text="Source 3",
            status=SegmentStatus.APPROVED,
            translation="Traduccion 3",
        ),
        StoredSegment(
            id="seg4",
            source_hash="seg4",
            source_text="Source 4",
            status=SegmentStatus.DEPRECATED,
            translation="Traduccion Vieja",
        ),
        StoredSegment(
            id="seg5",
            source_hash="seg5",
            source_text="Source 5",
            status=SegmentStatus.REFINED,
            translation="Traduccion 5",
        ),
        StoredSegment(
            id="seg6",
            source_hash="seg6",
            source_text="Source 6",
            status=SegmentStatus.LOCKED,
            translation="Traduccion bloqueada",
        ),
    ]
    repo.save_namespace("mock", segments)
    return repo


def test_reset_includes_drafted_and_critiqued():
    with tempfile.TemporaryDirectory() as tmpdir:
        repo = TMRepository(base_dir=tmpdir)
        segments = [
            StoredSegment(
                id="drafted",
                source_hash="drafted",
                source_text="Source drafted",
                status=SegmentStatus.DRAFTED,
                translation="",
            ),
            StoredSegment(
                id="critiqued",
                source_hash="critiqued",
                source_text="Source critiqued",
                status=SegmentStatus.CRITIQUED,
                translation="",
            ),
        ]
        repo.save_namespace("mock", segments)

        affected = repo.reset_namespace("mock", dry_run=False)
        assert len(affected) == 2
        loaded = repo.load_namespace("mock")
        assert loaded["drafted"].status == SegmentStatus.GENERATED
        assert loaded["critiqued"].status == SegmentStatus.GENERATED


def test_import_status_only_rejects_invalid_translation():
    with tempfile.TemporaryDirectory() as tmpdir:
        repo = TMRepository(base_dir=tmpdir)
        repo.save_namespace(
            "mock",
            [
                StoredSegment(
                    id="segph",
                    source_hash="segph",
                    source_text='Hello <macro id="1"/>',
                    status=SegmentStatus.REFINED,
                    translation="Hola sin placeholder",
                )
            ],
        )
        csv_path = os.path.join(tmpdir, "status_only.csv")
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["ID", "Status", "Source", "Translation"])
            writer.writerow(
                ["segph", "approved", 'Hello <macro id="1"/>', "Hola sin placeholder"]
            )

        updated, skipped = repo.import_data("mock", csv_path, FileFormat.CSV)
        assert updated == 0
        assert skipped == 1
        loaded = repo.load_namespace("mock")
        assert loaded["segph"].status == SegmentStatus.REFINED


def test_reset_namespace():
    with tempfile.TemporaryDirectory() as tmpdir:
        repo = setup_mock_repo(tmpdir)

        # Without force: only machine states (REFINED, CONFLICT) are reset
        affected = repo.reset_namespace("mock", dry_run=True)
        assert len(affected) == 1  # seg5 (REFINED) only

        loaded = repo.load_namespace("mock")
        assert loaded["seg2"].status == SegmentStatus.REVIEWED
        assert loaded["seg3"].status == SegmentStatus.APPROVED

        affected = repo.reset_namespace("mock", dry_run=False)
        assert len(affected) == 1
        loaded = repo.load_namespace("mock")
        assert loaded["seg5"].status == SegmentStatus.GENERATED
        assert loaded["seg5"].translation == ""
        assert len(loaded["seg5"].history) == 1
        assert loaded["seg2"].status == SegmentStatus.REVIEWED
        assert loaded["seg3"].status == SegmentStatus.APPROVED

        # With force: human-reviewed segments are also reset
        affected = repo.reset_namespace("mock", dry_run=False, force=True)
        assert len(affected) == 2  # seg2 REVIEWED, seg3 APPROVED
        loaded = repo.load_namespace("mock")
        assert loaded["seg2"].status == SegmentStatus.GENERATED
        assert loaded["seg2"].translation == ""
        assert len(loaded["seg2"].history) == 1
        assert loaded["seg3"].status == SegmentStatus.GENERATED
        assert (
            loaded["seg4"].status == SegmentStatus.DEPRECATED
        )  # Should not be affected
        assert loaded["seg6"].status == SegmentStatus.LOCKED  # Immutable


def test_reset_clears_machine_artifacts():
    with tempfile.TemporaryDirectory() as tmpdir:
        repo = TMRepository(base_dir=tmpdir)
        seg = StoredSegment(
            id="seg1",
            source_hash="seg1",
            source_text="Source",
            status=SegmentStatus.REFINED,
            translation="Traduccion",
            draft=StageArtifact(content="draft", model="m"),
            critique=StageArtifact(content="critique", model="m"),
        )
        repo.save_namespace("mock", [seg])

        repo.reset_namespace("mock", dry_run=False)
        loaded = repo.load_namespace("mock")["seg1"]
        assert loaded.status == SegmentStatus.GENERATED
        assert loaded.translation == ""
        assert loaded.draft is None
        assert loaded.critique is None


def test_reset_includes_error_without_force():
    with tempfile.TemporaryDirectory() as tmpdir:
        repo = TMRepository(base_dir=tmpdir)
        seg = StoredSegment(
            id="seg1",
            source_hash="seg1",
            source_text="Source",
            status=SegmentStatus.ERROR,
            translation="",
        )
        repo.save_namespace("mock", [seg])

        affected = repo.reset_namespace("mock", dry_run=False)
        assert len(affected) == 1
        assert repo.load_namespace("mock")["seg1"].status == SegmentStatus.GENERATED

    with tempfile.TemporaryDirectory() as tmpdir:
        repo = setup_mock_repo(tmpdir)

        # Test Dry Run
        removed = repo.prune_namespace("mock", dry_run=True)
        assert len(removed) == 1
        assert removed[0].id == "seg4"

        # Verify no disk changes
        loaded = repo.load_namespace("mock")
        assert "seg4" in loaded

        # Test Actual Run
        removed = repo.prune_namespace("mock", dry_run=False)
        assert len(removed) == 1

        # Verify disk changes
        loaded = repo.load_namespace("mock")
        assert "seg4" not in loaded
        assert len(loaded) == 5


def test_export_import_csv():
    with tempfile.TemporaryDirectory() as tmpdir:
        repo = setup_mock_repo(tmpdir)
        csv_path = os.path.join(tmpdir, "export.csv")

        # 1. Export
        count = repo.export_data("mock", csv_path, FileFormat.CSV)
        assert count == 5  # seg1-3, seg5, seg6 (seg4 deprecated excluded)
        assert os.path.exists(csv_path)

        # 2. Modify CSV to simulate human review
        with open(csv_path, encoding="utf-8") as f:
            reader = list(csv.DictReader(f))

        assert len(reader) == 5
        seg_by_id = {row["ID"]: row for row in reader}
        seg_by_id["seg5"]["Translation"] = "Human translation 5"
        seg_by_id["seg3"]["Translation"] = "Human modified translation 3"
        reader = list(seg_by_id.values())

        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(
                f, fieldnames=["ID", "Status", "Source", "Translation"]
            )
            writer.writeheader()
            writer.writerows(reader)

        # 3. Import
        updated, skipped = repo.import_data("mock", csv_path, FileFormat.CSV)
        assert updated == 2
        assert skipped == 3

        # 4. Verify TM updates
        loaded = repo.load_namespace("mock")
        assert loaded["seg5"].translation == "Human translation 5"
        assert loaded["seg5"].status == SegmentStatus.REVIEWED
        assert len(loaded["seg5"].history) == 1

        assert loaded["seg2"].translation == "Traduccion 2"
        assert loaded["seg2"].status == SegmentStatus.REVIEWED  # Unchanged

        assert loaded["seg3"].translation == "Human modified translation 3"
        assert loaded["seg3"].status == SegmentStatus.REVIEWED
        assert len(loaded["seg3"].history) == 1


def test_import_skips_locked_segment():
    with tempfile.TemporaryDirectory() as tmpdir:
        repo = setup_mock_repo(tmpdir)
        csv_path = os.path.join(tmpdir, "locked_import.csv")
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["ID", "Status", "Source", "Translation"])
            writer.writerow(
                ["seg6", "locked", "Source 6", "Attempted override translation"]
            )

        updated, skipped = repo.import_data("mock", csv_path, FileFormat.CSV)
        assert updated == 0
        assert skipped == 1

        loaded = repo.load_namespace("mock")
        assert loaded["seg6"].translation == "Traduccion bloqueada"
        assert loaded["seg6"].status == SegmentStatus.LOCKED


def test_import_refined_records_history():
    with tempfile.TemporaryDirectory() as tmpdir:
        repo = setup_mock_repo(tmpdir)
        csv_path = os.path.join(tmpdir, "refined_import.csv")
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["ID", "Status", "Source", "Translation"])
            writer.writerow(
                ["seg5", "refined", "Source 5", "Imported refined translation"]
            )

        updated, skipped = repo.import_data("mock", csv_path, FileFormat.CSV)
        assert updated == 1
        assert skipped == 0

        loaded = repo.load_namespace("mock")
        assert loaded["seg5"].translation == "Imported refined translation"
        assert loaded["seg5"].status == SegmentStatus.REVIEWED
        assert len(loaded["seg5"].history) == 1
        assert loaded["seg5"].history[0].translation == "Traduccion 5"
        assert loaded["seg5"].history[0].status == SegmentStatus.REFINED


def test_export_import_json():
    with tempfile.TemporaryDirectory() as tmpdir:
        repo = setup_mock_repo(tmpdir)
        json_path = os.path.join(tmpdir, "export.json")

        # 1. Export
        count = repo.export_data("mock", json_path, FileFormat.JSON)
        assert count == 5
        assert os.path.exists(json_path)

        # 2. Modify JSON to simulate human review
        with open(json_path, encoding="utf-8") as f:
            data = json.load(f)

        assert len(data) == 5
        data_by_id = {row["id"]: row for row in data}
        data_by_id["seg5"]["translation"] = "Human translation 5"
        data_by_id["seg3"]["translation"] = "Human modified translation 3"
        data = list(data_by_id.values())

        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        # 3. Import
        updated, skipped = repo.import_data("mock", json_path, FileFormat.JSON)
        assert updated == 2
        assert skipped == 3

        # 4. Verify TM updates
        loaded = repo.load_namespace("mock")
        assert loaded["seg5"].translation == "Human translation 5"
        assert loaded["seg5"].status == SegmentStatus.REVIEWED

        assert loaded["seg2"].translation == "Traduccion 2"
        assert loaded["seg2"].status == SegmentStatus.REVIEWED

        assert loaded["seg3"].translation == "Human modified translation 3"
        assert loaded["seg3"].status == SegmentStatus.REVIEWED
