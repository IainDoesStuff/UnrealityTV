"""SQLite database manager with migration support."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Optional, Dict, List


class Database:
    """SQLite database manager with migration support."""

    def __init__(self, db_path: Path):
        """Initialize database manager.

        Args:
            db_path: Path to the SQLite database file.
        """
        self.db_path = Path(db_path)
        self._connection = None

    @property
    def connection(self):
        """Get or create database connection."""
        if self._connection is None:
            self._connection = sqlite3.connect(str(self.db_path))
            # Enable dict-like row access
            self._connection.row_factory = sqlite3.Row
        return self._connection

    def initialize(self):
        """Run all migration SQL files in order.

        This method:
        1. Creates the _migrations tracking table
        2. Finds all .sql files in the migrations directory
        3. Applies each migration only once
        4. Records applied migrations in the _migrations table
        """
        # Get migrations directory (sibling of src/unrealitytv)
        migrations_dir = Path(__file__).parent / "migrations"
        migrations_dir.mkdir(exist_ok=True)

        # Create migrations table if it doesn't exist
        self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS _migrations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE
            )
            """
        )
        self.connection.commit()

        # Apply any unapplied migrations
        for migration_file in sorted(migrations_dir.glob("*.sql")):
            name = migration_file.name

            # Check if this migration has already been applied
            cursor = self.connection.execute(
                "SELECT * FROM _migrations WHERE name = ?", (name,)
            )
            if cursor.fetchone():
                continue

            # Run the migration
            with open(migration_file, "r") as f:
                sql = f.read()
            self.connection.executescript(sql)

            # Record that this migration was applied
            self.connection.execute(
                "INSERT INTO _migrations (name) VALUES (?)", (name,)
            )
            self.connection.commit()

        return self

    def close(self):
        """Close database connection."""
        if self._connection:
            self._connection.close()
            self._connection = None

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()


class RepositoryError(Exception):
    """Exception raised for repository operation failures."""

    pass


class EpisodeRepository:
    """Repository for managing episodes in the database."""

    def __init__(self, db: Database) -> None:
        """Initialize episode repository.

        Args:
            db: Database instance for connection management.
        """
        self.db = db

    def add_episode(
        self,
        file_path: str,
        show_name: str,
        season: Optional[int] = None,
        episode: Optional[int] = None,
        duration_ms: Optional[int] = None,
    ) -> int:
        """Add a new episode to the database.

        Args:
            file_path: Path to the episode file (must be unique)
            show_name: Name of the TV show
            season: Season number (optional)
            episode: Episode number (optional)
            duration_ms: Duration in milliseconds (optional)

        Returns:
            ID of the newly created episode

        Raises:
            RepositoryError: If episode already exists or insertion fails
        """
        try:
            cursor = self.db.connection.cursor()
            cursor.execute("SELECT id FROM episodes WHERE file_path = ?", (file_path,))
            if cursor.fetchone():
                msg = f"Episode with file path '{file_path}' already exists"
                raise RepositoryError(msg)

            cursor.execute(
                """
                INSERT INTO episodes (file_path, show_name, season, episode, duration_ms)
                VALUES (?, ?, ?, ?, ?)
                """,
                (file_path, show_name, season, episode, duration_ms),
            )
            self.db.connection.commit()
            return cursor.lastrowid
        except RepositoryError:
            raise
        except Exception as e:
            msg = f"Failed to add episode: {e}"
            raise RepositoryError(msg) from e

    def update_episode_metadata(
        self,
        episode_id: int,
        duration_ms: Optional[int] = None,
        analyzed_at: Optional[str] = None,
    ) -> None:
        """Update episode metadata.

        Args:
            episode_id: ID of the episode to update
            duration_ms: Duration in milliseconds (optional)
            analyzed_at: Timestamp of analysis (optional)

        Raises:
            RepositoryError: If episode not found or update fails
        """
        try:
            cursor = self.db.connection.cursor()
            cursor.execute(
                """
                UPDATE episodes
                SET duration_ms = COALESCE(?, duration_ms),
                    analyzed_at = COALESCE(?, analyzed_at)
                WHERE id = ?
                """,
                (duration_ms, analyzed_at, episode_id),
            )
            self.db.connection.commit()
            if cursor.rowcount == 0:
                msg = f"No episode found with ID {episode_id}"
                raise RepositoryError(msg)
        except RepositoryError:
            raise
        except Exception as e:
            msg = f"Failed to update episode metadata: {e}"
            raise RepositoryError(msg) from e

    def get_episode_by_file_path(self, file_path: str) -> Optional[Dict]:
        """Get episode by file path.

        Args:
            file_path: Path to the episode file

        Returns:
            Dictionary with episode data or None if not found

        Raises:
            RepositoryError: If query fails
        """
        try:
            cursor = self.db.connection.cursor()
            cursor.execute("SELECT * FROM episodes WHERE file_path = ?", (file_path,))
            row = cursor.fetchone()
            return dict(row) if row else None
        except Exception as e:
            msg = f"Failed to get episode by file path: {e}"
            raise RepositoryError(msg) from e

    def find_episodes_by_show(self, show_name: str) -> List[Dict]:
        """Find all episodes by show name.

        Args:
            show_name: Name of the TV show

        Returns:
            List of episode dictionaries

        Raises:
            RepositoryError: If query fails
        """
        try:
            cursor = self.db.connection.cursor()
            cursor.execute("SELECT * FROM episodes WHERE show_name = ?", (show_name,))
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        except Exception as e:
            msg = f"Failed to find episodes by show: {e}"
            raise RepositoryError(msg) from e

    def find_episodes_by_season(
        self, show_name: str, season: int
    ) -> List[Dict]:
        """Find episodes by show name and season.

        Args:
            show_name: Name of the TV show
            season: Season number

        Returns:
            List of episode dictionaries

        Raises:
            RepositoryError: If query fails
        """
        try:
            cursor = self.db.connection.cursor()
            cursor.execute(
                "SELECT * FROM episodes WHERE show_name = ? AND season = ?",
                (show_name, season),
            )
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        except Exception as e:
            msg = f"Failed to find episodes by season: {e}"
            raise RepositoryError(msg) from e

    def delete_episode(self, episode_id: int) -> None:
        """Delete an episode by ID.

        Args:
            episode_id: ID of the episode to delete

        Raises:
            RepositoryError: If episode not found or deletion fails
        """
        try:
            cursor = self.db.connection.cursor()
            cursor.execute("DELETE FROM episodes WHERE id = ?", (episode_id,))
            self.db.connection.commit()
            if cursor.rowcount == 0:
                msg = f"No episode found with ID {episode_id}"
                raise RepositoryError(msg)
        except RepositoryError:
            raise
        except Exception as e:
            msg = f"Failed to delete episode: {e}"
            raise RepositoryError(msg) from e


class SkipSegmentRepository:
    """Repository for managing skip segments in the database."""

    def __init__(self, db: Database) -> None:
        """Initialize skip segment repository.

        Args:
            db: Database instance for connection management.
        """
        self.db = db

    def add_segment(
        self,
        episode_id: int,
        start_ms: int,
        end_ms: int,
        segment_type: str,
        confidence: float,
        reason: Optional[str] = None,
    ) -> int:
        """Add a skip segment for an episode.

        Args:
            episode_id: ID of the episode
            start_ms: Start time in milliseconds
            end_ms: End time in milliseconds
            segment_type: Type of segment (e.g., 'recap', 'preview')
            confidence: Confidence score (0.0-1.0)
            reason: Reason for detection (optional)

        Returns:
            ID of the newly created segment

        Raises:
            RepositoryError: If insertion fails
        """
        try:
            cursor = self.db.connection.cursor()
            cursor.execute(
                """
                INSERT INTO skip_segments
                (episode_id, start_ms, end_ms, segment_type, confidence, reason)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (episode_id, start_ms, end_ms, segment_type, confidence, reason),
            )
            self.db.connection.commit()
            return cursor.lastrowid
        except Exception as e:
            msg = f"Failed to add skip segment: {e}"
            raise RepositoryError(msg) from e

    def get_segments_by_episode(self, episode_id: int) -> List[Dict]:
        """Get all skip segments for an episode.

        Args:
            episode_id: ID of the episode

        Returns:
            List of segment dictionaries

        Raises:
            RepositoryError: If query fails
        """
        try:
            cursor = self.db.connection.cursor()
            cursor.execute(
                "SELECT * FROM skip_segments WHERE episode_id = ?", (episode_id,)
            )
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        except Exception as e:
            msg = f"Failed to get segments by episode: {e}"
            raise RepositoryError(msg) from e

    def update_segment(
        self,
        segment_id: int,
        start_ms: int,
        end_ms: int,
        confidence: float,
        reason: Optional[str] = None,
    ) -> None:
        """Update a skip segment.

        Args:
            segment_id: ID of the segment to update
            start_ms: Start time in milliseconds
            end_ms: End time in milliseconds
            confidence: Confidence score (0.0-1.0)
            reason: Reason for detection (optional)

        Raises:
            RepositoryError: If segment not found or update fails
        """
        try:
            cursor = self.db.connection.cursor()
            cursor.execute(
                """
                UPDATE skip_segments
                SET start_ms = ?, end_ms = ?, confidence = ?, reason = ?
                WHERE id = ?
                """,
                (start_ms, end_ms, confidence, reason, segment_id),
            )
            self.db.connection.commit()
            if cursor.rowcount == 0:
                msg = f"No segment found with ID {segment_id}"
                raise RepositoryError(msg)
        except RepositoryError:
            raise
        except Exception as e:
            msg = f"Failed to update segment: {e}"
            raise RepositoryError(msg) from e

    def delete_segment(self, segment_id: int) -> None:
        """Delete a skip segment by ID.

        Args:
            segment_id: ID of the segment to delete

        Raises:
            RepositoryError: If segment not found or deletion fails
        """
        try:
            cursor = self.db.connection.cursor()
            cursor.execute("DELETE FROM skip_segments WHERE id = ?", (segment_id,))
            self.db.connection.commit()
            if cursor.rowcount == 0:
                msg = f"No segment found with ID {segment_id}"
                raise RepositoryError(msg)
        except RepositoryError:
            raise
        except Exception as e:
            msg = f"Failed to delete segment: {e}"
            raise RepositoryError(msg) from e

    def delete_segments_by_episode(self, episode_id: int) -> int:
        """Delete all skip segments for an episode.

        Args:
            episode_id: ID of the episode

        Returns:
            Number of segments deleted

        Raises:
            RepositoryError: If deletion fails
        """
        try:
            cursor = self.db.connection.cursor()
            cursor.execute("DELETE FROM skip_segments WHERE episode_id = ?", (episode_id,))
            self.db.connection.commit()
            return cursor.rowcount
        except Exception as e:
            msg = f"Failed to delete segments by episode: {e}"
            raise RepositoryError(msg) from e
