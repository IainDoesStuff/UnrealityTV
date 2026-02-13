"""Visual duplicate frame detector using perceptual hashing."""

from __future__ import annotations

import logging
import tempfile
from pathlib import Path

from unrealitytv.db import Database
from unrealitytv.models import SkipSegment
from unrealitytv.visual.duplicate_finder import DuplicateFinder
from unrealitytv.visual.extract_frames import FrameExtractionError, extract_frames
from unrealitytv.visual.hashing import compute_hashes_batch

logger = logging.getLogger(__name__)


def detect_visual_duplicates(
    video_path: Path,
    db: Database | None = None,
    episode_id: int | None = None,
    fps: float = 1.0,
    hamming_threshold: int = 8,
    min_duration_ms: int = 3000,
    gap_tolerance_ms: int = 2000,
) -> list[SkipSegment]:
    """Detect visually duplicate frames across episodes.

    Extracts frames from video, computes perceptual hashes, and compares them
    against previously analyzed episodes to find repeated scenes (flashbacks,
    opening sequences, etc.).

    Args:
        video_path: Path to input video file
        db: Optional Database instance for cross-episode comparison
        episode_id: Optional episode ID for storing/comparing hashes
        fps: Frames per second for extraction (default: 1.0)
        hamming_threshold: Hamming distance threshold for matching (0-64, default: 8)
        min_duration_ms: Minimum segment duration in milliseconds (default: 3000)
        gap_tolerance_ms: Maximum gap between consecutive matches to group (default: 2000)

    Returns:
        List of SkipSegment objects with type="flashback" for detected duplicates

    Raises:
        FrameExtractionError: If frame extraction fails
    """
    if not video_path.exists():
        msg = f"Video file not found: {video_path}"
        logger.error(msg)
        raise FileNotFoundError(msg)

    # If no database provided, return empty results (standalone mode)
    if not db or not episode_id:
        logger.info(
            "Skipping visual duplicate detection: database and episode_id required"
        )
        return []

    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            # Extract frames
            logger.info(f"Extracting frames from {video_path} at {fps} FPS")
            temp_path = Path(temp_dir)
            frame_list = extract_frames(video_path, temp_path, fps=fps)

            if not frame_list:
                logger.warning(f"No frames extracted from {video_path}")
                return []

            # Compute hashes
            logger.info(f"Computing hashes for {len(frame_list)} frames")
            hashes = compute_hashes_batch(frame_list)

            if not hashes:
                logger.warning("No valid hashes computed from frames")
                return []

            # Store hashes in database
            from unrealitytv.db import FrameHashRepository

            repo = FrameHashRepository(db)
            try:
                inserted = repo.add_hashes_batch(episode_id, hashes)
                logger.info(f"Stored {inserted} frame hashes for episode {episode_id}")
            except Exception as e:
                logger.warning(f"Failed to store hashes: {e}")
                # Continue without storing, but can't compare cross-episode

            # Find cross-episode duplicates
            finder = DuplicateFinder(db, hamming_threshold=hamming_threshold)
            try:
                duplicates = finder.find_duplicates_for_hashes(episode_id, hashes)
                logger.info(f"Found {len(duplicates)} duplicate matches")
            except Exception as e:
                logger.warning(f"Failed to find duplicates: {e}")
                duplicates = []

        # Group consecutive duplicates into segments
        segments = _group_duplicates_into_segments(
            duplicates, min_duration_ms, gap_tolerance_ms
        )
        logger.info(f"Created {len(segments)} flashback segments")
        return segments

    except FrameExtractionError as e:
        logger.error(f"Frame extraction failed: {e}")
        raise
    except Exception as e:
        logger.error(f"Visual duplicate detection failed: {e}")
        raise


def _group_duplicates_into_segments(
    duplicates: list, min_duration_ms: int, gap_tolerance_ms: int
) -> list[SkipSegment]:
    """Group consecutive duplicate matches into skip segments.

    Args:
        duplicates: List of DuplicateMatch objects
        min_duration_ms: Minimum segment duration in milliseconds
        gap_tolerance_ms: Maximum gap between consecutive matches

    Returns:
        List of SkipSegment objects
    """
    if not duplicates:
        return []

    segments = []
    current_group = [duplicates[0]]

    for i in range(1, len(duplicates)):
        current = duplicates[i]
        previous = duplicates[i - 1]

        # Check if within gap tolerance
        if current.source_timestamp_ms - previous.source_timestamp_ms <= gap_tolerance_ms:
            current_group.append(current)
        else:
            # End current group and start new one
            segment = _create_segment_from_group(current_group, min_duration_ms)
            if segment:
                segments.append(segment)
            current_group = [current]

    # Process final group
    segment = _create_segment_from_group(current_group, min_duration_ms)
    if segment:
        segments.append(segment)

    return segments


def _create_segment_from_group(
    group: list, min_duration_ms: int
) -> SkipSegment | None:
    """Create a skip segment from a group of matches.

    Args:
        group: List of DuplicateMatch objects
        min_duration_ms: Minimum segment duration in milliseconds

    Returns:
        SkipSegment if group meets duration threshold, None otherwise
    """
    if not group:
        return None

    start_ms = group[0].source_timestamp_ms
    end_ms = group[-1].source_timestamp_ms + 1000  # Add 1 second for last frame

    duration_ms = end_ms - start_ms
    if duration_ms < min_duration_ms:
        return None

    # Calculate average Hamming distance and confidence
    avg_distance = sum(m.hamming_distance for m in group) / len(group)
    confidence = max(0.0, min(1.0, 1.0 - (avg_distance / 64)))

    reason = f"visual_duplicate({len(group)} frames, avg_distance={avg_distance:.1f})"

    return SkipSegment(
        start_ms=start_ms,
        end_ms=end_ms,
        segment_type="flashback",
        confidence=confidence,
        reason=reason,
    )
