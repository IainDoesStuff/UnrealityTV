"""Keyword pattern matching for detecting recap and preview segments."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field

from unrealitytv.models import SkipSegment
from unrealitytv.transcription.whisper import TranscriptSegment

logger = logging.getLogger(__name__)


class PatternDetectionError(Exception):
    """Exception raised when pattern detection fails."""

    pass


@dataclass
class KeywordMatcher:
    """Detect recap and preview segments using keyword matching.

    Matches configurable keyword lists against transcript segments with
    word boundary handling, case-insensitivity, and confidence scoring.
    """

    recap_keywords: list[str] = field(
        default_factory=lambda: [
            "previously",
            "last time",
            "last week",
            "where we left off",
            "on the last episode",
        ]
    )
    preview_keywords: list[str] = field(
        default_factory=lambda: [
            "coming up",
            "next time",
            "next episode",
            "what's next",
            "up next",
        ]
    )

    def __post_init__(self) -> None:
        """Validate keyword lists."""
        if not all(isinstance(k, str) for k in self.recap_keywords):
            raise ValueError("All recap_keywords must be strings")
        if not all(isinstance(k, str) for k in self.preview_keywords):
            raise ValueError("All preview_keywords must be strings")

        logger.debug(
            f"Initialized KeywordMatcher with {len(self.recap_keywords)} recap "
            f"and {len(self.preview_keywords)} preview keywords"
        )

    def detect_segments(
        self, transcript: list[TranscriptSegment]
    ) -> list[SkipSegment]:
        """Detect recap and preview segments from a transcript.

        Args:
            transcript: List of TranscriptSegment objects with text and timing

        Returns:
            List of SkipSegment objects for detected recaps/previews

        Raises:
            PatternDetectionError: If detection fails
        """
        if not transcript:
            logger.debug("Empty transcript provided")
            return []

        try:
            matched_segments: list[SkipSegment] = []

            for segment in transcript:
                recap_match = self._match_keywords(
                    segment.text, self.recap_keywords
                )
                preview_match = self._match_keywords(
                    segment.text, self.preview_keywords
                )

                # Prioritize recap over preview if both match
                if recap_match:
                    confidence = recap_match["confidence"]
                    reason = f"Detected: {', '.join(recap_match['matched'])}"
                    skip_segment = SkipSegment(
                        start_ms=segment.start_time_ms,
                        end_ms=segment.end_time_ms,
                        segment_type="recap",
                        confidence=confidence,
                        reason=reason,
                    )
                    matched_segments.append(skip_segment)
                    logger.debug(
                        f"Recap match in '{segment.text[:50]}...' "
                        f"confidence={confidence:.2f}"
                    )
                elif preview_match:
                    confidence = preview_match["confidence"]
                    reason = f"Detected: {', '.join(preview_match['matched'])}"
                    skip_segment = SkipSegment(
                        start_ms=segment.start_time_ms,
                        end_ms=segment.end_time_ms,
                        segment_type="preview",
                        confidence=confidence,
                        reason=reason,
                    )
                    matched_segments.append(skip_segment)
                    logger.debug(
                        f"Preview match in '{segment.text[:50]}...' "
                        f"confidence={confidence:.2f}"
                    )

            logger.info(
                f"Pattern detection complete: {len(matched_segments)} segments "
                f"from {len(transcript)} transcript segments"
            )
            return matched_segments

        except Exception as e:
            msg = f"Pattern detection failed: {e}"
            logger.error(msg)
            raise PatternDetectionError(msg) from e

    def _match_keywords(
        self, text: str, keywords: list[str]
    ) -> dict[str, list[str] | float] | None:
        """Match keywords in text with word boundaries.

        Args:
            text: Text to search
            keywords: Keywords to match

        Returns:
            Dict with 'matched' list and 'confidence' float, or None if no match
        """
        text_lower = text.lower()
        matched = []

        for keyword in keywords:
            # Use word boundaries to match exact keywords
            pattern = rf"\b{re.escape(keyword)}\b"
            if re.search(pattern, text_lower):
                matched.append(keyword)

        if not matched:
            return None

        # Confidence based on number of keywords matched
        # More keywords = higher confidence (max 1.0)
        confidence = min(len(matched) / len(keywords), 1.0)
        confidence = max(confidence, 0.5)  # Minimum confidence 0.5 for at least one match

        return {"matched": matched, "confidence": confidence}
