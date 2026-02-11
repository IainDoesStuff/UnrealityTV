"""Audio extraction module for converting video files to WAV format."""

from __future__ import annotations

import logging
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)


class AudioExtractionError(Exception):
    """Exception raised when audio extraction fails."""

    pass


def extract_audio(input_path: Path, output_path: Path) -> None:
    """Extract audio from a video file and convert to mono WAV at 16kHz.

    This function uses FFmpeg to extract audio from a video file and converts it
    to mono WAV format at 16kHz sample rate, which is the format expected by
    Whisper for transcription.

    Args:
        input_path: Path to the input video file
        output_path: Path where the extracted audio WAV file will be saved

    Raises:
        AudioExtractionError: If FFmpeg is not installed, the input file is invalid,
                             or extraction fails for any reason
    """
    if not input_path.exists():
        msg = f"Input file does not exist: {input_path}"
        logger.error(msg)
        raise AudioExtractionError(msg)

    # Ensure output directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        logger.info(f"Extracting audio from {input_path} to {output_path}")
        subprocess.run(
            [
                "ffmpeg",
                "-i",
                str(input_path),
                "-vn",  # Disable video processing
                "-acodec",
                "pcm_s16le",  # PCM 16-bit little-endian
                "-ar",
                "16000",  # 16kHz sample rate
                "-ac",
                "1",  # Mono audio
                "-y",  # Overwrite output file without asking
                str(output_path),
            ],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        logger.info(f"Successfully extracted audio to {output_path}")
    except FileNotFoundError as e:
        msg = "FFmpeg not installed. Install with: apt-get install ffmpeg (Linux) or brew install ffmpeg (macOS)"
        logger.error(msg)
        raise AudioExtractionError(msg) from e
    except subprocess.CalledProcessError as e:
        stderr = e.stderr.decode("utf-8") if e.stderr else "Unknown error"
        msg = f"FFmpeg failed to extract audio: {stderr}"
        logger.error(msg)
        raise AudioExtractionError(msg) from e


def get_duration_ms(file_path: Path) -> int:
    """Get the duration of an audio or video file in milliseconds.

    Uses FFprobe (part of FFmpeg) to quickly query file metadata without
    processing the entire file.

    Args:
        file_path: Path to the audio or video file

    Returns:
        Duration in milliseconds as an integer

    Raises:
        AudioExtractionError: If FFprobe is not installed or the file is invalid
    """
    if not file_path.exists():
        msg = f"File does not exist: {file_path}"
        logger.error(msg)
        raise AudioExtractionError(msg)

    try:
        logger.info(f"Getting duration of {file_path}")
        result = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                str(file_path),
            ],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=10,
        )
        duration_str = result.stdout.decode("utf-8").strip()
        duration_ms = int(float(duration_str) * 1000)
        logger.info(f"Duration: {duration_ms}ms ({duration_ms / 1000:.1f}s)")
        return duration_ms
    except FileNotFoundError as e:
        msg = "FFprobe not installed. Install with: apt-get install ffmpeg (Linux) or brew install ffmpeg (macOS)"
        logger.error(msg)
        raise AudioExtractionError(msg) from e
    except subprocess.CalledProcessError as e:
        stderr = e.stderr.decode("utf-8") if e.stderr else "Unknown error"
        msg = f"FFprobe failed: {stderr}"
        logger.error(msg)
        raise AudioExtractionError(msg) from e
    except (ValueError, subprocess.TimeoutExpired) as e:
        msg = f"Failed to parse duration from file: {file_path}"
        logger.error(msg)
        raise AudioExtractionError(msg) from e
