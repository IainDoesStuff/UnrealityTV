"""Configuration system for UnrealityTV."""

from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings with support for environment variables."""

    plex_url: str = Field(default="http://localhost:32400")
    plex_token: str = Field(default="")
    watch_dir: Path = Field(default=Path("."))
    database_path: Path = Field(default=Path("unrealitytv.db"))
    gpu_enabled: bool = Field(default=False)

    # Phase 5: Enhanced configuration fields
    skip_segment_types: list[str] = Field(
        default=[],
        description="List of segment types to skip (e.g., recap, preview)"
    )
    confidence_threshold: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="Minimum confidence score for segments (0-1)"
    )
    min_segment_duration_ms: int = Field(
        default=3000,
        ge=0,
        description="Minimum segment duration in milliseconds"
    )
    detection_method: str = Field(
        default="auto",
        description="Scene detection method: scene_detect, transnetv2, hybrid, auto"
    )
    enable_plex_application: bool = Field(
        default=False,
        description="Enable applying segments to Plex"
    )
    batch_processing: bool = Field(
        default=False,
        description="Enable batch processing multiple episodes"
    )

    # Phase 6: Performance optimization and caching
    enable_caching: bool = Field(
        default=True,
        description="Enable result caching for transcription, analysis, and detection"
    )
    cache_dir: Path | None = Field(
        default=None,
        description="Cache directory (default: ~/.cache/unrealitytv)"
    )
    enable_metrics: bool = Field(
        default=False,
        description="Enable performance metrics collection"
    )
    metrics_file: Path | None = Field(
        default=None,
        description="File to persist performance metrics (JSON Lines format)"
    )
    enable_parallel_processing: bool = Field(
        default=False,
        description="Enable parallel processing of episodes"
    )
    max_workers: int = Field(
        default=4,
        ge=1,
        le=32,
        description="Maximum number of worker threads for parallel processing"
    )

    # Phase 7: Additional detection methods (silence and credits)
    silence_detection_enabled: bool = Field(
        default=False,
        description="Enable silence detection in videos"
    )
    silence_threshold_db: float = Field(
        default=-60.0,
        description="Decibel threshold for silence detection"
    )
    silence_min_duration_ms: int = Field(
        default=500,
        ge=0,
        description="Minimum silence duration in milliseconds"
    )
    credits_detection_enabled: bool = Field(
        default=False,
        description="Enable credits detection in videos"
    )
    credits_threshold: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="Confidence threshold for credits detection (0-1)"
    )
    credits_min_duration_ms: int = Field(
        default=5000,
        ge=0,
        description="Minimum credits sequence duration in milliseconds"
    )
    allow_combined_detection: bool = Field(
        default=True,
        description="Allow combining multiple detection methods in results"
    )

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
    }

    @field_validator("detection_method")
    @classmethod
    def validate_detection_method(cls, v: str) -> str:
        """Validate that detection_method is one of the allowed values."""
        allowed_methods = [
            "scene_detect",
            "transnetv2",
            "hybrid",
            "silence",
            "credits",
            "hybrid_extended",
            "auto",
        ]
        if v not in allowed_methods:
            msg = f"detection_method must be one of {allowed_methods}, got '{v}'"
            raise ValueError(msg)
        return v

    @field_validator("skip_segment_types", mode="before")
    @classmethod
    def parse_skip_segment_types(cls, v):
        """Parse skip_segment_types from comma-separated string if needed."""
        if isinstance(v, str):
            return [s.strip() for s in v.split(",") if s.strip()]
        return v or []
