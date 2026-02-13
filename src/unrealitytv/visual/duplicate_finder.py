"""Cross-episode duplicate frame finder."""

from __future__ import annotations

import logging

from pydantic import BaseModel

from unrealitytv.db import Database, RepositoryError

logger = logging.getLogger(__name__)


class DuplicateMatch(BaseModel):
    """Represents a matched duplicate frame across episodes."""

    source_episode_id: int
    source_timestamp_ms: int
    source_phash: str
    match_episode_id: int
    match_timestamp_ms: int
    match_phash: str
    hamming_distance: int


class DuplicateFinder:
    """Finder for visually duplicate frames across episodes."""

    def __init__(self, db: Database, hamming_threshold: int = 8) -> None:
        """Initialize duplicate finder.

        Args:
            db: Database instance for accessing frame hashes
            hamming_threshold: Maximum Hamming distance to consider a match (0-64)
        """
        self.db = db
        self.hamming_threshold = hamming_threshold

    def find_duplicates(self, episode_id: int) -> list[DuplicateMatch]:
        """Find all duplicate frames for an episode in other episodes.

        Args:
            episode_id: ID of the source episode

        Returns:
            List of DuplicateMatch objects sorted by source_timestamp_ms

        Raises:
            RepositoryError: If database query fails
        """
        try:
            from unrealitytv.db import FrameHashRepository

            repo = FrameHashRepository(self.db)
            source_hashes = repo.get_hashes_by_episode(episode_id)

            matches = []
            for source_hash in source_hashes:
                similar = repo.find_similar_hashes(
                    source_hash["phash"], exclude_episode_id=episode_id
                )
                for match_hash in similar:
                    distance = self._hamming_distance(
                        source_hash["phash"], match_hash["phash"]
                    )
                    if distance <= self.hamming_threshold:
                        matches.append(
                            DuplicateMatch(
                                source_episode_id=episode_id,
                                source_timestamp_ms=source_hash["timestamp_ms"],
                                source_phash=source_hash["phash"],
                                match_episode_id=match_hash["episode_id"],
                                match_timestamp_ms=match_hash["timestamp_ms"],
                                match_phash=match_hash["phash"],
                                hamming_distance=distance,
                            )
                        )

            return sorted(matches, key=lambda x: x.source_timestamp_ms)
        except RepositoryError:
            raise
        except Exception as e:
            msg = f"Failed to find duplicates for episode {episode_id}: {e}"
            logger.error(msg)
            raise RepositoryError(msg) from e

    def find_duplicates_for_hashes(
        self, episode_id: int, hashes: list[tuple[int, str]]
    ) -> list[DuplicateMatch]:
        """Find duplicates for a specific set of hashes.

        Args:
            episode_id: ID of the source episode
            hashes: List of (timestamp_ms, phash) tuples

        Returns:
            List of DuplicateMatch objects sorted by source_timestamp_ms

        Raises:
            RepositoryError: If database query fails
        """
        try:
            from unrealitytv.db import FrameHashRepository

            repo = FrameHashRepository(self.db)

            matches = []
            for timestamp_ms, phash in hashes:
                similar = repo.find_similar_hashes(phash, exclude_episode_id=episode_id)
                for match_hash in similar:
                    distance = self._hamming_distance(phash, match_hash["phash"])
                    if distance <= self.hamming_threshold:
                        matches.append(
                            DuplicateMatch(
                                source_episode_id=episode_id,
                                source_timestamp_ms=timestamp_ms,
                                source_phash=phash,
                                match_episode_id=match_hash["episode_id"],
                                match_timestamp_ms=match_hash["timestamp_ms"],
                                match_phash=match_hash["phash"],
                                hamming_distance=distance,
                            )
                        )

            return sorted(matches, key=lambda x: x.source_timestamp_ms)
        except RepositoryError:
            raise
        except Exception as e:
            msg = f"Failed to find duplicates for episode {episode_id}: {e}"
            logger.error(msg)
            raise RepositoryError(msg) from e

    @staticmethod
    def _hamming_distance(hash1: str, hash2: str) -> int:
        """Calculate Hamming distance between two hex hashes.

        Args:
            hash1: First hex hash string
            hash2: Second hex hash string

        Returns:
            Hamming distance (0-64 for 64-bit hashes)
        """
        try:
            xor_result = int(hash1, 16) ^ int(hash2, 16)
            return bin(xor_result).count("1")
        except ValueError:
            return 64  # Max distance for invalid hashes
