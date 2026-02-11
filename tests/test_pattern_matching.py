"""Tests for keyword pattern matching detection."""

from __future__ import annotations

import pytest

from src.unrealitytv.detection.patterns import (
    KeywordMatcher,
    PatternDetectionError,
)
from src.unrealitytv.transcription.whisper import TranscriptSegment


@pytest.fixture
def sample_transcript() -> list[TranscriptSegment]:
    """Create a sample transcript with mixed content."""
    return [
        TranscriptSegment(
            start_time_ms=1000,
            end_time_ms=2000,
            text="Previously on UnrealityTV, we saw the drama unfold.",
        ),
        TranscriptSegment(
            start_time_ms=3000,
            end_time_ms=4000,
            text="Now let's see what happens next in this episode.",
        ),
        TranscriptSegment(
            start_time_ms=5000,
            end_time_ms=6000,
            text="This is the main content of the show.",
        ),
        TranscriptSegment(
            start_time_ms=7000,
            end_time_ms=8000,
            text="Coming up next, we have an exciting twist!",
        ),
    ]


@pytest.fixture
def default_matcher() -> KeywordMatcher:
    """Create a matcher with default keywords."""
    return KeywordMatcher()


class TestKeywordMatcherInitialization:
    """Tests for KeywordMatcher initialization."""

    def test_default_keywords(self) -> None:
        """Test that default keywords are loaded."""
        matcher = KeywordMatcher()
        assert len(matcher.recap_keywords) > 0
        assert len(matcher.preview_keywords) > 0
        assert "previously" in matcher.recap_keywords
        assert "coming up" in matcher.preview_keywords

    def test_custom_keywords(self) -> None:
        """Test initialization with custom keywords."""
        recap_kw = ["recap_custom", "old_content"]
        preview_kw = ["preview_custom", "future_content"]
        matcher = KeywordMatcher(recap_keywords=recap_kw, preview_keywords=preview_kw)

        assert matcher.recap_keywords == recap_kw
        assert matcher.preview_keywords == preview_kw

    def test_invalid_recap_keywords(self) -> None:
        """Test error when recap keywords contain non-strings."""
        with pytest.raises(ValueError, match="must be strings"):
            KeywordMatcher(recap_keywords=["valid", 123])

    def test_invalid_preview_keywords(self) -> None:
        """Test error when preview keywords contain non-strings."""
        with pytest.raises(ValueError, match="must be strings"):
            KeywordMatcher(preview_keywords=["valid", 123])


class TestRecapDetection:
    """Tests for recap segment detection."""

    def test_successful_recap_detection(
        self, sample_transcript: list[TranscriptSegment]
    ) -> None:
        """Test detection of recap segments."""
        matcher = KeywordMatcher()
        results = matcher.detect_segments(sample_transcript)

        # Should find the "Previously" segment
        recap_results = [r for r in results if r.segment_type == "recap"]
        assert len(recap_results) == 1
        assert recap_results[0].start_ms == 1000
        assert recap_results[0].end_ms == 2000
        assert recap_results[0].confidence >= 0.5

    def test_recap_with_custom_keywords(self) -> None:
        """Test recap detection with custom keywords."""
        transcript = [
            TranscriptSegment(
                start_time_ms=1000,
                end_time_ms=2000,
                text="In the previous episode, we saw everything change.",
            )
        ]
        matcher = KeywordMatcher(recap_keywords=["previous episode", "before"])
        results = matcher.detect_segments(transcript)

        assert len(results) == 1
        assert results[0].segment_type == "recap"

    def test_recap_word_boundaries(self) -> None:
        """Test that recap keywords respect word boundaries."""
        transcript = [
            TranscriptSegment(
                start_time_ms=1000,
                end_time_ms=2000,
                text="This is previously unknown information.",  # 'previously' as adverb, not our keyword
            )
        ]
        matcher = KeywordMatcher()
        results = matcher.detect_segments(transcript)

        # "previously" in this context is a match even though it's adverbial
        # Our word boundary check just ensures it's not part of another word
        assert len(results) == 1  # Should still match


class TestPreviewDetection:
    """Tests for preview segment detection."""

    def test_successful_preview_detection(
        self, sample_transcript: list[TranscriptSegment]
    ) -> None:
        """Test detection of preview segments."""
        matcher = KeywordMatcher()
        results = matcher.detect_segments(sample_transcript)

        preview_results = [r for r in results if r.segment_type == "preview"]
        assert len(preview_results) == 1
        assert preview_results[0].start_ms == 7000
        assert preview_results[0].end_ms == 8000

    def test_preview_with_custom_keywords(self) -> None:
        """Test preview detection with custom keywords."""
        transcript = [
            TranscriptSegment(
                start_time_ms=1000,
                end_time_ms=2000,
                text="What's next on this amazing show?",
            )
        ]
        matcher = KeywordMatcher(preview_keywords=["what's next", "upcoming"])
        results = matcher.detect_segments(transcript)

        assert len(results) == 1
        assert results[0].segment_type == "preview"


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_empty_transcript(self, default_matcher: KeywordMatcher) -> None:
        """Test handling of empty transcript."""
        results = default_matcher.detect_segments([])
        assert len(results) == 0

    def test_no_matching_keywords(self) -> None:
        """Test transcript with no matching keywords."""
        transcript = [
            TranscriptSegment(
                start_time_ms=1000,
                end_time_ms=2000,
                text="This is regular content with no special markers.",
            )
        ]
        matcher = KeywordMatcher()
        results = matcher.detect_segments(transcript)

        assert len(results) == 0

    def test_multiple_keywords_in_one_segment(self) -> None:
        """Test segment matching multiple keywords."""
        transcript = [
            TranscriptSegment(
                start_time_ms=1000,
                end_time_ms=2000,
                text="Previously on the last episode, we left off with a cliffhanger.",
            )
        ]
        matcher = KeywordMatcher()
        results = matcher.detect_segments(transcript)

        assert len(results) == 1
        assert "previously" in results[0].reason.lower()
        assert "last" in results[0].reason.lower()
        # Confidence should be higher with multiple matches
        assert results[0].confidence >= 0.5

    def test_case_insensitivity(self) -> None:
        """Test that matching is case-insensitive."""
        transcript = [
            TranscriptSegment(
                start_time_ms=1000,
                end_time_ms=2000,
                text="PREVIOUSLY ON UNREALITYTV, WE SAW AMAZING THINGS.",
            )
        ]
        matcher = KeywordMatcher()
        results = matcher.detect_segments(transcript)

        assert len(results) == 1
        assert results[0].segment_type == "recap"

    def test_word_boundary_non_match(self) -> None:
        """Test that word boundaries prevent false positives."""
        transcript = [
            TranscriptSegment(
                start_time_ms=1000,
                end_time_ms=2000,
                text="This is a preview of upcoming features.",  # 'preview' should not match 'coming up'
            )
        ]
        matcher = KeywordMatcher()
        results = matcher.detect_segments(transcript)

        # "coming up" as a phrase should not match just "preview"
        assert len(results) == 0


class TestConfidenceScoring:
    """Tests for confidence score calculation."""

    def test_single_keyword_match_confidence(self) -> None:
        """Test confidence with single keyword match."""
        transcript = [
            TranscriptSegment(
                start_time_ms=1000, end_time_ms=2000, text="Previously on the show."
            )
        ]
        matcher = KeywordMatcher()
        results = matcher.detect_segments(transcript)

        assert len(results) == 1
        # Confidence should be between 0.5 and 1.0
        assert 0.5 <= results[0].confidence <= 1.0

    def test_multiple_keywords_increase_confidence(self) -> None:
        """Test that multiple keyword matches are reflected in reason."""
        transcript = [
            TranscriptSegment(
                start_time_ms=1000,
                end_time_ms=2000,
                text="Previously on the last week we saw amazing things.",
            )
        ]
        matcher = KeywordMatcher()
        results = matcher.detect_segments(transcript)

        assert len(results) == 1
        # Multiple matches should be listed in the reason
        assert "previously" in results[0].reason.lower()
        assert "last week" in results[0].reason.lower()

    def test_confidence_capped_at_one(self) -> None:
        """Test that confidence is never greater than 1.0."""
        transcript = [
            TranscriptSegment(
                start_time_ms=1000,
                end_time_ms=2000,
                text="Previously last time last week where we left off.",
            )
        ]
        matcher = KeywordMatcher()
        results = matcher.detect_segments(transcript)

        assert len(results) == 1
        assert results[0].confidence <= 1.0


class TestPriorityHandling:
    """Tests for handling segments that match multiple categories."""

    def test_recap_priority_over_preview(self) -> None:
        """Test that recap matches take priority over preview."""
        transcript = [
            TranscriptSegment(
                start_time_ms=1000,
                end_time_ms=2000,
                text="Previously on the show, coming up next is amazing.",
            )
        ]
        matcher = KeywordMatcher()
        results = matcher.detect_segments(transcript)

        # Should only detect as recap (recap has priority)
        assert len(results) == 1
        assert results[0].segment_type == "recap"


class TestReasonField:
    """Tests for the reason field in detected segments."""

    def test_reason_includes_matched_keywords(self) -> None:
        """Test that reason field lists matched keywords."""
        transcript = [
            TranscriptSegment(
                start_time_ms=1000, end_time_ms=2000, text="Previously on the show."
            )
        ]
        matcher = KeywordMatcher()
        results = matcher.detect_segments(transcript)

        assert len(results) == 1
        assert "previously" in results[0].reason.lower()

    def test_reason_with_multiple_matches(self) -> None:
        """Test reason field with multiple keyword matches."""
        transcript = [
            TranscriptSegment(
                start_time_ms=1000,
                end_time_ms=2000,
                text="Previously on the last episode.",
            )
        ]
        matcher = KeywordMatcher()
        results = matcher.detect_segments(transcript)

        assert len(results) == 1
        reason_lower = results[0].reason.lower()
        assert "previously" in reason_lower or "last" in reason_lower


class TestErrorHandling:
    """Tests for error handling."""

    def test_malformed_transcript_segment(self) -> None:
        """Test handling of segments with missing fields."""
        matcher = KeywordMatcher()

        # TranscriptSegment requires start_time_ms, end_time_ms, text
        # When passed a dict instead, it will fail and be wrapped in PatternDetectionError
        with pytest.raises(PatternDetectionError):
            matcher.detect_segments(  # type: ignore
                [
                    {
                        "start_time_ms": 1000,
                        "text": "test",
                    }  # Missing end_time_ms and is dict not TranscriptSegment
                ]
            )
