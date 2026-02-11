"""Detection module for identifying skip-worthy segments."""

from .patterns import KeywordMatcher, PatternDetectionError

__all__ = ["KeywordMatcher", "PatternDetectionError"]
