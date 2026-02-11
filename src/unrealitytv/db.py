# src/unrealitytv/db.py
import sqlite3
from pathlib import Path

class Database:
    """SQLite database manager with migration support"""

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.connection = None
        self._migrations_applied = set()

    def initialize(self):
        """Run all migration SQL files in order"""
        migrations_dir = self.db_path.parent / "migrations"
        
        # Create migrations table if it doesn"t exist
        self.connection = sqlite3.connect(self.db_path)
        self.connection.execute("""
            CREATE TABLE IF NOT EXISTS _migrations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE
            )
        """.format(self.db_path))
        self.connection.commit()
        
        # Apply any unapplied migrations
        for migration_file in sorted(migrations_dir.glob("*.sql")):
            name = migration_file.name
            
            # Check if this migration has already been applied
            cursor = self.connection.execute("SELECT * FROM _migrations WHERE name = ?", (name,))
            if cursor.fetchone():
                continue
            
            # Run the migration
            with open(migration_file, "r") as f:
                sql = f.read()
            self.connection.executescript(sql)
            
            # Record that this migration was applied
            self.connection.execute("INSERT INTO _migrations (name) VALUES (?)", (name,))
            self.connection.commit()
            
        return self

    @property
def connection(self):
        """Get database connection"""
        if self.connection is None:
            self.connection = sqlite3.connect(self.db_path)
        return self.connection