"""Tests for database layer."""



from unrealitytv.db import Database


class TestDatabase:
    """Test Database class."""

    def test_initialize_creates_tables(self, tmp_db):
        """Test that initialize() creates all tables."""
        db = Database(tmp_db)
        db.initialize()

        cursor = db.connection.cursor()

        # Check that _migrations table exists
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='_migrations'"
        )
        assert cursor.fetchone() is not None

        # Check that episodes table exists
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='episodes'"
        )
        assert cursor.fetchone() is not None

        # Check that skip_segments table exists
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='skip_segments'"
        )
        assert cursor.fetchone() is not None

        # Check that frame_hashes table exists
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='frame_hashes'"
        )
        assert cursor.fetchone() is not None

    def test_initialize_is_idempotent(self, tmp_db):
        """Test that running initialize() twice doesn't error."""
        db = Database(tmp_db)
        db.initialize()
        db.initialize()  # Should not raise

        cursor = db.connection.cursor()
        # Check that tables still exist and are intact
        cursor.execute(
            "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='episodes'"
        )
        assert cursor.fetchone()[0] == 1

    def test_can_insert_into_episodes(self, tmp_db):
        """Test inserting and querying from episodes table."""
        db = Database(tmp_db)
        db.initialize()

        cursor = db.connection.cursor()
        cursor.execute(
            """
            INSERT INTO episodes (file_path, show_name, season, episode, duration_ms)
            VALUES (?, ?, ?, ?, ?)
            """,
            ("/path/to/show.mkv", "Test Show", 1, 5, 3600000),
        )
        db.connection.commit()

        # Query back
        cursor.execute("SELECT show_name, season, episode FROM episodes")
        row = cursor.fetchone()
        assert row == ("Test Show", 1, 5)

    def test_can_insert_into_skip_segments(self, tmp_db):
        """Test inserting into skip_segments table."""
        db = Database(tmp_db)
        db.initialize()

        cursor = db.connection.cursor()

        # Insert episode first
        cursor.execute(
            """
            INSERT INTO episodes (file_path, show_name, season, episode, duration_ms)
            VALUES (?, ?, ?, ?, ?)
            """,
            ("/path/to/show.mkv", "Test Show", 1, 5, 3600000),
        )
        episode_id = cursor.lastrowid
        db.connection.commit()

        # Insert skip segment
        cursor.execute(
            """
            INSERT INTO skip_segments (episode_id, start_ms, end_ms, segment_type, confidence, reason)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (episode_id, 1000, 5000, "recap", 0.95, "Previously on..."),
        )
        db.connection.commit()

        # Query back
        cursor.execute(
            "SELECT segment_type, confidence, reason FROM skip_segments WHERE episode_id = ?",
            (episode_id,),
        )
        row = cursor.fetchone()
        assert row == ("recap", 0.95, "Previously on...")

    def test_can_insert_into_frame_hashes(self, tmp_db):
        """Test inserting into frame_hashes table."""
        db = Database(tmp_db)
        db.initialize()

        cursor = db.connection.cursor()

        # Insert episode first
        cursor.execute(
            """
            INSERT INTO episodes (file_path, show_name, season, episode, duration_ms)
            VALUES (?, ?, ?, ?, ?)
            """,
            ("/path/to/show.mkv", "Test Show", 1, 5, 3600000),
        )
        episode_id = cursor.lastrowid
        db.connection.commit()

        # Insert frame hash
        cursor.execute(
            """
            INSERT INTO frame_hashes (episode_id, timestamp_ms, phash)
            VALUES (?, ?, ?)
            """,
            (episode_id, 1000, "abc123def456"),
        )
        db.connection.commit()

        # Query back
        cursor.execute(
            "SELECT phash FROM frame_hashes WHERE episode_id = ?",
            (episode_id,),
        )
        row = cursor.fetchone()
        assert row == ("abc123def456",)

    def test_connection_property_lazy_loads(self, tmp_db):
        """Test that connection property creates connection on first access."""
        db = Database(tmp_db)
        assert db._connection is None
        conn = db.connection
        assert conn is not None
        assert db._connection is not None

    def test_context_manager(self, tmp_db):
        """Test using Database as context manager."""
        with Database(tmp_db) as db:
            db.initialize()
            cursor = db.connection.cursor()
            cursor.execute(
                "SELECT COUNT(*) FROM sqlite_master WHERE type='table'"
            )
            count = cursor.fetchone()[0]
            assert count >= 3  # At least _migrations and the 3 main tables
