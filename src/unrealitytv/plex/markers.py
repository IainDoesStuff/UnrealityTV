"""Plex marker management and data models."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class MarkerType(str, Enum):
    """Types of markers that can be created in Plex."""

    INTRO = "intro"
    CREDITS = "credits"
    COMMERCIAL = "commercial"
    PREVIEW = "preview"
    RECAP = "recap"


class PlexMarker(BaseModel):
    """Represents a marker in a Plex item."""

    item_id: str = Field(..., description="Plex item ID")
    start_ms: int = Field(..., ge=0, description="Start time in milliseconds")
    end_ms: int = Field(..., ge=0, description="End time in milliseconds")
    marker_type: MarkerType = Field(..., description="Type of marker")
    created_at: Optional[datetime] = Field(None, description="Creation timestamp")

    @field_validator("end_ms")
    @classmethod
    def end_after_start(cls, v, info):
        """Validate that end_ms > start_ms."""
        if "start_ms" in info.data and v <= info.data["start_ms"]:
            raise ValueError("end_ms must be greater than start_ms")
        return v

    def to_dict(self) -> dict:
        """Convert marker to dictionary."""
        data = self.model_dump()
        data["marker_type"] = self.marker_type.value
        return data
