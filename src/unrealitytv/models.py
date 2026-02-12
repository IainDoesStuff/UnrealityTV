"""Data models for UnrealityTV."""

import json
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
