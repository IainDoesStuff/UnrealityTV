CREATE TABLE IF NOT EXISTS episodes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_path TEXT UNIQUE NOT NULL,
    show_name TEXT NOT NULL,
    season INTEGER,
    episode INTEGER,
    duration_ms INTEGER,
    analyzed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS skip_segments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    episode_id INTEGER NOT NULL REFERENCES episodes(id),
    start_ms INTEGER NOT NULL,
    end_ms INTEGER NOT NULL,
    segment_type TEXT NOT NULL,
    confidence REAL NOT NULL,
    reason TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS frame_hashes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    episode_id INTEGER NOT NULL REFERENCES episodes(id),
    timestamp_ms INTEGER NOT NULL,
    phash TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_frame_hashes_phash ON frame_hashes(phash);
CREATE INDEX IF NOT EXISTS idx_skip_segments_episode ON skip_segments(episode_id);
