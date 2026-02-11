"""Audio processing module for UnrealityTV."""

from .extract import AudioExtractionError, extract_audio, get_duration_ms

__all__ = ["extract_audio", "get_duration_ms", "AudioExtractionError"]
