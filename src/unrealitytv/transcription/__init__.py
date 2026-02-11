"""Transcription module for converting audio to text."""

from .whisper import TranscriptSegment, WhisperError, WhisperTranscriber

__all__ = ["WhisperTranscriber", "TranscriptSegment", "WhisperError"]
