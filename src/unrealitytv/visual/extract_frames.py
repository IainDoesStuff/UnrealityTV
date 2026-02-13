"""Frame extraction module for converting video files to JPEG frames."""

from __future__ import annotations

import logging
import re
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)


class FrameExtractionError(Exception):
    """Exception raised when frame extraction fails."""

    pass


def extract_frames(
    video_path: Path, output_dir: Path, fps: float = 1.0
) -> list[tuple[int, Path]]:
    """Extract frames from a video using FFmpeg at specified FPS.

    This function uses FFmpeg to extract frames from a video file at a specified
    frame rate. Frames are saved as JPEG images in the output directory with
    filenames like frame_000001.jpg, frame_000002.jpg, etc.

    Args:
        video_path: Path to the input video file
        output_dir: Directory where extracted frames will be saved
        fps: Frames per second to extract (default: 1.0)

    Returns:
        List of (timestamp_ms, frame_path) tuples sorted by timestamp_ms.
        - timestamp_ms: Milliseconds since video start (0-based indexing)
        - frame_path: Path to extracted JPEG frame

    Raises:
        FileNotFoundError: If input file doesn't exist or FFmpeg is not installed
        FrameExtractionError: If FFmpeg command fails
    """
    if not video_path.exists():
        msg = f"Input file does not exist: {video_path}"
        logger.error(msg)
        raise FileNotFoundError(msg)

    # Ensure output directory exists
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        logger.info(f"Extracting frames from {video_path} at {fps} FPS to {output_dir}")
        subprocess.run(
            [
                "ffmpeg",
                "-i",
                str(video_path),
                "-vf",
                f"fps={fps}",
                "-q:v",
                "2",
                str(output_dir / "frame_%06d.jpg"),
            ],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        logger.info(f"Successfully extracted frames to {output_dir}")
    except FileNotFoundError as e:
        msg = "FFmpeg not installed. Install with: apt-get install ffmpeg (Linux) or brew install ffmpeg (macOS)"
        logger.error(msg)
        raise FileNotFoundError(msg) from e
    except subprocess.CalledProcessError as e:
        stderr = e.stderr.decode("utf-8") if e.stderr else "Unknown error"
        msg = f"FFmpeg failed to extract frames: {stderr}"
        logger.error(msg)
        raise FrameExtractionError(msg) from e

    # Parse frame filenames and calculate timestamps
    extracted_frames = []
    pattern = re.compile(r"frame_(\d{6})\.jpg")

    for frame_file in sorted(output_dir.glob("frame_*.jpg")):
        match = pattern.match(frame_file.name)
        if match:
            # FFmpeg outputs 1-based frame numbers (frame_000001.jpg, etc.)
            # Convert to 0-based index for timestamp calculation
            frame_number = int(match.group(1))
            frame_index = frame_number - 1
            timestamp_ms = int((frame_index / fps) * 1000)
            extracted_frames.append((timestamp_ms, frame_file))

    # Sort by timestamp (should already be sorted, but ensure it)
    extracted_frames.sort(key=lambda x: x[0])

    logger.info(f"Extracted {len(extracted_frames)} frames from {video_path}")
    return extracted_frames
