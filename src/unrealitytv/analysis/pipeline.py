"""Analysis pipeline that orchestrates audio extraction, transcription, and pattern matching."""

from __future__ import annotations

import logging
import time
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Optional

from src.unrealitytv.audio.extract import extract_audio, get_duration_ms
from src.unrealitytv.detection.patterns import KeywordMatcher, PatternDetectionError
from src.unrealitytv.models import AnalysisResult, Episode, SkipSegment
from src.unrealitytv.transcription.whisper import (
    TranscriptSegment,
    WhisperError,
    WhisperTranscriber,
)

logger = logging.getLogger(__name__)


class AnalysisPipelineError(Exception):
    """Exception raised when analysis pipeline fails."""

    pass


class AnalysisPipeline:
    """Orchestrates the full analysis pipeline for video episodes.

    Chains together:
    1. Audio extraction from video using FFmpeg
    2. Speech-to-text transcription using Whisper
    3. Recap/preview detection using keyword pattern matching

    Attributes:
        gpu_enabled: Whether to use GPU for Whisper transcription
        recap_keywords: Custom keywords for recap detection
        preview_keywords: Custom keywords for preview detection
        cleanup_temp_files: Whether to delete temporary files after analysis
    """

    def __init__(
        self,
        gpu_enabled: bool = False,
        recap_keywords: Optional[list[str]] = None,
        preview_keywords: Optional[list[str]] = None,
        cleanup_temp_files: bool = True,
    ) -> None:
        """Initialize the analysis pipeline.

        Args:
            gpu_enabled: If True, use GPU for Whisper if available
            recap_keywords: Custom keywords for recap detection (overrides defaults)
            preview_keywords: Custom keywords for preview detection (overrides defaults)
            cleanup_temp_files: If True, delete temporary audio files after analysis
        """
        self.gpu_enabled = gpu_enabled
        self.recap_keywords = recap_keywords
        self.preview_keywords = preview_keywords
        self.cleanup_temp_files = cleanup_temp_files
        self._transcriber: Optional[WhisperTranscriber] = None
        self._matcher: Optional[KeywordMatcher] = None

        logger.debug(
            f"Initialized AnalysisPipeline with gpu_enabled={gpu_enabled}, "
            f"cleanup_temp_files={cleanup_temp_files}"
        )

    def analyze(self, episode: Episode) -> AnalysisResult:
        """Analyze an episode to detect recap and preview segments.

        Performs:
        1. Audio extraction from the video file
        2. Transcription using Whisper
        3. Pattern matching to detect recap/preview segments

        Args:
            episode: Episode object with file_path and metadata

        Returns:
            AnalysisResult containing detected skip segments

        Raises:
            AnalysisPipelineError: If any step of the pipeline fails
        """
        if not episode.file_path.exists():
            msg = f"Episode file does not exist: {episode.file_path}"
            logger.error(msg)
            raise AnalysisPipelineError(msg)

        start_time = time.time()
        temp_dir = TemporaryDirectory()  # type: ignore
        temp_path = Path(temp_dir.name)

        try:
            logger.info(f"Starting analysis pipeline for episode: {episode.show_name}")

            # Step 1: Extract audio
            logger.info("Step 1/3: Extracting audio from video...")
            audio_path = self._extract_audio(episode, temp_path)

            # Update episode duration if not already set
            if episode.duration_ms is None:
                try:
                    episode.duration_ms = get_duration_ms(episode.file_path)
                    logger.debug(f"Detected episode duration: {episode.duration_ms} ms")
                except Exception as e:
                    logger.warning(f"Could not detect episode duration: {e}")

            # Step 2: Transcribe audio
            logger.info("Step 2/3: Transcribing audio...")
            transcript = self._transcribe_audio(audio_path)

            # Step 3: Detect segments
            logger.info("Step 3/3: Detecting recap/preview segments...")
            segments = self._detect_segments(transcript)

            elapsed_time = time.time() - start_time
            logger.info(
                f"Pipeline complete. Found {len(segments)} segments in "
                f"{elapsed_time:.2f} seconds"
            )

            return AnalysisResult(episode=episode, segments=segments)

        except (AnalysisPipelineError, PatternDetectionError, WhisperError) as e:
            msg = f"Pipeline failed during analysis: {e}"
            logger.error(msg)
            raise AnalysisPipelineError(msg) from e
        except Exception as e:
            msg = f"Unexpected error during analysis: {e}"
            logger.error(msg, exc_info=True)
            raise AnalysisPipelineError(msg) from e
        finally:
            if self.cleanup_temp_files:
                try:
                    temp_dir.cleanup()  # type: ignore
                    logger.debug("Cleaned up temporary directory")
                except Exception as e:
                    logger.warning(f"Could not clean up temporary directory: {e}")

    def _extract_audio(self, episode: Episode, temp_dir: Path) -> Path:
        """Extract audio from episode video file.

        Args:
            episode: Episode to extract audio from
            temp_dir: Directory to store extracted audio

        Returns:
            Path to the extracted audio file

        Raises:
            AnalysisPipelineError: If audio extraction fails
        """
        try:
            audio_path = temp_dir / f"{episode.file_path.stem}.wav"
            logger.debug(f"Extracting audio to: {audio_path}")
            extract_audio(episode.file_path, audio_path)
            logger.info(f"Audio extracted successfully: {audio_path}")
            return audio_path
        except FileNotFoundError as e:
            msg = f"Audio extraction failed: {e}"
            logger.error(msg)
            raise AnalysisPipelineError(msg) from e
        except Exception as e:
            msg = f"Audio extraction error: {e}"
            logger.error(msg)
            raise AnalysisPipelineError(msg) from e

    def _transcribe_audio(self, audio_path: Path) -> list[TranscriptSegment]:
        """Transcribe audio file to text segments.

        Args:
            audio_path: Path to audio file

        Returns:
            List of TranscriptSegment objects

        Raises:
            AnalysisPipelineError: If transcription fails
        """
        try:
            if self._transcriber is None:
                self._transcriber = WhisperTranscriber(gpu_enabled=self.gpu_enabled)

            logger.debug(f"Transcribing audio: {audio_path}")
            transcript = self._transcriber.transcribe(audio_path)
            logger.info(f"Transcription complete: {len(transcript)} segments")
            return transcript
        except Exception as e:
            msg = f"Transcription failed: {e}"
            logger.error(msg)
            raise AnalysisPipelineError(msg) from e

    def _detect_segments(
        self, transcript: list[TranscriptSegment]
    ) -> list[SkipSegment]:
        """Detect recap and preview segments from transcript.

        Args:
            transcript: List of transcript segments

        Returns:
            List of detected skip segments

        Raises:
            AnalysisPipelineError: If detection fails
        """
        try:
            if self._matcher is None:
                self._matcher = KeywordMatcher(
                    recap_keywords=self.recap_keywords
                    if self.recap_keywords
                    else [],
                    preview_keywords=self.preview_keywords
                    if self.preview_keywords
                    else [],
                )

            logger.debug(f"Detecting segments from {len(transcript)} transcript items")
            segments = self._matcher.detect_segments(transcript)
            logger.info(f"Detection complete: {len(segments)} segments found")
            return segments
        except Exception as e:
            msg = f"Segment detection failed: {e}"
            logger.error(msg)
            raise AnalysisPipelineError(msg) from e

    def close(self) -> None:
        """Clean up resources (release Whisper model from memory).

        This should be called when the pipeline is no longer needed to free memory.
        """
        if self._transcriber is not None:
            logger.debug("Closing Whisper transcriber")
            self._transcriber.close()
            self._transcriber = None
