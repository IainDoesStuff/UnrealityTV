"""Credits detection using frame analysis."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from unrealitytv.models import SceneBoundary

logger = logging.getLogger(__name__)


def detect_credits(
    video_path: Path,
    threshold: float = 0.7,
    min_duration_ms: int = 5000,
    frame_sample_rate: int = 10,
) -> list[SceneBoundary]:
    """Detect credit sequences in a video using frame analysis.

    Uses two strategies to detect credits:
    1. Black frame detection: Pure black frames (pixel values < 30)
    2. Color consistency: Low-variance color frames (indicates static content)

    Args:
        video_path: Path to the video file
        threshold: Confidence threshold for credit detection (default 0.7)
            - For black frame strategy: ratio of black pixels (0-1)
            - For color variance: variance threshold (0-1)
        min_duration_ms: Minimum credit sequence duration in milliseconds (default 5000ms)
        frame_sample_rate: Sample every Nth frame for efficiency (default 10)

    Returns:
        List of detected credit segments as SceneBoundary objects

    Raises:
        RuntimeError: If OpenCV is not installed or video processing fails
        FileNotFoundError: If video file does not exist
    """
    if not video_path.exists():
        msg = f"Video file does not exist: {video_path}"
        logger.error(msg)
        raise FileNotFoundError(msg)

    try:
        import cv2
    except ImportError as e:
        msg = "opencv-python is not installed. Install with: pip install opencv-python"
        logger.error(msg)
        raise RuntimeError(msg) from e

    try:
        from unrealitytv.models import SceneBoundary

        logger.info(
            f"Detecting credits in {video_path.name} "
            f"(threshold: {threshold}, min_duration: {min_duration_ms}ms, "
            f"sample_rate: 1/{frame_sample_rate})"
        )

        # Open video
        cap = cv2.VideoCapture(str(video_path))
        if not cap.isOpened():
            msg = f"Failed to open video file: {video_path}"
            logger.error(msg)
            raise RuntimeError(msg)

        try:
            fps = cap.get(cv2.CAP_PROP_FPS)
            if fps <= 0:
                fps = 30.0  # Default fallback
                logger.warning(f"Invalid FPS from video, using default: {fps}")

            # Analyze frames
            credit_frames: list[bool] = []
            frame_numbers: list[int] = []
            frame_count = 0

            while True:
                ret, frame = cap.read()
                if not ret:
                    break

                frame_number = int(cap.get(cv2.CAP_PROP_POS_FRAMES))

                # Sample frames efficiently
                if frame_number % frame_sample_rate != 0:
                    continue

                is_credit_frame = _is_credit_frame(frame, threshold)
                credit_frames.append(is_credit_frame)
                frame_numbers.append(frame_number)
                frame_count += 1

            if frame_count == 0:
                logger.warning(f"No frames processed in {video_path.name}")
                return []

            # Find contiguous credit regions
            credit_segments: list[SceneBoundary] = []
            in_credits = False
            start_ms = 0.0

            for idx, (frame_num, is_credit) in enumerate(zip(frame_numbers, credit_frames)):
                if not in_credits and is_credit:
                    # Start of credits
                    in_credits = True
                    start_ms = (frame_num / fps) * 1000

                elif in_credits and not is_credit:
                    # End of credits
                    end_frame = frame_numbers[idx - 1]
                    end_ms = (end_frame / fps) * 1000
                    duration_ms = end_ms - start_ms

                    if duration_ms >= min_duration_ms:
                        credit_segments.append(
                            SceneBoundary(
                                start_ms=int(start_ms),
                                end_ms=int(end_ms),
                                scene_index=len(credit_segments),
                            )
                        )
                    in_credits = False

            # Handle credits at end of video
            if in_credits:
                end_frame = frame_numbers[-1]
                end_ms = (end_frame / fps) * 1000
                duration_ms = end_ms - start_ms
                if duration_ms >= min_duration_ms:
                    credit_segments.append(
                        SceneBoundary(
                            start_ms=int(start_ms),
                            end_ms=int(end_ms),
                            scene_index=len(credit_segments),
                        )
                    )

            logger.info(
                f"Detected {len(credit_segments)} credit segments in {video_path.name} "
                f"(analyzed {frame_count} frames)"
            )
            return credit_segments

        finally:
            cap.release()

    except ImportError as e:
        msg = f"Failed to import required module: {e}"
        logger.error(msg)
        raise RuntimeError(msg) from e
    except Exception as e:
        msg = f"Error detecting credits in {video_path}: {e}"
        logger.error(msg)
        raise RuntimeError(msg) from e


def _is_credit_frame(frame, threshold: float) -> bool:
    """Check if a frame is likely part of credits.

    Uses two criteria:
    1. High ratio of black pixels (>threshold)
    2. Low color variance (indicates static/simple content)

    Args:
        frame: OpenCV frame (BGR)
        threshold: Threshold for decision (0-1)

    Returns:
        True if frame appears to be credits, False otherwise
    """
    try:
        import cv2
        import numpy as np
    except ImportError:
        return False

    try:
        # Convert to grayscale
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # Strategy 1: Black frame detection
        # Count pixels below 30 (very dark)
        black_pixels = np.sum(gray < 30)
        total_pixels = gray.shape[0] * gray.shape[1]
        black_ratio = black_pixels / total_pixels

        if black_ratio > threshold:
            return True

        # Strategy 2: Color variance detection
        # Low variance indicates static content (common in credits)
        # Calculate standard deviation of pixel intensities
        color_std = np.std(gray)

        # Normalize std to 0-1 range (max std is ~128 for uniform distribution)
        normalized_std = color_std / 128.0

        # If color variance is very low (< threshold), likely credits
        if normalized_std < (1.0 - threshold):
            return True

        return False
    except Exception:
        return False
