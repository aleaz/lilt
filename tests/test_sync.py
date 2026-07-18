from unittest.mock import MagicMock, patch

from lilt.core.sync import sync_file
from lilt.models.segment import SegmentStatus, StoredSegment
from lilt.models.sync_result import SyncResult


def _minimal_segment(segment_id: str) -> StoredSegment:
    return StoredSegment(
        id=segment_id,
        source_hash="a" * 64,
        source_text="text",
        status=SegmentStatus.GENERATED,
    )


def test_sync_file():
    mock_parser = MagicMock()
    mock_tm = MagicMock()

    mock_seg1 = MagicMock()
    mock_seg1.is_translatable.return_value = True
    mock_seg2 = MagicMock()
    mock_seg2.is_translatable.return_value = True
    mock_segments = [mock_seg1, mock_seg2]
    mock_parser.parse_file.return_value = mock_segments

    active = [_minimal_segment("seg1"), _minimal_segment("seg2")]

    with patch("lilt.core.sync.sync_parsed_blocks") as mock_sync_parsed:
        mock_sync_parsed.return_value = SyncResult(
            namespace="namespace1",
            active_segments=active,
        )

        result = sync_file("test.tex", mock_tm, "namespace1", mock_parser)
        assert result.namespace == "namespace1"

    mock_parser.parse_file.assert_called_once_with("test.tex")

    assert result.total_active == 2
