"""Whisper transcription wrapper for speech-to-text conversion."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class WhisperError(Exception):
    """Exception raised when Whisper transcription fails."""

    pass


class TranscriptSegment(BaseModel):
    """A segment of transcribed text with timing information.

    Attributes:
        start_time_ms: Start time in milliseconds
        end_time_ms: End time in milliseconds
        text: The transcribed text for this segment
    """

    start_time_ms: int = Field(..., ge=0, description="Start time in milliseconds")
    end_time_ms: int = Field(..., ge=0, description="End time in milliseconds")
    text: str = Field(..., min_length=1, description="Transcribed text")

    @property
    def duration_ms(self) -> int:
        """Get duration of this segment in milliseconds."""
        return self.end_time_ms - self.start_time_ms


class WhisperTranscriber:
    """Wrapper around OpenAI's Whisper model for transcribing audio.

    Handles GPU/CPU device selection, lazy model loading, and error handling
    for Whisper-based speech-to-text transcription.

    Attributes:
        gpu_enabled: Whether to attempt GPU acceleration if available
    """

    def __init__(self, gpu_enabled: bool = False) -> None:
        """Initialize the Whisper transcriber.

        Args:
            gpu_enabled: If True, use GPU (CUDA) if available, otherwise CPU
        """
        self.gpu_enabled = gpu_enabled
        self._model: Optional[object] = None
        logger.info(
            f"Initialized WhisperTranscriber with gpu_enabled={gpu_enabled}"
        )

    @property
    def device(self) -> str:
        """Get the device to use for Whisper (cuda or cpu).

        Returns:
            'cuda' if GPU is enabled and available, otherwise 'cpu'
        """
        try:
            import torch

            if self.gpu_enabled and torch.cuda.is_available():
                logger.info("Using CUDA device for Whisper")
                return "cuda"
        except ImportError:
            logger.warning("PyTorch not available, falling back to CPU")
        except Exception as e:
            logger.warning(f"Error checking CUDA availability: {e}, using CPU")

        logger.info("Using CPU device for Whisper")
        return "cpu"

    def _load_model(self) -> None:
        """Load the Whisper model (lazy loading).

        Raises:
            WhisperError: If model loading fails
        """
        try:
            import whisper

            logger.info(f"Loading Whisper base model on {self.device}")
            self._model = whisper.load_model("base", device=self.device)
            logger.info("Whisper model loaded successfully")
        except ImportError as e:
            msg = (
                "Whisper not installed. Install with: pip install openai-whisper"
            )
            logger.error(msg)
            raise WhisperError(msg) from e
        except Exception as e:
            msg = f"Failed to load Whisper model: {e}"
            logger.error(msg)
            raise WhisperError(msg) from e

    def transcribe(self, audio_path: Path) -> list[TranscriptSegment]:
        """Transcribe an audio file using Whisper.

        Args:
            audio_path: Path to the audio file (WAV format recommended)

        Returns:
            List of TranscriptSegment objects with timing and text

        Raises:
            WhisperError: If transcription fails
            FileNotFoundError: If audio file doesn't exist
        """
        if not audio_path.exists():
            msg = f"Audio file does not exist: {audio_path}"
            logger.error(msg)
            raise FileNotFoundError(msg)

        # Lazy load model on first transcription
        if self._model is None:
            self._load_model()

        try:
            logger.info(f"Transcribing audio from {audio_path}")
            result = self._model.transcribe(str(audio_path))
            logger.info(
                f"Transcription complete: {len(result.get('segments', []))} segments"
            )

            # Convert Whisper segments to our TranscriptSegment format
            segments: list[TranscriptSegment] = []
            for segment in result.get("segments", []):
                # Skip segments with empty or very short text
                text = segment.get("text", "").strip()
                if not text:
                    continue

                try:
                    ts = TranscriptSegment(
                        start_time_ms=int(segment["start"] * 1000),
                        end_time_ms=int(segment["end"] * 1000),
                        text=text,
                    )
                    segments.append(ts)
                except (ValueError, KeyError) as e:
                    logger.warning(
                        f"Skipping malformed segment: {segment}, error: {e}"
                    )
                    continue

            if not segments:
                logger.warning("Transcription resulted in no valid segments")
                return []

            logger.info(f"Successfully extracted {len(segments)} transcript segments")
            return segments

        except Exception as e:
            msg = f"Transcription failed: {e}"
            logger.error(msg)
            raise WhisperError(msg) from e

    def close(self) -> None:
        """Clean up resources (release model from memory).

        This can be called to free memory when the transcriber is no longer needed.
        """
        if self._model is not None:
            logger.info("Closing Whisper transcriber and releasing model")
            self._model = None
