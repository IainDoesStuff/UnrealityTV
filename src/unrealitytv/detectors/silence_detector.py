"""Silence detection using audio analysis."""

from __future__ import annotations

import logging
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from unrealitytv.models import SceneBoundary

logger = logging.getLogger(__name__)


def detect_silence(
    video_path: Path,
    threshold_db: float = -60,
    min_duration_ms: int = 500,
    silence_type: str = "both",
) -> list[SceneBoundary]:
    """Detect silent segments in a video using audio analysis.

    Args:
        video_path: Path to the video file
        threshold_db: Decibel threshold for silence detection (default -60dB)
        min_duration_ms: Minimum silence duration in milliseconds (default 500ms)
        silence_type: Type of silence to detect:
            - "both": Detect silence across all channels
            - "mono": Treat as mono (average channels)
            - "stereo": Detect silence in all channels
            (default "both")

    Returns:
        List of detected silence segments as SceneBoundary objects

    Raises:
        RuntimeError: If librosa is not installed or audio processing fails
        FileNotFoundError: If video file does not exist
    """
    if not video_path.exists():
        msg = f"Video file does not exist: {video_path}"
        logger.error(msg)
        raise FileNotFoundError(msg)

    try:
        import librosa
        import numpy as np
    except ImportError as e:
        msg = "librosa is not installed. Install with: pip install librosa"
        logger.error(msg)
        raise RuntimeError(msg) from e

    try:
        from unrealitytv.models import SceneBoundary

        logger.info(
            f"Detecting silence in {video_path.name} "
            f"(threshold: {threshold_db}dB, min_duration: {min_duration_ms}ms)"
        )

        # Extract audio to temporary file
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_file:
            tmp_audio_path = Path(tmp_file.name)

        try:
            from unrealitytv.audio.extract import extract_audio

            extract_audio(video_path, tmp_audio_path)

            # Load audio
            y, sr = librosa.load(str(tmp_audio_path), sr=None)

            # Convert to decibels (RMS energy per frame)
            s = librosa.feature.melspectrogram(y=y, sr=sr)
            db = librosa.power_to_db(s, ref=np.max)

            # Take mean across frequency bins
            db_mean = np.mean(db, axis=0)

            # Find frames below threshold
            is_silent = db_mean < threshold_db

            # Convert frames to time
            times = librosa.frames_to_time(np.arange(len(is_silent)), sr=sr)
            times_ms = times * 1000

            # Find contiguous silent regions
            silent_segments: list[SceneBoundary] = []
            in_silence = False
            start_ms = 0.0

            for idx, (time_ms, silent) in enumerate(zip(times_ms, is_silent)):
                if not in_silence and silent:
                    # Start of silence
                    in_silence = True
                    start_ms = time_ms
                elif in_silence and not silent:
                    # End of silence
                    end_ms = time_ms
                    duration_ms = end_ms - start_ms

                    if duration_ms >= min_duration_ms:
                        silent_segments.append(
                            SceneBoundary(
                                start_ms=int(start_ms),
                                end_ms=int(end_ms),
                                scene_index=len(silent_segments),
                            )
                        )
                    in_silence = False

            # Handle silence at end of file
            if in_silence:
                end_ms = times_ms[-1] if len(times_ms) > 0 else start_ms
                duration_ms = end_ms - start_ms
                if duration_ms >= min_duration_ms:
                    silent_segments.append(
                        SceneBoundary(
                            start_ms=int(start_ms),
                            end_ms=int(end_ms),
                            scene_index=len(silent_segments),
                        )
                    )

            logger.info(
                f"Detected {len(silent_segments)} silence segments in {video_path.name}"
            )
            return silent_segments

        finally:
            # Cleanup temporary audio file
            if tmp_audio_path.exists():
                tmp_audio_path.unlink()

    except ImportError as e:
        msg = f"Failed to import required module: {e}"
        logger.error(msg)
        raise RuntimeError(msg) from e
    except FileNotFoundError as e:
        msg = f"Audio extraction failed: {e}"
        logger.error(msg)
        raise RuntimeError(msg) from e
    except Exception as e:
        msg = f"Error detecting silence in {video_path}: {e}"
        logger.error(msg)
        raise RuntimeError(msg) from e
