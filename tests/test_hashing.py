"""Tests for perceptual hashing module."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from unrealitytv.visual.hashing import compute_hashes_batch, compute_phash, hamming_distance


class TestComputePhash:
    """Test suite for compute_phash function."""

    @patch("PIL.Image.open")
    @patch("imagehash.phash")
    def test_compute_phash_returns_16_char_hex(self, mock_phash, mock_open):
        """Test that compute_phash returns 16-character hex string."""
        mock_image = MagicMock()
        mock_hash = MagicMock()
        mock_hash.__str__ = MagicMock(return_value="1010101010101010")

        mock_open.return_value.__enter__.return_value = mock_image
        mock_phash.return_value = mock_hash

        result = compute_phash(Path("test.jpg"))

        assert isinstance(result, str)
        assert len(result) == 16
        assert all(c in "0123456789abcdef" for c in result)

    def test_compute_phash_missing_dependencies(self):
        """Test RuntimeError when imagehash or PIL not installed."""
        with patch.dict("sys.modules", {"PIL": None, "imagehash": None}):
            with pytest.raises(RuntimeError) as exc_info:
                compute_phash(Path("test.jpg"))

            assert "imagehash and Pillow required" in str(exc_info.value)

    @patch("PIL.Image.open")
    def test_compute_phash_corrupted_image(self, mock_open):
        """Test RuntimeError for corrupted image file."""
        mock_open.side_effect = IOError("Cannot identify image file")

        with pytest.raises(RuntimeError) as exc_info:
            compute_phash(Path("corrupted.jpg"))

        assert "Failed to compute pHash" in str(exc_info.value)

    @patch("PIL.Image.open")
    @patch("imagehash.phash")
    def test_compute_phash_identical_hashes(self, mock_phash, mock_open):
        """Test that identical images produce identical hashes."""
        mock_image = MagicMock()
        mock_hash = MagicMock()
        mock_hash.__str__ = MagicMock(return_value="1010101010101010")

        mock_open.return_value.__enter__.return_value = mock_image
        mock_phash.return_value = mock_hash

        result1 = compute_phash(Path("test1.jpg"))
        result2 = compute_phash(Path("test2.jpg"))

        assert result1 == result2


class TestComputeHashesBatch:
    """Test suite for compute_hashes_batch function."""

    def test_compute_hashes_batch_valid_frames(self):
        """Test batch processing with valid frames."""
        frames = [
            (0, Path("frame_000001.jpg")),
            (1000, Path("frame_000002.jpg")),
        ]

        with patch("unrealitytv.visual.hashing.compute_phash") as mock_compute:
            mock_compute.side_effect = ["aaaaaaaaaaaaaaaa", "bbbbbbbbbbbbbbbb"]

            result = compute_hashes_batch(frames)

            assert len(result) == 2
            assert result[0] == (0, "aaaaaaaaaaaaaaaa")
            assert result[1] == (1000, "bbbbbbbbbbbbbbbb")

    def test_compute_hashes_batch_skips_corrupted(self):
        """Test that corrupted frames are skipped."""
        frames = [
            (0, Path("frame_000001.jpg")),
            (1000, Path("frame_000002.jpg")),
            (2000, Path("frame_000003.jpg")),
        ]

        with patch("unrealitytv.visual.hashing.compute_phash") as mock_compute:
            mock_compute.side_effect = [
                "aaaaaaaaaaaaaaaa",
                RuntimeError("Corrupted"),
                "cccccccccccccccc",
            ]

            result = compute_hashes_batch(frames)

            assert len(result) == 2
            assert result[0] == (0, "aaaaaaaaaaaaaaaa")
            assert result[1] == (2000, "cccccccccccccccc")

    def test_compute_hashes_batch_maintains_order(self):
        """Test that output maintains input order (excluding skipped)."""
        frames = [
            (5000, Path("frame5.jpg")),
            (1000, Path("frame1.jpg")),
            (3000, Path("frame3.jpg")),
        ]

        with patch("unrealitytv.visual.hashing.compute_phash") as mock_compute:
            mock_compute.side_effect = ["aaaa", "bbbb", "cccc"]

            result = compute_hashes_batch(frames)

            assert result[0][0] == 5000
            assert result[1][0] == 1000
            assert result[2][0] == 3000

    def test_compute_hashes_batch_empty_list(self):
        """Test with empty frame list."""
        result = compute_hashes_batch([])
        assert result == []

    def test_compute_hashes_batch_single_frame(self):
        """Test with single frame."""
        frames = [(0, Path("frame_000001.jpg"))]

        with patch("unrealitytv.visual.hashing.compute_phash") as mock_compute:
            mock_compute.return_value = "aaaaaaaaaaaaaaaa"

            result = compute_hashes_batch(frames)

            assert len(result) == 1
            assert result[0] == (0, "aaaaaaaaaaaaaaaa")

    def test_compute_hashes_batch_all_corrupted(self):
        """Test when all frames are corrupted."""
        frames = [
            (0, Path("frame_000001.jpg")),
            (1000, Path("frame_000002.jpg")),
        ]

        with patch("unrealitytv.visual.hashing.compute_phash") as mock_compute:
            mock_compute.side_effect = [RuntimeError("Bad"), RuntimeError("Bad")]

            result = compute_hashes_batch(frames)

            assert result == []


class TestHammingDistance:
    """Test suite for hamming_distance function."""

    def test_hamming_distance_identical(self):
        """Test Hamming distance for identical hashes."""
        hash1 = "aaaaaaaaaaaaaaaa"
        hash2 = "aaaaaaaaaaaaaaaa"
        assert hamming_distance(hash1, hash2) == 0

    def test_hamming_distance_single_bit_difference(self):
        """Test Hamming distance with single bit difference."""
        hash1 = "0000000000000000"
        hash2 = "0000000000000001"
        # 0 XOR 1 in last position = 1 bit different
        assert hamming_distance(hash1, hash2) == 1

    def test_hamming_distance_completely_different(self):
        """Test Hamming distance for completely different hashes."""
        hash1 = "0000000000000000"
        hash2 = "ffffffffffffffff"
        # 64 bits all different
        assert hamming_distance(hash1, hash2) == 64

    def test_hamming_distance_arbitrary_values(self):
        """Test Hamming distance with known values."""
        # 0x1234 XOR 0x5678 = 0x444c (5 bits set)
        hash1 = "0000000000001234"
        hash2 = "0000000000005678"
        distance = hamming_distance(hash1, hash2)
        assert distance == 5

    def test_hamming_distance_invalid_hex(self):
        """Test ValueError for invalid hex strings."""
        with pytest.raises(ValueError):
            hamming_distance("zzzzzzzzzzzzzzzz", "aaaaaaaaaaaaaaaa")

    def test_hamming_distance_symmetric(self):
        """Test that hamming_distance is symmetric."""
        hash1 = "aaaaaaaaaaaaaaaa"
        hash2 = "bbbbbbbbbbbbbbbb"
        assert hamming_distance(hash1, hash2) == hamming_distance(hash2, hash1)
