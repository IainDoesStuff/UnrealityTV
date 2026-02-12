"""Tests for performance metrics collection."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import pytest

from unrealitytv.metrics import MetricsCollector, ProcessingMetrics


class TestProcessingMetrics:
    """Tests for ProcessingMetrics model."""

    def test_metrics_creation(self) -> None:
        """Test creating a processing metric."""
        metric = ProcessingMetrics(
            component="transcription",
            duration_ms=1000,
            cached=False,
        )
        assert metric.component == "transcription"
        assert metric.duration_ms == 1000
        assert metric.cached is False
        assert isinstance(metric.timestamp, datetime)

    def test_metrics_with_episode(self, tmp_path: Path) -> None:
        """Test metric with episode file."""
        episode_file = tmp_path / "episode.mp4"
        metric = ProcessingMetrics(
            component="analysis",
            duration_ms=5000,
            cached=True,
            episode_file=episode_file,
        )
        assert metric.episode_file == episode_file

    def test_metrics_validation_duration(self) -> None:
        """Test duration validation."""
        with pytest.raises(ValueError):
            ProcessingMetrics(component="test", duration_ms=-1)

    def test_metrics_serialization(self) -> None:
        """Test metrics can be serialized to JSON."""
        metric = ProcessingMetrics(
            component="transcription",
            duration_ms=1000,
            cached=False,
        )
        json_str = metric.model_dump_json()
        data = json.loads(json_str)

        assert data["component"] == "transcription"
        assert data["duration_ms"] == 1000
        assert data["cached"] is False


class TestMetricsCollector:
    """Tests for MetricsCollector."""

    @pytest.fixture
    def collector(self, tmp_path: Path) -> MetricsCollector:
        """Create metrics collector with temp file."""
        metrics_file = tmp_path / "metrics.jsonl"
        return MetricsCollector(metrics_file=metrics_file)

    @pytest.fixture
    def collector_memory_only(self) -> MetricsCollector:
        """Create in-memory metrics collector."""
        return MetricsCollector()

    def test_init_with_file(self, tmp_path: Path) -> None:
        """Test initializing with metrics file."""
        metrics_file = tmp_path / "metrics.jsonl"
        collector = MetricsCollector(metrics_file=metrics_file)

        assert collector.metrics_file == metrics_file
        assert collector.metrics == []

    def test_init_memory_only(self) -> None:
        """Test initializing without metrics file."""
        collector = MetricsCollector()

        assert collector.metrics_file is None
        assert collector.metrics == []

    def test_record_metric(self, collector: MetricsCollector) -> None:
        """Test recording a metric."""
        metric = ProcessingMetrics(
            component="transcription", duration_ms=1000, cached=False
        )

        collector.record(metric)

        assert len(collector.metrics) == 1
        assert collector.metrics[0] == metric

    def test_record_persists_to_file(self, collector: MetricsCollector) -> None:
        """Test that metrics are persisted to file."""
        metric = ProcessingMetrics(
            component="transcription", duration_ms=1000, cached=False
        )

        collector.record(metric)

        assert collector.metrics_file.exists()
        with open(collector.metrics_file) as f:
            lines = f.readlines()

        assert len(lines) == 1
        data = json.loads(lines[0])
        assert data["component"] == "transcription"

    def test_record_multiple_metrics(self, collector: MetricsCollector) -> None:
        """Test recording multiple metrics."""
        for i in range(5):
            metric = ProcessingMetrics(
                component="transcription", duration_ms=1000 * i, cached=i % 2 == 0
            )
            collector.record(metric)

        assert len(collector.metrics) == 5

        with open(collector.metrics_file) as f:
            lines = f.readlines()

        assert len(lines) == 5

    def test_get_average_duration(self, collector_memory_only: MetricsCollector) -> None:
        """Test calculating average duration for component."""
        metrics = [
            ProcessingMetrics(component="transcription", duration_ms=1000),
            ProcessingMetrics(component="transcription", duration_ms=2000),
            ProcessingMetrics(component="transcription", duration_ms=3000),
        ]

        for metric in metrics:
            collector_memory_only.record(metric)

        avg = collector_memory_only.get_average_duration("transcription")
        assert avg == 2000.0

    def test_get_average_duration_no_metrics(
        self, collector_memory_only: MetricsCollector
    ) -> None:
        """Test average duration returns 0 for missing component."""
        avg = collector_memory_only.get_average_duration("nonexistent")
        assert avg == 0.0

    def test_get_cache_hit_rate_all(self, collector_memory_only: MetricsCollector) -> None:
        """Test cache hit rate across all components."""
        metrics = [
            ProcessingMetrics(component="transcription", duration_ms=1000, cached=True),
            ProcessingMetrics(component="transcription", duration_ms=1000, cached=False),
            ProcessingMetrics(component="analysis", duration_ms=5000, cached=True),
            ProcessingMetrics(component="analysis", duration_ms=5000, cached=True),
        ]

        for metric in metrics:
            collector_memory_only.record(metric)

        hit_rate = collector_memory_only.get_cache_hit_rate()
        assert hit_rate == 75.0  # 3 out of 4

    def test_get_cache_hit_rate_by_component(
        self, collector_memory_only: MetricsCollector
    ) -> None:
        """Test cache hit rate for specific component."""
        metrics = [
            ProcessingMetrics(component="transcription", duration_ms=1000, cached=True),
            ProcessingMetrics(component="transcription", duration_ms=1000, cached=False),
            ProcessingMetrics(component="analysis", duration_ms=5000, cached=True),
            ProcessingMetrics(component="analysis", duration_ms=5000, cached=True),
        ]

        for metric in metrics:
            collector_memory_only.record(metric)

        transcription_rate = collector_memory_only.get_cache_hit_rate("transcription")
        assert transcription_rate == 50.0  # 1 out of 2

        analysis_rate = collector_memory_only.get_cache_hit_rate("analysis")
        assert analysis_rate == 100.0  # 2 out of 2

    def test_get_cache_hit_rate_no_metrics(
        self, collector_memory_only: MetricsCollector
    ) -> None:
        """Test cache hit rate returns 0 with no metrics."""
        hit_rate = collector_memory_only.get_cache_hit_rate()
        assert hit_rate == 0.0

    def test_export_summary(self, collector_memory_only: MetricsCollector) -> None:
        """Test exporting performance summary."""
        metrics = [
            ProcessingMetrics(component="transcription", duration_ms=1000, cached=True),
            ProcessingMetrics(component="transcription", duration_ms=2000, cached=False),
            ProcessingMetrics(component="analysis", duration_ms=5000, cached=True),
            ProcessingMetrics(component="detection", duration_ms=3000, cached=False),
        ]

        for metric in metrics:
            collector_memory_only.record(metric)

        summary = collector_memory_only.export_summary()

        assert summary["total_operations"] == 4
        assert summary["total_cached"] == 2
        assert summary["overall_cache_hit_rate"] == 50.0

        # Check component breakdown
        assert len(summary["components"]) == 3
        assert summary["components"]["transcription"]["operations"] == 2
        assert summary["components"]["transcription"]["average_duration_ms"] == 1500.0
        assert summary["components"]["transcription"]["cache_hit_rate"] == 50.0

        assert summary["components"]["analysis"]["operations"] == 1
        assert summary["components"]["analysis"]["average_duration_ms"] == 5000.0
        assert summary["components"]["analysis"]["cache_hit_rate"] == 100.0

        assert summary["components"]["detection"]["operations"] == 1
        assert summary["components"]["detection"]["cache_hit_rate"] == 0.0

    def test_export_summary_empty(
        self, collector_memory_only: MetricsCollector
    ) -> None:
        """Test export summary with no metrics."""
        summary = collector_memory_only.export_summary()

        assert summary["total_operations"] == 0
        assert summary["total_cached"] == 0
        assert summary["overall_cache_hit_rate"] == 0.0
        assert summary["components"] == {}

    def test_record_creates_directory(self, tmp_path: Path) -> None:
        """Test that record creates parent directories."""
        metrics_file = tmp_path / "subdir" / "metrics.jsonl"
        collector = MetricsCollector(metrics_file=metrics_file)

        metric = ProcessingMetrics(component="test", duration_ms=100)
        collector.record(metric)

        assert metrics_file.exists()
        assert metrics_file.parent.exists()

    def test_file_persistence_format(self, collector: MetricsCollector) -> None:
        """Test that metrics file uses JSON Lines format."""
        for i in range(3):
            metric = ProcessingMetrics(
                component=f"component_{i}", duration_ms=1000 * (i + 1)
            )
            collector.record(metric)

        with open(collector.metrics_file) as f:
            lines = f.readlines()

        assert len(lines) == 3

        # Verify each line is valid JSON
        for line in lines:
            data = json.loads(line)
            assert "component" in data
            assert "duration_ms" in data
            assert "cached" in data

    def test_metrics_with_episode_file(
        self, collector_memory_only: MetricsCollector, tmp_path: Path
    ) -> None:
        """Test metrics with episode file paths."""
        episode_file = tmp_path / "episode.mp4"
        metric = ProcessingMetrics(
            component="analysis",
            duration_ms=5000,
            cached=True,
            episode_file=episode_file,
        )

        collector_memory_only.record(metric)

        summary = collector_memory_only.export_summary()
        assert summary["total_operations"] == 1
        assert summary["components"]["analysis"]["cache_hit_rate"] == 100.0

    def test_concurrent_recording(self, collector_memory_only: MetricsCollector) -> None:
        """Test recording many metrics."""
        for component in ["transcription", "analysis", "detection"]:
            for i in range(10):
                metric = ProcessingMetrics(
                    component=component,
                    duration_ms=1000 * (i + 1),
                    cached=i % 3 == 0,
                )
                collector_memory_only.record(metric)

        assert len(collector_memory_only.metrics) == 30

        summary = collector_memory_only.export_summary()
        assert len(summary["components"]) == 3
        for component in ["transcription", "analysis", "detection"]:
            assert summary["components"][component]["operations"] == 10

    def test_metrics_error_on_write(self, tmp_path: Path) -> None:
        """Test MetricsError on write failure."""
        metrics_file = tmp_path / "metrics.jsonl"
        collector = MetricsCollector(metrics_file=metrics_file)

        # Make parent directory read-only
        tmp_path.chmod(0o444)
        try:
            metric = ProcessingMetrics(component="test", duration_ms=100)
            # Record should still work (just logs warning)
            collector.record(metric)
            # But the metric should be in memory
            assert len(collector.metrics) == 1
        finally:
            tmp_path.chmod(0o755)
