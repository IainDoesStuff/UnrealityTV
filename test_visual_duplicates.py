#!/usr/bin/env python3
"""Test visual duplicate detection across episodes."""

import logging
from pathlib import Path

from unrealitytv.db import Database
from unrealitytv.detectors.visual_duplicate_detector import detect_visual_duplicates

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

def main():
    """Run visual duplicate detection on test episodes."""

    # Setup paths
    test_data_dir = Path("/home/desktop-server/opencode/UnrealityTV/test_data")
    db_path = Path("/tmp/unrealitytv_test.db")

    e02_video = test_data_dir / "90day_s04e02_5min.mkv"
    e03_video = test_data_dir / "90day_test_5min.mkv"

    # Verify videos exist
    if not e02_video.exists():
        logger.error(f"E02 video not found: {e02_video}")
        return
    if not e03_video.exists():
        logger.error(f"E03 video not found: {e03_video}")
        return

    logger.info(f"E02 video: {e02_video}")
    logger.info(f"E03 video: {e03_video}")

    # Initialize database
    logger.info(f"Initializing database: {db_path}")
    db = Database(db_path)
    db.initialize()

    try:
        # Phase 1: Analyze E02 and store frame hashes
        logger.info("=" * 80)
        logger.info("PHASE 1: Analyzing E02 (storing frame hashes)")
        logger.info("=" * 80)

        e02_segments = detect_visual_duplicates(
            video_path=e02_video,
            db=db,
            episode_id=1,  # S04E02
            fps=1.0,
            hamming_threshold=8,
            min_duration_ms=3000,
            gap_tolerance_ms=2000,
        )

        logger.info(f"E02 Analysis complete:")
        logger.info(f"  - Visual duplicate segments found: {len(e02_segments)}")
        if e02_segments:
            for seg in e02_segments:
                logger.info(
                    f"    - {seg.start_ms}ms-{seg.end_ms}ms "
                    f"({(seg.end_ms - seg.start_ms) / 1000:.1f}s) "
                    f"confidence: {seg.confidence:.2%}"
                )

        # Phase 2: Analyze E03 and find duplicates against E02
        logger.info("=" * 80)
        logger.info("PHASE 2: Analyzing E03 (finding duplicates against E02)")
        logger.info("=" * 80)

        e03_segments = detect_visual_duplicates(
            video_path=e03_video,
            db=db,
            episode_id=2,  # S04E03
            fps=1.0,
            hamming_threshold=8,
            min_duration_ms=3000,
            gap_tolerance_ms=2000,
        )

        logger.info(f"E03 Analysis complete:")
        logger.info(f"  - Visual duplicate segments found: {len(e03_segments)}")
        if e03_segments:
            for seg in e03_segments:
                logger.info(
                    f"    - {seg.start_ms}ms-{seg.end_ms}ms "
                    f"({(seg.end_ms - seg.start_ms) / 1000:.1f}s) "
                    f"confidence: {seg.confidence:.2%}"
                )
        else:
            logger.info("    - (No visual duplicates from E02 found in E03)")

        # Summary
        logger.info("=" * 80)
        logger.info("SUMMARY")
        logger.info("=" * 80)
        logger.info(f"E02 self-duplicates (within episode): {len(e02_segments)}")
        logger.info(f"E03 cross-duplicates (against E02): {len(e03_segments)}")

        # Expected behavior
        logger.info("\nExpected behavior:")
        logger.info("- E02 analysis: Small number of self-duplicates (flashbacks within episode)")
        logger.info("- E03 analysis: Likely higher number of cross-duplicates:")
        logger.info("  * Opening sequence (typical in reality TV)")
        logger.info("  * Flashback clips from prior scenes")
        logger.info("  * Recurring establishing shots")
        logger.info("  * Producer intros")

        logger.info("\n✅ Visual duplicate detection test complete!")

    finally:
        # Cleanup
        if db_path.exists():
            logger.info(f"\nTest database: {db_path}")
            logger.info("(Keeping database for inspection)")

if __name__ == "__main__":
    main()
