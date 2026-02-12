"""Data models for UnrealityTV."""

import json
from datetime import datetime
from pathlib import Path
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator


class PlexMetadata(BaseModel):
    """Plex metadata for an episode."""

    plex_item_id: str
    plex_library_key: str
    plex_section_key: str


class Episode(BaseModel):
    """Represents a single episode."""

    file_path: Path
    show_name: str
    season: Optional[int] = None
    episode: Optional[int] = None
    duration_ms: Optional[int] = None
    plex_metadata: Optional[PlexMetadata] = None

    model_config = {"json_encoders": {Path: str}}


class SkipSegment(BaseModel):
    """Represents a segment to skip."""

    start_ms: int
    end_ms: int
    segment_type: Literal[
        "recap",
        "preview",
        "repeated_establishing_shot",
        "flashback",
        "filler",
    ]
    confidence: float = Field(..., ge=0.0, le=1.0)
    reason: str

    @field_validator("end_ms")
    @classmethod
    def end_after_start(cls, v, info):
        """Validate that end_ms > start_ms."""
        if "start_ms" in info.data and v <= info.data["start_ms"]:
            raise ValueError("end_ms must be greater than start_ms")
        return v


class SceneBoundary(BaseModel):
    """Represents a scene boundary in a video."""

    start_ms: int
    end_ms: int
    scene_index: int


class AnalysisResult(BaseModel):
    """Complete analysis result for an episode."""

    episode: Episode
    segments: list[SkipSegment]

    def to_json(self) -> str:
        """Serialize to JSON string."""
        return self.model_dump_json(serialize_as_any=True)

    @classmethod
    def from_json(cls, json_str: str) -> "AnalysisResult":
        """Deserialize from JSON string."""
        data = json.loads(json_str)
        return cls.model_validate(data)

    def to_file(self, path: Path) -> None:
        """Write analysis result to JSON file."""
        path.write_text(self.to_json())

    @classmethod
    def from_file(cls, path: Path) -> "AnalysisResult":
        """Load analysis result from JSON file."""
        return cls.from_json(path.read_text())


class SegmentApplicationResult(BaseModel):
    """Result of applying segments to an episode."""

    episode: Episode
    segments_applied: int = Field(..., ge=0, description="Number of segments successfully applied")
    segments_skipped: int = Field(..., ge=0, description="Number of segments skipped")
    skip_reasons: list[str] = Field(
        default=[],
        description="Reasons segments were skipped (confidence_too_low, duration_too_short, type_filtered)"
    )
    application_errors: list[str] = Field(
        default=[],
        description="List of errors encountered during application"
    )
    plex_error: Optional[str] = Field(None, description="Top-level Plex error if any")
    applied_at: datetime = Field(default_factory=datetime.now)

    @field_validator("skip_reasons")
    @classmethod
    def validate_skip_reasons(cls, v):
        """Validate that skip reasons are from allowed set."""
        allowed_reasons = {"confidence_too_low", "duration_too_short", "type_filtered"}
        invalid_reasons = set(v) - allowed_reasons
        if invalid_reasons:
            msg = f"Invalid skip reasons: {invalid_reasons}. Must be one of {allowed_reasons}"
            raise ValueError(msg)
        return v

    def to_json(self) -> str:
        """Serialize to JSON string."""
        return self.model_dump_json(serialize_as_any=True)

    @classmethod
    def from_json(cls, json_str: str) -> "SegmentApplicationResult":
        """Deserialize from JSON string."""
        data = json.loads(json_str)
        return cls.model_validate(data)

    def to_file(self, path: Path) -> None:
        """Write application result to JSON file."""
        path.write_text(self.to_json())

    @classmethod
    def from_file(cls, path: Path) -> "SegmentApplicationResult":
        """Load application result from JSON file."""
        return cls.from_json(path.read_text())
