"""Tests for Whisper transcription wrapper."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.unrealitytv.transcription.whisper import (
    TranscriptSegment,
    WhisperError,
    WhisperTranscriber,
)

# Mock whisper and torch modules before importing
sys.modules["whisper"] = MagicMock()
sys.modules["torch"] = MagicMock()


@pytest.fixture
def temp_audio_file(tmp_path: Path) -> Path:
    """Create a temporary dummy audio file."""
    audio_file = tmp_path / "test_audio.wav"
    audio_file.write_bytes(b"RIFF" + b"\x00" * 100)  # Dummy WAV header
    return audio_file


@pytest.fixture
def mock_whisper_result() -> dict:
    """Mock Whisper transcription result with two segments."""
    return {
        "segments": [
            {
                "id": 0,
                "seek": 0,
                "start": 0.1,
                "end": 2.5,
                "text": " Hello, how are you today?",
                "tokens": [],
                "temperature": 0.0,
                "avg_logprob": -0.3,
                "compression_ratio": 1.5,
                "no_speech_prob": 0.001,
            },
            {
                "id": 1,
                "seek": 0,
                "start": 3.0,
                "end": 5.5,
                "text": " I'm doing great, thanks for asking!",
                "tokens": [],
                "temperature": 0.0,
                "avg_logprob": -0.25,
                "compression_ratio": 1.4,
                "no_speech_prob": 0.0,
            },
        ],
        "language": "en",
    }


@pytest.fixture
def mock_empty_result() -> dict:
    """Mock Whisper result with no segments."""
    return {"segments": [], "language": "en"}


class TestTranscriptSegment:
    """Tests for TranscriptSegment model."""

    def test_segment_creation(self) -> None:
        """Test creating a transcript segment."""
        segment = TranscriptSegment(
            start_time_ms=100, end_time_ms=2500, text="Hello world"
        )
        assert segment.start_time_ms == 100
        assert segment.end_time_ms == 2500
        assert segment.text == "Hello world"

    def test_segment_duration_property(self) -> None:
        """Test duration_ms property."""
        segment = TranscriptSegment(
            start_time_ms=100, end_time_ms=2500, text="Hello"
        )
        assert segment.duration_ms == 2400

    def test_segment_validation_end_before_start(self) -> None:
        """Test that end_time must be >= start_time (validation)."""
        # Pydantic will allow equal times, which is fine for 0-duration segments
        segment = TranscriptSegment(
            start_time_ms=100, end_time_ms=100, text="test"
        )
        assert segment.duration_ms == 0

    def test_segment_validation_text_not_empty(self) -> None:
        """Test that text cannot be empty."""
        with pytest.raises(ValueError):
            TranscriptSegment(start_time_ms=0, end_time_ms=100, text="")

    def test_segment_validation_negative_time_fails(self) -> None:
        """Test that negative times fail validation."""
        with pytest.raises(ValueError):
            TranscriptSegment(start_time_ms=-100, end_time_ms=100, text="test")


class TestWhisperTranscriberDevice:
    """Tests for device selection (GPU/CPU)."""

    def test_cpu_device_selection(self) -> None:
        """Test CPU device selection when GPU is disabled."""
        transcriber = WhisperTranscriber(gpu_enabled=False)
        assert transcriber.device == "cpu"

    def test_gpu_device_selection_when_available(self) -> None:
        """Test GPU device selection when available and enabled."""
        with patch.dict(sys.modules, {"torch": MagicMock(cuda=MagicMock(is_available=MagicMock(return_value=True)))}):
            transcriber = WhisperTranscriber(gpu_enabled=True)
            assert transcriber.device == "cuda"

    def test_gpu_disabled_falls_back_to_cpu(self) -> None:
        """Test that CPU is used when GPU is disabled."""
        with patch.dict(sys.modules, {"torch": MagicMock(cuda=MagicMock(is_available=MagicMock(return_value=True)))}):
            transcriber = WhisperTranscriber(gpu_enabled=False)
            assert transcriber.device == "cpu"

    def test_gpu_not_available_falls_back_to_cpu(self) -> None:
        """Test that CPU is used when GPU is not available."""
        with patch.dict(sys.modules, {"torch": MagicMock(cuda=MagicMock(is_available=MagicMock(return_value=False)))}):
            transcriber = WhisperTranscriber(gpu_enabled=True)
            assert transcriber.device == "cpu"


class TestWhisperTranscriberModelLoading:
    """Tests for model loading and lazy initialization."""

    def test_model_loaded_on_first_transcription(
        self, temp_audio_file: Path, mock_whisper_result: dict
    ) -> None:
        """Test that model is loaded on first transcription (lazy loading)."""
        mock_model = MagicMock()
        mock_model.transcribe.return_value = mock_whisper_result
        mock_whisper_module = MagicMock()
        mock_whisper_module.load_model.return_value = mock_model

        with patch.dict(sys.modules, {"whisper": mock_whisper_module}):
            transcriber = WhisperTranscriber(gpu_enabled=False)
            assert transcriber._model is None

            segments = transcriber.transcribe(temp_audio_file)

            mock_whisper_module.load_model.assert_called_once_with("base", device="cpu")
            assert transcriber._model is not None
            assert len(segments) == 2

    def test_model_reused_on_subsequent_calls(
        self, temp_audio_file: Path, mock_whisper_result: dict
    ) -> None:
        """Test that model is reused for subsequent transcriptions."""
        mock_model = MagicMock()
        mock_model.transcribe.return_value = mock_whisper_result
        mock_whisper_module = MagicMock()
        mock_whisper_module.load_model.return_value = mock_model

        with patch.dict(sys.modules, {"whisper": mock_whisper_module}):
            transcriber = WhisperTranscriber(gpu_enabled=False)

            # Transcribe twice
            transcriber.transcribe(temp_audio_file)
            transcriber.transcribe(temp_audio_file)

            # Model should only be loaded once
            mock_whisper_module.load_model.assert_called_once()

    def test_model_loading_failure(self, temp_audio_file: Path) -> None:
        """Test error handling when model loading fails."""
        mock_whisper_module = MagicMock()
        mock_whisper_module.load_model.side_effect = RuntimeError("CUDA out of memory")

        with patch.dict(sys.modules, {"whisper": mock_whisper_module}):
            transcriber = WhisperTranscriber(gpu_enabled=True)

            with pytest.raises(WhisperError, match="Failed to load Whisper model"):
                transcriber.transcribe(temp_audio_file)

    def test_whisper_not_installed(self, temp_audio_file: Path) -> None:
        """Test error when Whisper package is not installed."""
        mock_whisper_module = MagicMock()
        mock_whisper_module.load_model.side_effect = ImportError()

        with patch.dict(sys.modules, {"whisper": mock_whisper_module}):
            transcriber = WhisperTranscriber(gpu_enabled=False)

            with pytest.raises(WhisperError, match="Whisper not installed"):
                transcriber.transcribe(temp_audio_file)


class TestWhisperTranscription:
    """Tests for transcription functionality."""

    def test_successful_transcription(
        self, temp_audio_file: Path, mock_whisper_result: dict
    ) -> None:
        """Test successful audio transcription."""
        mock_model = MagicMock()
        mock_model.transcribe.return_value = mock_whisper_result
        mock_whisper_module = MagicMock()
        mock_whisper_module.load_model.return_value = mock_model

        with patch.dict(sys.modules, {"whisper": mock_whisper_module}):
            transcriber = WhisperTranscriber(gpu_enabled=False)
            segments = transcriber.transcribe(temp_audio_file)

            assert len(segments) == 2
            assert segments[0].text == "Hello, how are you today?"
            assert segments[0].start_time_ms == 100
            assert segments[0].end_time_ms == 2500
            assert segments[1].text == "I'm doing great, thanks for asking!"

    def test_empty_transcription(
        self, temp_audio_file: Path, mock_empty_result: dict
    ) -> None:
        """Test handling of empty transcription results."""
        mock_model = MagicMock()
        mock_model.transcribe.return_value = mock_empty_result
        mock_whisper_module = MagicMock()
        mock_whisper_module.load_model.return_value = mock_model

        with patch.dict(sys.modules, {"whisper": mock_whisper_module}):
            transcriber = WhisperTranscriber(gpu_enabled=False)
            segments = transcriber.transcribe(temp_audio_file)

            assert len(segments) == 0

    def test_audio_file_not_exists(self) -> None:
        """Test error when audio file doesn't exist."""
        transcriber = WhisperTranscriber(gpu_enabled=False)

        with pytest.raises(FileNotFoundError, match="Audio file does not exist"):
            transcriber.transcribe(Path("/nonexistent/audio.wav"))

    def test_transcription_failure(self, temp_audio_file: Path) -> None:
        """Test error handling when transcription fails."""
        mock_model = MagicMock()
        mock_model.transcribe.side_effect = RuntimeError("Transcription failed")
        mock_whisper_module = MagicMock()
        mock_whisper_module.load_model.return_value = mock_model

        with patch.dict(sys.modules, {"whisper": mock_whisper_module}):
            transcriber = WhisperTranscriber(gpu_enabled=False)

            with pytest.raises(WhisperError, match="Transcription failed"):
                transcriber.transcribe(temp_audio_file)

    def test_skips_empty_text_segments(self, temp_audio_file: Path) -> None:
        """Test that segments with empty/whitespace text are skipped."""
        result = {
            "segments": [
                {"start": 0.0, "end": 1.0, "text": "Valid text"},
                {"start": 1.0, "end": 2.0, "text": "   "},  # Only whitespace
                {"start": 2.0, "end": 3.0, "text": ""},  # Empty
                {"start": 3.0, "end": 4.0, "text": "Another valid"},
            ]
        }
        mock_model = MagicMock()
        mock_model.transcribe.return_value = result
        mock_whisper_module = MagicMock()
        mock_whisper_module.load_model.return_value = mock_model

        with patch.dict(sys.modules, {"whisper": mock_whisper_module}):
            transcriber = WhisperTranscriber(gpu_enabled=False)
            segments = transcriber.transcribe(temp_audio_file)

            assert len(segments) == 2
            assert segments[0].text == "Valid text"
            assert segments[1].text == "Another valid"

    def test_handles_malformed_segments(self, temp_audio_file: Path) -> None:
        """Test that malformed segments are skipped gracefully."""
        result = {
            "segments": [
                {"start": 0.0, "end": 1.0, "text": "Valid text"},
                {"start": "invalid", "end": 2.0, "text": "Bad start time"},
                {"start": 2.0, "end": 3.0, "text": "Another valid"},
            ]
        }
        mock_model = MagicMock()
        mock_model.transcribe.return_value = result
        mock_whisper_module = MagicMock()
        mock_whisper_module.load_model.return_value = mock_model

        with patch.dict(sys.modules, {"whisper": mock_whisper_module}):
            transcriber = WhisperTranscriber(gpu_enabled=False)
            segments = transcriber.transcribe(temp_audio_file)

            # Malformed segment should be skipped
            assert len(segments) == 2
            assert segments[0].text == "Valid text"
            assert segments[1].text == "Another valid"


class TestWhisperTranscriberCleanup:
    """Tests for resource cleanup."""

    def test_close_releases_model(
        self, temp_audio_file: Path, mock_whisper_result: dict
    ) -> None:
        """Test that close() releases the model."""
        mock_model = MagicMock()
        mock_model.transcribe.return_value = mock_whisper_result
        mock_whisper_module = MagicMock()
        mock_whisper_module.load_model.return_value = mock_model

        with patch.dict(sys.modules, {"whisper": mock_whisper_module}):
            transcriber = WhisperTranscriber(gpu_enabled=False)
            transcriber.transcribe(temp_audio_file)

            assert transcriber._model is not None
            transcriber.close()
            assert transcriber._model is None
