"""Detection orchestrator managing multiple scene detection methods."""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from unrealitytv.models import SceneBoundary

logger = logging.getLogger(__name__)


class DetectionOrchestrator:
    """Orchestrates scene detection using multiple methods with strategy selection."""

    def __init__(self, method: str = "auto"):
        """Initialize the orchestrator.

        Args:
            method: Detection method to use.
                - "scene_detect": PySceneDetect (CPU, always available)
                - "transnetv2": TransNetV2 (GPU, fallback to CPU if unavailable)
                - "hybrid": Run both methods and merge results
                - "silence": Silence detection using audio analysis
                - "credits": Credits detection using frame analysis
                - "visual_duplicates": Visual duplicate detection (returns SkipSegment)
                - "hybrid_extended": Run all available methods and merge results
                - "auto": Choose based on hardware availability (default)
        """
        self.method = method

    def detect_scenes(
        self,
        video_path: Path,
        **kwargs,
    ) -> list[SceneBoundary]:
        """Detect scenes using configured method.

        Args:
            video_path: Path to the video file
            **kwargs: Additional arguments passed to detection methods

        Returns:
            List of detected scenes as SceneBoundary objects.
            Note: "visual_duplicates" method returns SkipSegment list instead.
        """
        if self.method == "scene_detect":
            return self._detect_with_scene_detect(video_path, **kwargs)
        elif self.method == "transnetv2":
            return self._detect_with_transnetv2(video_path, **kwargs)
        elif self.method == "hybrid":
            return self._detect_with_hybrid(video_path, **kwargs)
        elif self.method == "silence":
            return self._detect_with_silence(video_path, **kwargs)
        elif self.method == "credits":
            return self._detect_with_credits(video_path, **kwargs)
        elif self.method == "visual_duplicates":
            return self._detect_with_visual_duplicates(video_path, **kwargs)
        elif self.method == "hybrid_extended":
            return self._detect_with_hybrid_extended(video_path, **kwargs)
        elif self.method == "auto":
            return self._detect_with_auto_select(video_path, **kwargs)
        else:
            msg = f"Unknown detection method: {self.method}"
            logger.error(msg)
            raise ValueError(msg)

    def _detect_with_scene_detect(
        self,
        video_path: Path,
        **kwargs,
    ) -> list[SceneBoundary]:
        """Detect scenes using PySceneDetect."""
        from unrealitytv.detectors.scene_detector import detect_scenes

        logger.info(f"Detecting scenes with PySceneDetect for {video_path.name}")
        start_time = time.time()

        try:
            scenes = detect_scenes(video_path, **kwargs)
            elapsed = time.time() - start_time
            logger.info(
                f"PySceneDetect detected {len(scenes)} scenes in {elapsed:.2f}s"
            )
            return scenes
        except Exception as e:
            logger.error(f"PySceneDetect detection failed: {e}")
            raise

    def _detect_with_transnetv2(
        self,
        video_path: Path,
        **kwargs,
    ) -> list[SceneBoundary]:
        """Detect scenes using TransNetV2."""
        from unrealitytv.detectors.transnetv2_detector import detect_scenes_gpu

        logger.info(f"Detecting scenes with TransNetV2 for {video_path.name}")
        start_time = time.time()

        try:
            scenes = detect_scenes_gpu(video_path, **kwargs)
            elapsed = time.time() - start_time
            logger.info(
                f"TransNetV2 detected {len(scenes)} scenes in {elapsed:.2f}s"
            )
            return scenes
        except RuntimeError as e:
            if "transnetv2 library is not installed" in str(e):
                logger.warning("TransNetV2 not available, falling back to PySceneDetect")
                return self._detect_with_scene_detect(video_path, **kwargs)
            raise

    def _detect_with_hybrid(
        self,
        video_path: Path,
        **kwargs,
    ) -> list[SceneBoundary]:
        """Detect scenes using both methods and merge results."""
        logger.info(f"Detecting scenes with hybrid method for {video_path.name}")
        start_time = time.time()

        # Run PySceneDetect
        scene_detect_scenes = self._detect_with_scene_detect(video_path, **kwargs)

        # Try to run TransNetV2
        try:
            transnetv2_scenes = self._detect_with_transnetv2(video_path, **kwargs)
        except RuntimeError:
            logger.warning("TransNetV2 failed, using only PySceneDetect results")
            transnetv2_scenes = []

        # Merge results
        merged = self._merge_scene_lists(scene_detect_scenes, transnetv2_scenes)
        elapsed = time.time() - start_time
        logger.info(
            f"Hybrid detection found {len(merged)} scenes in {elapsed:.2f}s "
            f"({len(scene_detect_scenes)} from PySceneDetect, "
            f"{len(transnetv2_scenes)} from TransNetV2)"
        )
        return merged

    def _detect_with_silence(
        self,
        video_path: Path,
        **kwargs,
    ) -> list[SceneBoundary]:
        """Detect silence segments using audio analysis."""
        from unrealitytv.detectors.silence_detector import detect_silence

        logger.info(f"Detecting silence in {video_path.name}")
        start_time = time.time()

        try:
            silences = detect_silence(video_path, **kwargs)
            elapsed = time.time() - start_time
            logger.info(
                f"Silence detection found {len(silences)} segments in {elapsed:.2f}s"
            )
            return silences
        except Exception as e:
            logger.error(f"Silence detection failed: {e}")
            raise

    def _detect_with_credits(
        self,
        video_path: Path,
        **kwargs,
    ) -> list[SceneBoundary]:
        """Detect credits sequences using frame analysis."""
        from unrealitytv.detectors.credits_detector import detect_credits

        logger.info(f"Detecting credits in {video_path.name}")
        start_time = time.time()

        try:
            credits = detect_credits(video_path, **kwargs)
            elapsed = time.time() - start_time
            logger.info(
                f"Credits detection found {len(credits)} segments in {elapsed:.2f}s"
            )
            return credits
        except Exception as e:
            logger.error(f"Credits detection failed: {e}")
            raise

    def _detect_with_hybrid_extended(
        self,
        video_path: Path,
        **kwargs,
    ) -> list[SceneBoundary]:
        """Run all available detection methods and merge results."""
        logger.info(f"Detecting scenes with hybrid_extended method for {video_path.name}")
        start_time = time.time()

        results: list[SceneBoundary] = []

        # Run PySceneDetect
        scene_detect_scenes = self._detect_with_scene_detect(video_path, **kwargs)
        results.extend(scene_detect_scenes)

        # Try TransNetV2
        try:
            transnetv2_scenes = self._detect_with_transnetv2(video_path, **kwargs)
            results.extend(transnetv2_scenes)
        except RuntimeError as e:
            logger.warning(f"TransNetV2 detection skipped: {e}")

        # Try Silence detection
        try:
            silence_scenes = self._detect_with_silence(video_path, **kwargs)
            results.extend(silence_scenes)
        except Exception as e:
            logger.warning(f"Silence detection skipped: {e}")

        # Try Credits detection
        try:
            credits_scenes = self._detect_with_credits(video_path, **kwargs)
            results.extend(credits_scenes)
        except Exception as e:
            logger.warning(f"Credits detection skipped: {e}")

        # Merge all results
        merged = self._merge_scene_lists(
            results, []
        ) if results else []
        elapsed = time.time() - start_time
        logger.info(
            f"Hybrid extended detection found {len(merged)} combined segments "
            f"in {elapsed:.2f}s"
        )
        return merged

    def _detect_with_auto_select(
        self,
        video_path: Path,
        **kwargs,
    ) -> list[SceneBoundary]:
        """Auto-select method based on hardware availability."""
        try:
            import torch

            if torch.cuda.is_available():
                logger.info("GPU available, using TransNetV2")
                return self._detect_with_transnetv2(video_path, **kwargs)
        except ImportError:
            pass

        logger.info("No GPU available, using PySceneDetect")
        return self._detect_with_scene_detect(video_path, **kwargs)

    def _detect_with_visual_duplicates(
        self,
        video_path: Path,
        **kwargs,
    ) -> list:
        """Detect visually duplicate frames across episodes.

        This method returns SkipSegment objects (not SceneBoundary),
        as visual duplicates are identified flashback segments ready to skip.

        Args:
            video_path: Path to the video file
            **kwargs: Additional arguments passed to detect_visual_duplicates
                      (db, episode_id, fps, hamming_threshold, etc.)

        Returns:
            List of SkipSegment objects representing detected flashbacks
        """
        try:
            from unrealitytv.detectors.visual_duplicate_detector import (
                detect_visual_duplicates,
            )

            logger.info(
                f"Detecting visual duplicates for {video_path.name}"
            )
            start_time = time.time()

            segments = detect_visual_duplicates(video_path, **kwargs)
            elapsed = time.time() - start_time
            logger.info(
                f"Visual duplicate detection found {len(segments)} segments in {elapsed:.2f}s"
            )
            return segments
        except ImportError as e:
            msg = "Visual duplicate detection requires imagehash and Pillow: pip install imagehash Pillow"
            logger.error(msg)
            raise RuntimeError(msg) from e
        except Exception as e:
            logger.error(f"Visual duplicate detection failed: {e}")
            raise

    @staticmethod
    def _merge_scene_lists(
        scenes1: list[SceneBoundary],
        scenes2: list[SceneBoundary],
    ) -> list[SceneBoundary]:
        """Merge two lists of scenes, removing duplicates and overlaps.

        Args:
            scenes1: First list of scenes (e.g., from PySceneDetect)
            scenes2: Second list of scenes (e.g., from TransNetV2)

        Returns:
            Merged list of unique scenes, sorted by start time
        """
        if not scenes2:
            return scenes1
        if not scenes1:
            return scenes2

        # Combine and sort all scenes
        all_scenes = sorted(
            scenes1 + scenes2, key=lambda s: (s.start_ms, s.end_ms)
        )

        merged: list[SceneBoundary] = []
        for scene in all_scenes:
            if not merged:
                merged.append(scene)
            else:
                last = merged[-1]
                # Check if scenes overlap or are adjacent (within 100ms)
                if scene.start_ms <= last.end_ms + 100:
                    # Merge: extend end time to max of both
                    last.end_ms = max(last.end_ms, scene.end_ms)
                else:
                    # Non-overlapping, add as new scene
                    merged.append(scene)

        # Re-index scenes
        for i, scene in enumerate(merged):
            scene.scene_index = i

        return merged
