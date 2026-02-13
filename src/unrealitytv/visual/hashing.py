"""Perceptual hashing module for frame comparison."""

from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def compute_phash(frame_path: Path) -> str:
    """Compute perceptual hash of a frame image.

    Uses imagehash library to compute a pHash (perceptual hash) of an image,
    which is robust to compression and minor visual changes.

    Args:
        frame_path: Path to JPEG frame image

    Returns:
        16-character hex string representing 64-bit pHash

    Raises:
        RuntimeError: If imagehash or PIL not installed
    """
    try:
        from PIL import Image

        import imagehash
    except ImportError as e:
        msg = "imagehash and Pillow required. Install with: pip install imagehash Pillow"
        logger.error(msg)
        raise RuntimeError(msg) from e

    try:
        with Image.open(frame_path) as img:
            hash_object = imagehash.phash(img)
            # Convert hash to 16-char hex string
            # hash_object.hash is a numpy array, convert to binary string
            hash_bits = str(hash_object).replace(" ", "")
            hash_int = int(hash_bits, 2)
            return format(hash_int, "016x")
    except (IOError, ValueError) as e:
        msg = f"Failed to compute pHash for {frame_path}: {e}"
        logger.error(msg)
        raise RuntimeError(msg) from e


def compute_hashes_batch(frames: list[tuple[int, Path]]) -> list[tuple[int, str]]:
    """Batch process frames to compute pHashes, skipping corrupted frames.

    Iterates through frames and computes perceptual hashes. Frames that cannot
    be processed (corrupted images, missing files) are logged and skipped.

    Args:
        frames: List of (timestamp_ms, frame_path) tuples

    Returns:
        List of (timestamp_ms, phash_hex_string) tuples, in input order
        (excluding skipped frames)

    """
    results = []
    for timestamp_ms, frame_path in frames:
        try:
            phash = compute_phash(frame_path)
            results.append((timestamp_ms, phash))
        except RuntimeError as e:
            logger.warning(f"Skipping corrupted frame {frame_path}: {e}")
    return results


def hamming_distance(hash1: str, hash2: str) -> int:
    """Calculate Hamming distance between two hex pHash strings.

    The Hamming distance is the number of bit positions where the two hashes
    differ. For 64-bit hashes, this ranges from 0 (identical) to 64 (completely
    different).

    Args:
        hash1: First 16-character hex pHash string
        hash2: Second 16-character hex pHash string

    Returns:
        Integer Hamming distance (0-64 for 64-bit hashes)
    """
    try:
        xor_result = int(hash1, 16) ^ int(hash2, 16)
        return bin(xor_result).count("1")
    except ValueError as e:
        msg = f"Invalid hex hash format: {e}"
        logger.error(msg)
        raise ValueError(msg) from e
