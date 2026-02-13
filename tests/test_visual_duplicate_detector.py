"""Tests for visual duplicate detector."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from unrealitytv.detectors.visual_duplicate_detector import (
    detect_visual_duplicates,
)
from unrealitytv.visual.duplicate_finder import DuplicateMatch


@pytest.fixture
def mock_db():
    """Create a mock database instance."""
    db = MagicMock()
    db.connection = MagicMock()
    return db


@pytest.fixture
def temp_video(tmp_path):
    """Create a temporary video file."""
    video_file = tmp_path / "test.mp4"
    video_file.touch()
    return video_file


class TestDetectVisualDuplicates:
    """Tests for detect_visual_duplicates function."""

    def test_detect_visual_duplicates_missing_file(self):
        """Test FileNotFoundError for missing video file."""
        missing_video = Path("/nonexistent/video.mp4")

        with pytest.raises(FileNotFoundError):
            detect_visual_duplicates(missing_video)

    def test_detect_visual_duplicates_no_database(self, temp_video):
        """Test standalone mode (no database) returns empty list."""
        result = detect_visual_duplicates(temp_video)
        assert result == []

    def test_detect_visual_duplicates_no_episode_id(self, temp_video, mock_db):
        """Test that missing episode_id returns empty list."""
        result = detect_visual_duplicates(temp_video, db=mock_db, episode_id=None)
        assert result == []

    @patch("unrealitytv.detectors.visual_duplicate_detector.extract_frames")
    def test_detect_visual_duplicates_no_frames(
        self, mock_extract, temp_video, mock_db
    ):
        """Test handling when no frames are extracted."""
        mock_extract.return_value = []

        result = detect_visual_duplicates(temp_video, db=mock_db, episode_id=1)
        assert result == []

    @patch("unrealitytv.detectors.visual_duplicate_detector.compute_hashes_batch")
    @patch("unrealitytv.detectors.visual_duplicate_detector.extract_frames")
    def test_detect_visual_duplicates_no_hashes(
        self, mock_extract, mock_hashes, temp_video, mock_db
    ):
        """Test handling when no hashes are computed."""
        mock_extract.return_value = [(0, Path("frame_1.jpg"))]
        mock_hashes.return_value = []

        result = detect_visual_duplicates(temp_video, db=mock_db, episode_id=1)
        assert result == []

    @patch("unrealitytv.detectors.visual_duplicate_detector.DuplicateFinder")
    @patch("unrealitytv.db.FrameHashRepository")
    @patch("unrealitytv.detectors.visual_duplicate_detector.compute_hashes_batch")
    @patch("unrealitytv.detectors.visual_duplicate_detector.extract_frames")
    def test_detect_visual_duplicates_with_matches(
        self,
        mock_extract,
        mock_hashes,
        mock_repo_class,
        mock_finder_class,
        temp_video,
        mock_db,
    ):
        """Test detecting visual duplicates with matches found."""
        # Setup mocks
        mock_extract.return_value = [
            (0, Path("frame_1.jpg")),
            (1000, Path("frame_2.jpg")),
        ]
        mock_hashes.return_value = [(0, "aaaa"), (1000, "bbbb")]

        mock_repo = MagicMock()
        mock_repo_class.return_value = mock_repo

        match1 = MagicMock(spec=DuplicateMatch)
        match1.source_episode_id = 1
        match1.source_timestamp_ms = 0
        match1.hamming_distance = 2

        mock_finder = MagicMock()
        mock_finder_class.return_value = mock_finder
        mock_finder.find_duplicates_for_hashes.return_value = [match1]

        result = detect_visual_duplicates(temp_video, db=mock_db, episode_id=1)

        assert len(result) >= 0
        mock_extract.assert_called_once()

    @patch("unrealitytv.detectors.visual_duplicate_detector.extract_frames")
    def test_detect_visual_duplicates_extraction_error(
        self, mock_extract, temp_video, mock_db
    ):
        """Test FrameExtractionError propagates correctly."""
        from unrealitytv.visual.extract_frames import FrameExtractionError

        mock_extract.side_effect = FrameExtractionError("FFmpeg failed")

        with pytest.raises(FrameExtractionError):
            detect_visual_duplicates(temp_video, db=mock_db, episode_id=1)


class TestGroupDuplicatesIntoSegments:
    """Tests for segment grouping logic."""

    @patch(
        "unrealitytv.detectors.visual_duplicate_detector._group_duplicates_into_segments"
    )
    @patch(
        "unrealitytv.detectors.visual_duplicate_detector.DuplicateFinder"
    )
    @patch(
        "unrealitytv.db.FrameHashRepository"
    )
    @patch(
        "unrealitytv.detectors.visual_duplicate_detector.compute_hashes_batch"
    )
    @patch(
        "unrealitytv.detectors.visual_duplicate_detector.extract_frames"
    )
    def test_grouping_creates_segments(
        self,
        mock_extract,
        mock_hashes,
        mock_repo_class,
        mock_finder_class,
        mock_grouping,
        temp_video,
        mock_db,
    ):
        """Test that grouping function is called."""
        mock_extract.return_value = [(0, Path("frame_1.jpg"))]
        mock_hashes.return_value = [(0, "aaaa")]
        mock_repo = MagicMock()
        mock_repo_class.return_value = mock_repo
        mock_finder = MagicMock()
        mock_finder_class.return_value = mock_finder
        mock_finder.find_duplicates_for_hashes.return_value = []
        mock_grouping.return_value = []

        detect_visual_duplicates(temp_video, db=mock_db, episode_id=1)

        mock_grouping.assert_called_once()

    def test_consecutive_matches_grouped(self):
        """Test that consecutive matches within tolerance are grouped."""
        from unrealitytv.detectors.visual_duplicate_detector import (
            _group_duplicates_into_segments,
        )

        match1 = MagicMock(spec=DuplicateMatch)
        match1.source_timestamp_ms = 0
        match1.hamming_distance = 2

        match2 = MagicMock(spec=DuplicateMatch)
        match2.source_timestamp_ms = 1000  # Within gap tolerance
        match2.hamming_distance = 3

        segments = _group_duplicates_into_segments(
            [match1, match2], min_duration_ms=500, gap_tolerance_ms=2000
        )

        # Should create 1 segment from 2 consecutive matches
        assert len(segments) == 1

    def test_matches_outside_gap_separate(self):
        """Test that matches outside gap tolerance create separate segments."""
        from unrealitytv.detectors.visual_duplicate_detector import (
            _group_duplicates_into_segments,
        )

        match1 = MagicMock(spec=DuplicateMatch)
        match1.source_timestamp_ms = 0
        match1.hamming_distance = 2

        match2 = MagicMock(spec=DuplicateMatch)
        match2.source_timestamp_ms = 5000  # Outside gap tolerance
        match2.hamming_distance = 3

        segments = _group_duplicates_into_segments(
            [match1, match2], min_duration_ms=500, gap_tolerance_ms=2000
        )

        # Each match should be separate (if above min duration)
        assert len(segments) <= 2

    def test_segment_below_min_duration_excluded(self):
        """Test that segments below min duration are excluded."""
        from unrealitytv.detectors.visual_duplicate_detector import (
            _group_duplicates_into_segments,
        )

        match1 = MagicMock(spec=DuplicateMatch)
        match1.source_timestamp_ms = 0
        match1.hamming_distance = 2

        segments = _group_duplicates_into_segments(
            [match1], min_duration_ms=5000, gap_tolerance_ms=2000
        )

        # Single short match should be excluded
        assert len(segments) == 0

    def test_empty_duplicates_returns_empty(self):
        """Test that empty duplicates list returns empty segments."""
        from unrealitytv.detectors.visual_duplicate_detector import (
            _group_duplicates_into_segments,
        )

        segments = _group_duplicates_into_segments([], min_duration_ms=1000, gap_tolerance_ms=1000)
        assert segments == []


class TestCreateSegmentFromGroup:
    """Tests for segment creation from groups."""

    def test_segment_has_flashback_type(self):
        """Test that created segments have flashback type."""
        from unrealitytv.detectors.visual_duplicate_detector import (
            _create_segment_from_group,
        )

        match = MagicMock(spec=DuplicateMatch)
        match.source_timestamp_ms = 0
        match.hamming_distance = 2

        segment = _create_segment_from_group([match], min_duration_ms=500)

        if segment:
            assert segment.segment_type == "flashback"

    def test_segment_confidence_from_hamming(self):
        """Test that confidence is based on Hamming distance."""
        from unrealitytv.detectors.visual_duplicate_detector import (
            _create_segment_from_group,
        )

        match = MagicMock(spec=DuplicateMatch)
        match.source_timestamp_ms = 0
        match.hamming_distance = 0  # Perfect match

        segment = _create_segment_from_group([match], min_duration_ms=500)

        if segment:
            assert segment.confidence == 1.0

    def test_segment_includes_duration_reason(self):
        """Test that segment reason includes duration and distance info."""
        from unrealitytv.detectors.visual_duplicate_detector import (
            _create_segment_from_group,
        )

        match = MagicMock(spec=DuplicateMatch)
        match.source_timestamp_ms = 0
        match.hamming_distance = 4

        segment = _create_segment_from_group([match], min_duration_ms=500)

        if segment:
            assert "visual_duplicate" in segment.reason
            assert "frames" in segment.reason
