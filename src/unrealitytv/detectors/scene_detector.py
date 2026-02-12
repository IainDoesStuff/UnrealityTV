"""Scene boundary detection using PySceneDetect."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from unrealitytv.models import SceneBoundary

try:
    from scenedetect import AdaptiveDetector, SceneManager, VideoManager
except ImportError:
    # Will be caught and handled in the function
    AdaptiveDetector = None  # type: ignore
    SceneManager = None  # type: ignore
    VideoManager = None  # type: ignore

logger = logging.getLogger(__name__)


def detect_scenes(
    video_path: Path,
    threshold: float = 3.0,
    min_scene_len_ms: int = 2000,
) -> list[SceneBoundary]:
    """Detect scene boundaries in a video using PySceneDetect.

    Args:
        video_path: Path to the video file
        threshold: Threshold for AdaptiveDetector (default 3.0)
        min_scene_len_ms: Minimum scene length in milliseconds (default 2000)

    Returns:
        List of detected scenes as SceneBoundary objects

    Raises:
        RuntimeError: If scenedetect is not installed or video processing fails
    """
    if AdaptiveDetector is None:
        msg = "scenedetect library is not installed. Install with: pip install scenedetect[opencv]"
        logger.error(msg)
        raise RuntimeError(msg)

    try:
        from unrealitytv.models import SceneBoundary

        # Initialize video manager and scene manager
        video_manager = VideoManager([str(video_path)])
        scene_manager = SceneManager()

        # Add AdaptiveDetector with the given threshold
        scene_manager.add_detector(AdaptiveDetector(adaptive_threshold=threshold))

        # Process the video
        base_timecode = video_manager.get_base_timecode()
        video_manager.set_downscale_factor()

        try:
            video_manager.start()
            scene_manager.detect_scenes(frame_source=video_manager)
        finally:
            video_manager.release()

        scenes = scene_manager.get_scene_list(base_timecode)

        # Filter and convert scenes to SceneBoundary objects
        filtered_scenes: list[SceneBoundary] = []
        for index, (start_tc, end_tc) in enumerate(scenes):
            start_ms = int(start_tc.get_seconds() * 1000)
            end_ms = int(end_tc.get_seconds() * 1000)
            scene_duration_ms = end_ms - start_ms

            if scene_duration_ms >= min_scene_len_ms:
                filtered_scenes.append(
                    SceneBoundary(
                        start_ms=start_ms,
                        end_ms=end_ms,
                        scene_index=index,
                    )
                )

        logger.info(f"Detected {len(filtered_scenes)} scenes in {video_path.name}")
        return filtered_scenes

    except ImportError as e:
        msg = f"Failed to import required module: {e}"
        logger.error(msg)
        raise RuntimeError(msg) from e
    except Exception as e:
        msg = f"Error detecting scenes in {video_path}: {e}"
        logger.error(msg)
        raise RuntimeError(msg) from e
