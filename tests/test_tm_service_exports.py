import csv
import json
import os
from pathlib import Path

from lilt.models.segment import SegmentStatus, StoredSegment
from lilt.services.tm_service import TMService


def test_tm_service_stats_and_exports(tmpdir):
    # Setup TM Service and create some dummy data
    workspace = str(tmpdir)
    lilt_dir = Path(workspace) / ".lilt"
    lilt_dir.mkdir(parents=True, exist_ok=True)
    (lilt_dir / "lilt.yaml").write_text(
        "project:\n  source_lang: en\n  target_lang: es\n"
        "llm:\n  base_url: http://127.0.0.1:9\n  model: mock\n",
        encoding="utf-8",
    )
    service = TMService(workspace)

    seg1 = StoredSegment(
        id="abc123def456",
        source_hash="abc123def456",
        source_text="Hello world",
        translation="Hola mundo",
        status=SegmentStatus.APPROVED,
    )
    seg2 = StoredSegment(
        id="xyz987wvu654",
        source_hash="xyz987wvu654",
        source_text="Test segment",
        translation="Segmento de prueba",
        status=SegmentStatus.DRAFTED,
    )

    service.repo.save_namespace("intro", [seg1, seg2])

    # 1. Test Stats
    stats = service.get_stats("intro")
    assert stats["total"] == 2
    assert stats[SegmentStatus.APPROVED.value] == 1
    assert stats[SegmentStatus.DRAFTED.value] == 1

    # 2. Test JSON Export
    json_out = os.path.join(workspace, "out.json")
    service.export_tm("intro", json_out)

    assert os.path.exists(json_out)
    with open(json_out, encoding="utf-8") as f:
        data = json.load(f)
        assert len(data) == 2
        assert data[0]["id"] == "abc123def456"
        assert data[0]["source"] == "Hello world"
        assert data[0]["translation"] == "Hola mundo"

    # 3. Test CSV Export
    csv_out = os.path.join(workspace, "out.csv")
    service.export_tm("intro", csv_out)

    assert os.path.exists(csv_out)
    with open(csv_out, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        assert len(rows) == 2
        assert rows[0]["ID"] == "abc123def456"
        assert rows[0]["Source"] == "Hello world"
        assert rows[0]["Translation"] == "Hola mundo"
        assert rows[0]["Status"] == "approved"
