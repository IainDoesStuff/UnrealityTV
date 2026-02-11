"""SQLite database manager with migration support."""

import sqlite3
from pathlib import Path


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
