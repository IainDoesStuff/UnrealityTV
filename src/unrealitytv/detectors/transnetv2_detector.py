"""Scene boundary detection using TransNetV2 with GPU acceleration."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from unrealitytv.models import SceneBoundary

try:
    import torch
    from transnetv2 import TransNetV2
except ImportError:
    # Will be caught and handled in the function
    torch = None  # type: ignore
    TransNetV2 = None  # type: ignore

try:
    import cv2
except ImportError:
    # Will be caught and handled in the function
    cv2 = None  # type: ignore

logger = logging.getLogger(__name__)


def detect_scenes_gpu(
    video_path: Path,
    gpu_device: int = 0,
    threshold: float = 0.5,
    min_scene_len_ms: int = 2000,
) -> list[SceneBoundary]:
    """Detect scene boundaries in a video using TransNetV2 with GPU acceleration.

    Args:
        video_path: Path to the video file
        gpu_device: GPU device index to use (default 0)
        threshold: Confidence threshold for scene detection (default 0.5)
        min_scene_len_ms: Minimum scene length in milliseconds (default 2000)

    Returns:
        List of detected scenes as SceneBoundary objects

    Raises:
        RuntimeError: If transnetv2 is not installed or video processing fails
    """
    if TransNetV2 is None:
        msg = "transnetv2 library is not installed. Install with: pip install transnetv2"
        logger.error(msg)
        raise RuntimeError(msg)

    try:
        from unrealitytv.models import SceneBoundary

        if cv2 is None:
            msg = "opencv-python library is not installed. Install with: pip install opencv-python"
            logger.error(msg)
            raise RuntimeError(msg)

        # Determine device
        if torch.cuda.is_available():
            device = torch.device(f"cuda:{gpu_device}")
        else:
            device = torch.device("cpu")
            logger.warning(f"GPU device {gpu_device} not available, using CPU")

        # Load model
        model = TransNetV2()
        model = model.to(device)
        model.eval()

        logger.info(
            f"Processing video {video_path.name} on device {device} "
            f"with threshold {threshold}"
        )

        # Open video
        cap = cv2.VideoCapture(str(video_path))
        if not cap.isOpened():
            msg = f"Failed to open video file: {video_path}"
            logger.error(msg)
            raise RuntimeError(msg)

        try:
            fps = cap.get(cv2.CAP_PROP_FPS)
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

            # Process frames with TransNetV2
            frame_scores = []
            frame_count = 0

            while True:
                ret, frame = cap.read()
                if not ret:
                    break

                # Prepare frame for model
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                frame_tensor = (
                    torch.from_numpy(frame_rgb)
                    .float()
                    .unsqueeze(0)
                    .to(device)
                    / 255.0
                )

                # Get prediction
                with torch.no_grad():
                    predictions = model(frame_tensor)
                score = predictions[0, 0].item()
                frame_scores.append(score)
                frame_count += 1

            # Detect scene boundaries based on scores
            filtered_scenes: list[SceneBoundary] = []
            scene_index = 0

            for i in range(len(frame_scores) - 1):
                # Scene boundary detected if score exceeds threshold
                if frame_scores[i] < threshold <= frame_scores[i + 1]:
                    # Start of a new scene
                    start_frame = i
                    start_ms = int((start_frame / fps) * 1000) if fps > 0 else 0

                    # Find end of scene
                    end_frame = i + 1
                    for j in range(i + 1, len(frame_scores)):
                        if frame_scores[j] < threshold:
                            end_frame = j
                            break
                    else:
                        end_frame = len(frame_scores) - 1

                    end_ms = int((end_frame / fps) * 1000) if fps > 0 else 0
                    scene_duration_ms = end_ms - start_ms

                    if scene_duration_ms >= min_scene_len_ms:
                        filtered_scenes.append(
                            SceneBoundary(
                                start_ms=start_ms,
                                end_ms=end_ms,
                                scene_index=scene_index,
                            )
                        )
                        scene_index += 1

            logger.info(
                f"Detected {len(filtered_scenes)} scenes in {video_path.name} "
                f"({total_frames} frames)"
            )
            return filtered_scenes

        finally:
            cap.release()

    except ImportError as e:
        msg = f"Failed to import required module: {e}"
        logger.error(msg)
        raise RuntimeError(msg) from e
    except Exception as e:
        msg = f"Error detecting scenes in {video_path}: {e}"
        logger.error(msg)
        raise RuntimeError(msg) from e
