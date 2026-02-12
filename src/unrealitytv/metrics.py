"""Performance metrics collection and reporting."""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class MetricsError(Exception):
    """Exception raised when metrics operations fail."""

    pass


class ProcessingMetrics(BaseModel):
    """Metrics for a processing operation.

    Attributes:
        component: Name of the component (e.g., transcription, analysis)
        duration_ms: Duration of operation in milliseconds
        cached: Whether the result was retrieved from cache
        timestamp: When the operation completed
        episode_file: Optional path to associated episode file
    """

    component: str = Field(..., description="Component name (e.g., transcription, analysis)")
    duration_ms: int = Field(..., ge=0, description="Duration in milliseconds")
    cached: bool = Field(default=False, description="Whether result was cached")
    timestamp: datetime = Field(
        default_factory=datetime.now, description="When operation completed"
    )
    episode_file: Optional[Path] = Field(None, description="Associated episode file")

    model_config = {"json_encoders": {Path: str, datetime: str}}


class MetricsCollector:
    """Collects and aggregates processing metrics.

    Tracks performance metrics for different components and
    can export summaries for performance analysis.
    """

    def __init__(self, metrics_file: Optional[Path] = None) -> None:
        """Initialize metrics collector.

        Args:
            metrics_file: Optional file path to persist metrics to JSON
        """
        self.metrics_file = metrics_file
        self.metrics: list[ProcessingMetrics] = []

        if metrics_file:
            logger.info(f"Initialized MetricsCollector with file: {metrics_file}")
        else:
            logger.info("Initialized MetricsCollector (in-memory only)")

    def record(self, metric: ProcessingMetrics) -> None:
        """Record a processing metric.

        Args:
            metric: Metric to record

        Raises:
            MetricsError: If file persistence fails
        """
        self.metrics.append(metric)

        if self.metrics_file:
            try:
                self._append_to_file(metric)
            except Exception as e:
                logger.warning(f"Failed to write metric to file: {e}")

        logger.debug(
            f"Recorded metric: component={metric.component}, "
            f"duration_ms={metric.duration_ms}, cached={metric.cached}"
        )

    def _append_to_file(self, metric: ProcessingMetrics) -> None:
        """Append metric to file in JSON Lines format.

        Args:
            metric: Metric to append

        Raises:
            MetricsError: If write fails
        """
        try:
            self.metrics_file.parent.mkdir(parents=True, exist_ok=True)

            with open(self.metrics_file, "a") as f:
                json.dump(json.loads(metric.model_dump_json()), f)
                f.write("\n")
        except Exception as e:
            msg = f"Failed to append metric to {self.metrics_file}: {e}"
            raise MetricsError(msg) from e

    def get_average_duration(self, component: str) -> float:
        """Get average duration for a component.

        Args:
            component: Component name

        Returns:
            Average duration in milliseconds, or 0.0 if no metrics
        """
        component_metrics = [m for m in self.metrics if m.component == component]

        if not component_metrics:
            return 0.0

        total_duration = sum(m.duration_ms for m in component_metrics)
        return total_duration / len(component_metrics)

    def get_cache_hit_rate(self, component: Optional[str] = None) -> float:
        """Get cache hit rate as percentage.

        Args:
            component: Optional component name to filter by

        Returns:
            Cache hit rate as percentage (0-100)
        """
        if component:
            metrics = [m for m in self.metrics if m.component == component]
        else:
            metrics = self.metrics

        if not metrics:
            return 0.0

        cache_hits = sum(1 for m in metrics if m.cached)
        return (cache_hits / len(metrics)) * 100

    def export_summary(self) -> dict:
        """Export performance summary.

        Returns:
            Dict with summary statistics including total operations,
            cache hit rates, and per-component metrics
        """
        components = set(m.component for m in self.metrics)

        summary = {
            "total_operations": len(self.metrics),
            "total_cached": sum(1 for m in self.metrics if m.cached),
            "overall_cache_hit_rate": self.get_cache_hit_rate(),
            "components": {},
        }

        for component in sorted(components):
            summary["components"][component] = {
                "operations": len([m for m in self.metrics if m.component == component]),
                "average_duration_ms": self.get_average_duration(component),
                "cache_hit_rate": self.get_cache_hit_rate(component),
            }

        logger.info(f"Performance summary: {json.dumps(summary, indent=2)}")
        return summary
