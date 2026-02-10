# UnrealityTV — Project Plan

Automatically detect and skip repetitive/unwanted segments in reality TV shows during Plex playback.

Based on research in [`docs/research/scene-detection-approaches.md`](research/scene-detection-approaches.md).

---

## How to Use This Plan

Each task below is designed to be **self-contained** and **small enough for a single LLM coding session**. Tasks within a phase are ordered — complete them sequentially. Phases themselves have dependencies noted at the top of each section.

**Task format:**
- **Scope**: What files to create/modify
- **Inputs**: What the task receives (prior task outputs, libraries, etc.)
- **Outputs**: What the task must produce (files, tests passing, etc.)
- **Acceptance criteria**: How to verify the task is done

---

## Phase 0: Project Scaffolding

> **Dependencies**: None — start here.

### Task 0.1 — Python Project Structure

**Goal**: Create the basic Python package layout with `pyproject.toml`.

**Scope**: Create these files:
```
pyproject.toml
src/unrealitytv/__init__.py
src/unrealitytv/cli.py
src/unrealitytv/config.py
tests/__init__.py
tests/conftest.py
.gitignore
```

**Details**:
- Use `pyproject.toml` with `[build-system]` using `hatchling` or `setuptools`
- Project name: `unrealitytv`
- Python requirement: `>=3.10`
- Add initial dependencies: `click`, `pydantic`, `pydantic-settings`
- Add dev dependencies: `pytest`, `ruff`
- In `cli.py`: create a minimal Click CLI group with `--version` and `--config` options
- In `config.py`: create a Pydantic `Settings` class with fields:
  - `plex_url: str = "http://localhost:32400"`
  - `plex_token: str = ""`
  - `watch_dir: Path = Path(".")`
  - `database_path: Path = Path("unrealitytv.db")`
  - `gpu_enabled: bool = False`
- In `.gitignore`: standard Python ignores (`.venv`, `__pycache__`, `*.egg-info`, `.ruff_cache`, `dist/`)

**Acceptance criteria**:
- [ ] `pip install -e ".[dev]"` succeeds
- [ ] `unrealitytv --version` prints a version string
- [ ] `ruff check src/ tests/` passes with no errors
- [ ] `pytest` runs (0 tests collected is OK at this point)

---

### Task 0.2 — Database Schema

**Goal**: Create the SQLite database layer using plain `sqlite3` with migration support.

**Scope**: Create these files:
```
src/unrealitytv/db.py
src/unrealitytv/migrations/001_initial.sql
tests/test_db.py
```

**Details**:
- In `db.py`: create a `Database` class that:
  - Takes a `Path` to the SQLite file in its constructor
  - Has an `initialize()` method that runs all migration SQL files in order
  - Tracks applied migrations in a `_migrations` table
  - Exposes a `connection` property for raw access
- In `001_initial.sql`, create these tables:
  ```sql
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
  ```

**Inputs**: `db.py` imports only stdlib `sqlite3` and `pathlib`

**Acceptance criteria**:
- [ ] `Database("test.db").initialize()` creates all tables
- [ ] Running `initialize()` twice is idempotent (no errors)
- [ ] Tests in `test_db.py` cover: creation, idempotency, inserting a row into each table, and querying it back
- [ ] `ruff check` and `pytest` pass

---

### Task 0.3 — Data Models

**Goal**: Define Pydantic models for the core domain objects used throughout the project.

**Scope**: Create these files:
```
src/unrealitytv/models.py
tests/test_models.py
```

**Details**:
- Define these Pydantic `BaseModel` classes:

```python
class Episode:
    file_path: Path
    show_name: str
    season: int | None
    episode: int | None
    duration_ms: int | None

class SkipSegment:
    start_ms: int
    end_ms: int
    segment_type: Literal["recap", "preview", "repeated_establishing_shot", "flashback", "filler"]
    confidence: float  # 0.0 - 1.0
    reason: str

class AnalysisResult:
    episode: Episode
    segments: list[SkipSegment]

class SceneBoundary:
    start_ms: int
    end_ms: int
    scene_index: int
```

- Add a `to_json()` method on `AnalysisResult` that outputs the skip-segment JSON format from the research doc
- Add a `from_json(path: Path)` classmethod on `AnalysisResult` to load from file
- Add validation: `start_ms < end_ms`, `0.0 <= confidence <= 1.0`

**Acceptance criteria**:
- [ ] Models can be instantiated and serialized to/from JSON
- [ ] Validation rejects `start_ms >= end_ms` and `confidence > 1.0`
- [ ] Round-trip test: create `AnalysisResult` → `to_json()` → `from_json()` → compare
- [ ] `ruff check` and `pytest` pass

---

### Task 0.4 — Episode Filename Parser

**Goal**: Parse show name, season, and episode number from common media file naming conventions.

**Scope**: Create these files:
```
src/unrealitytv/parsers.py
tests/test_parsers.py
```

**Details**:
- Create a function `parse_episode(file_path: Path) -> Episode`
- Support these naming formats (regex-based):
  - `Show.Name.S01E05.720p.mkv` → show="Show Name", season=1, episode=5
  - `Show Name - S01E05 - Episode Title.mp4` → show="Show Name", season=1, episode=5
  - `Show Name - 1x05 - Title.mkv` → show="Show Name", season=1, episode=5
  - `Show.Name.2024.S01E05.mkv` → show="Show Name", season=1, episode=5
- Replace dots with spaces in show names (but not in file extensions)
- Return `None` for season/episode if pattern doesn't match (don't crash)

**Acceptance criteria**:
- [ ] All four naming formats above parse correctly
- [ ] Unknown format returns an `Episode` with `season=None, episode=None`
- [ ] Tests cover at least 8 different filenames
- [ ] `ruff check` and `pytest` pass

---

### Task 0.5 — CLI Subcommands (Stubs)

**Goal**: Wire up the CLI with stub subcommands that will be implemented in later phases.

**Scope**: Modify `src/unrealitytv/cli.py`

**Details**:
- Add these Click subcommands to the CLI group:
  - `analyze` — Takes a file path argument. Prints "Analysis not yet implemented" for now. Will later run the full pipeline.
  - `scan` — Takes a directory path argument. Prints "Scanner not yet implemented". Will later watch for new files.
  - `status` — No arguments. Connects to the database (from config) and prints episode count and segment count.
  - `inject` — Takes a file path argument. Prints "Marker injection not yet implemented". Will later push markers to Plex.
- The `status` command should actually work — it should use `Database` to query counts.
- All commands should load config via `Settings`.

**Acceptance criteria**:
- [ ] `unrealitytv analyze somefile.mkv` prints the stub message
- [ ] `unrealitytv scan /some/dir` prints the stub message
- [ ] `unrealitytv status` prints episode/segment counts from DB (0/0 for empty DB)
- [ ] `unrealitytv inject somefile.mkv` prints the stub message
- [ ] `ruff check` and `pytest` pass (add a test that invokes each command via Click's `CliRunner`)

---

## Phase 1: MVP — Transcript-Based Recap/Preview Detection

> **Dependencies**: Phase 0 complete.
>
> This is the highest-value, lowest-complexity feature. Detect "Previously on..." and "Coming up..." segments using speech-to-text.

### Task 1.1 — Audio Extraction

**Goal**: Extract the audio track from a video file to a temporary WAV file using FFmpeg.

**Scope**: Create these files:
```
src/unrealitytv/audio/extract.py
src/unrealitytv/audio/__init__.py
tests/test_audio_extract.py
```

**Details**:
- Create function `extract_audio(video_path: Path, output_path: Path | None = None) -> Path`
- Use `subprocess.run` to call FFmpeg: `ffmpeg -i <input> -vn -acodec pcm_s16le -ar 16000 -ac 1 <output>`
  - `-vn`: no video
  - `-ar 16000`: 16kHz sample rate (required by Whisper)
  - `-ac 1`: mono
- If `output_path` is None, use `tempfile.NamedTemporaryFile` with `.wav` suffix
- Raise a clear `RuntimeError` if FFmpeg is not found or returns non-zero
- Also create `get_duration_ms(video_path: Path) -> int` using `ffprobe`

**Acceptance criteria**:
- [ ] Function raises `RuntimeError` with helpful message when FFmpeg is missing
- [ ] Function raises `FileNotFoundError` for non-existent input file
- [ ] Test mocks `subprocess.run` to verify correct FFmpeg command is built
- [ ] `get_duration_ms` parses ffprobe JSON output correctly (mock test)
- [ ] `ruff check` and `pytest` pass

---

### Task 1.2 — Whisper Transcription Wrapper

**Goal**: Transcribe audio using `faster-whisper` and return timestamped segments.

**Scope**: Create these files:
```
src/unrealitytv/audio/transcribe.py
tests/test_transcribe.py
```

**Details**:
- Add `faster-whisper` to project dependencies in `pyproject.toml`
- Create a class `Transcriber`:
  - `__init__(self, model_size: str = "base", device: str = "cpu", compute_type: str = "int8")`
  - Lazily load the `WhisperModel` on first use
  - Method `transcribe(audio_path: Path) -> list[TranscriptSegment]`
- Define `TranscriptSegment` as a Pydantic model:
  ```python
  class TranscriptSegment(BaseModel):
      start_ms: int
      end_ms: int
      text: str
  ```
- Map `faster-whisper` segment output to `TranscriptSegment` list (multiply timestamps by 1000 for ms)
- Handle the case where `faster-whisper` is not installed: raise `ImportError` with install instructions

**Acceptance criteria**:
- [ ] `Transcriber` can be instantiated without loading the model
- [ ] `transcribe()` returns a `list[TranscriptSegment]` with correct field types
- [ ] Test mocks the Whisper model to avoid needing actual model weights
- [ ] Missing `faster-whisper` import raises a clear error message
- [ ] `ruff check` and `pytest` pass

---

### Task 1.3 — Keyword Pattern Matching for Recap/Preview

**Goal**: Scan a transcript for patterns that indicate recap or preview segments.

**Scope**: Create these files:
```
src/unrealitytv/detectors/transcript_detector.py
src/unrealitytv/detectors/__init__.py
tests/test_transcript_detector.py
```

**Details**:
- Create function `detect_recap_preview(segments: list[TranscriptSegment]) -> list[SkipSegment]`
- Define keyword patterns (case-insensitive regex):
  - **Recap indicators**: `"previously on"`, `"last time on"`, `"when we left off"`, `"if you remember"`, `"let's take a look back"`
  - **Preview indicators**: `"coming up"`, `"next time on"`, `"stay tuned"`, `"on the next episode"`, `"still to come"`
- Logic:
  1. Find transcript segments containing a keyword match
  2. The **recap** keyword anchor defines the start of a recap segment
  3. Extend the segment to include surrounding transcript segments until there's a gap of >10 seconds without speech (configurable)
  4. The **preview** keyword anchor defines the start of a preview segment — extend to end of episode
  5. Recap segments in the first 5 minutes get a confidence boost (+0.1)
  6. Preview segments in the last 5 minutes get a confidence boost (+0.1)
  7. Base confidence: 0.80 for keyword match
- Return `list[SkipSegment]` with `segment_type="recap"` or `"preview"`

**Acceptance criteria**:
- [ ] Detects "Previously on 90 Day Fiance" at timestamp 5s → returns a recap `SkipSegment`
- [ ] Detects "Coming up next" at timestamp 2500s in a 2700s episode → returns a preview `SkipSegment`
- [ ] Confidence is higher for recap at start and preview at end
- [ ] Returns empty list for transcript with no keywords
- [ ] Tests cover at least 6 scenarios (2 recap, 2 preview, 1 none, 1 both)
- [ ] `ruff check` and `pytest` pass

---

### Task 1.4 — Analysis Pipeline (MVP)

**Goal**: Wire together audio extraction → transcription → keyword detection into a single pipeline function.

**Scope**: Create these files:
```
src/unrealitytv/pipeline.py
tests/test_pipeline.py
```

**Details**:
- Create function `analyze_episode(video_path: Path, config: Settings) -> AnalysisResult`
- Pipeline steps:
  1. Parse episode info from filename (`parsers.parse_episode`)
  2. Get video duration (`audio.extract.get_duration_ms`)
  3. Extract audio (`audio.extract.extract_audio`)
  4. Transcribe (`audio.transcribe.Transcriber.transcribe`)
  5. Detect recap/preview (`detectors.transcript_detector.detect_recap_preview`)
  6. Assemble `AnalysisResult`
  7. Clean up temp audio file
- Use a context manager or try/finally to ensure temp file cleanup
- Log each step with Python `logging` at INFO level

**Acceptance criteria**:
- [ ] `analyze_episode` calls each step in order
- [ ] Temp audio file is cleaned up even if an error occurs
- [ ] Returns a valid `AnalysisResult` with `episode` and `segments` populated
- [ ] Test mocks all external dependencies (FFmpeg, Whisper) and verifies the pipeline orchestration
- [ ] `ruff check` and `pytest` pass

---

### Task 1.5 — Wire Up the `analyze` CLI Command

**Goal**: Replace the stub `analyze` command with the real pipeline.

**Scope**: Modify `src/unrealitytv/cli.py`

**Details**:
- The `analyze` command should:
  1. Load `Settings` from config
  2. Initialize `Database` and call `initialize()`
  3. Call `analyze_episode(video_path, config)`
  4. Save the episode and skip segments to the database
  5. Write the `AnalysisResult` JSON to `<video_name>.segments.json` alongside the video file
  6. Print a summary: number of segments found, their types, and time ranges
- Add `--output` option to override where the JSON is written
- Add `--model-size` option (default `"base"`) passed to `Transcriber`

**Acceptance criteria**:
- [ ] `unrealitytv analyze episode.mkv` runs the pipeline and prints results
- [ ] JSON output file is created with correct format
- [ ] Episode and segments are stored in the database
- [ ] `--output` flag works
- [ ] Test uses `CliRunner` with mocked pipeline
- [ ] `ruff check` and `pytest` pass

---

### Task 1.6 — DB Repository Methods

**Goal**: Add CRUD methods to `Database` for episodes and skip segments.

**Scope**: Modify `src/unrealitytv/db.py`, add `tests/test_db_repository.py`

**Details**:
- Add these methods to `Database`:
  - `save_episode(episode: Episode) -> int` — insert or update, return row ID
  - `save_segments(episode_id: int, segments: list[SkipSegment]) -> None` — bulk insert, replacing any existing segments for that episode
  - `get_episode(file_path: Path) -> Episode | None`
  - `get_segments(episode_id: int) -> list[SkipSegment]`
  - `get_all_episodes(show_name: str | None = None) -> list[Episode]`
  - `get_episode_with_segments(file_path: Path) -> AnalysisResult | None`
- Use parameterized queries (no string formatting of SQL)

**Acceptance criteria**:
- [ ] `save_episode` + `get_episode` round-trips correctly
- [ ] `save_segments` replaces old segments (not duplicates)
- [ ] `get_all_episodes` filters by show name when provided
- [ ] `get_episode_with_segments` returns full `AnalysisResult`
- [ ] Tests cover all methods
- [ ] `ruff check` and `pytest` pass

---

## Phase 2: Scene Boundary Detection

> **Dependencies**: Phase 0 complete. Can be done in parallel with Phase 1.

### Task 2.1 — PySceneDetect Integration

**Goal**: Detect scene boundaries in a video file using PySceneDetect's AdaptiveDetector.

**Scope**: Create these files:
```
src/unrealitytv/detectors/scene_detector.py
tests/test_scene_detector.py
```

**Details**:
- Add `scenedetect[opencv]` to project dependencies
- Create function `detect_scenes(video_path: Path) -> list[SceneBoundary]`
- Use `AdaptiveDetector` from PySceneDetect
- Convert the scene list to `list[SceneBoundary]` using the model from Task 0.3
- Add optional parameters: `threshold: float = 3.0`, `min_scene_len_ms: int = 2000`
- Handle import errors gracefully

**Acceptance criteria**:
- [ ] Returns `list[SceneBoundary]` with valid timestamps
- [ ] Respects `min_scene_len_ms` — no scenes shorter than the minimum
- [ ] Test mocks `scenedetect.detect` and verifies correct parameters passed
- [ ] `ruff check` and `pytest` pass

---

### Task 2.2 — TransNetV2 Integration (GPU Path)

**Goal**: Add a GPU-accelerated scene detection path using TransNetV2.

**Scope**: Modify `src/unrealitytv/detectors/scene_detector.py`, add tests

**Details**:
- Add `transnetv2` as an optional dependency in `pyproject.toml` (under `[project.optional-dependencies]` as `gpu`)
- Create function `detect_scenes_transnet(video_path: Path) -> list[SceneBoundary]`
- Add a factory function `get_scene_detector(gpu_enabled: bool)` that returns the appropriate function
- Handle the case where `transnetv2` is not installed

**Acceptance criteria**:
- [ ] `get_scene_detector(gpu_enabled=True)` returns TransNetV2-based detector
- [ ] `get_scene_detector(gpu_enabled=False)` returns PySceneDetect-based detector
- [ ] Missing `transnetv2` falls back to PySceneDetect with a warning
- [ ] `ruff check` and `pytest` pass

---

## Phase 3: Visual Duplicate Detection

> **Dependencies**: Phase 0 and Phase 2 complete.

### Task 3.1 — Frame Extraction

**Goal**: Extract frames from a video at a given interval (default 1 fps) using FFmpeg.

**Scope**: Create these files:
```
src/unrealitytv/visual/extract_frames.py
src/unrealitytv/visual/__init__.py
tests/test_extract_frames.py
```

**Details**:
- Create function `extract_frames(video_path: Path, output_dir: Path, fps: float = 1.0) -> list[tuple[int, Path]]`
  - Returns list of `(timestamp_ms, frame_path)` tuples
- Use FFmpeg: `ffmpeg -i <input> -vf "fps=<fps>" <output_dir>/frame_%06d.jpg`
- Calculate timestamp from frame index: `timestamp_ms = int((frame_index / fps) * 1000)`
- Create `output_dir` if it doesn't exist

**Acceptance criteria**:
- [ ] Correct FFmpeg command is constructed
- [ ] Returns list of `(timestamp_ms, Path)` tuples
- [ ] Test mocks subprocess and filesystem
- [ ] `ruff check` and `pytest` pass

---

### Task 3.2 — Perceptual Hashing

**Goal**: Compute perceptual hashes for extracted frames and store them.

**Scope**: Create these files:
```
src/unrealitytv/visual/hashing.py
tests/test_hashing.py
```

**Details**:
- Add `ImageHash` and `Pillow` to project dependencies
- Create function `compute_phash(frame_path: Path) -> str` — returns hex string of the pHash
- Create function `compute_hashes_batch(frames: list[tuple[int, Path]]) -> list[tuple[int, str]]` — returns `(timestamp_ms, phash_hex)` pairs
- Create function `hamming_distance(hash1: str, hash2: str) -> int`
- Create function `find_duplicates(hashes: list[tuple[int, str]], threshold: int = 8) -> list[tuple[int, int, int]]` — returns `(timestamp1_ms, timestamp2_ms, distance)` for all matches below threshold

**Acceptance criteria**:
- [ ] `compute_phash` returns a hex string
- [ ] `hamming_distance` correctly computes distance between two hashes
- [ ] `find_duplicates` finds matches within threshold, ignores those above
- [ ] Test uses actual small test images (create 2 similar + 1 different)
- [ ] `ruff check` and `pytest` pass

---

### Task 3.3 — FAISS Index for Season-Wide Search

**Goal**: Build and query a FAISS index of frame hashes for finding duplicates across episodes.

**Scope**: Create these files:
```
src/unrealitytv/visual/index.py
tests/test_index.py
```

**Details**:
- Add `faiss-cpu` to project dependencies
- Create class `FrameIndex`:
  - `__init__(self, dimension: int = 64)` — pHash is 64-bit
  - `add_episode(episode_id: int, hashes: list[tuple[int, str]])` — convert hex hashes to binary vectors and add to index
  - `search(query_hash: str, k: int = 5, threshold: int = 8) -> list[Match]` where `Match` has `episode_id`, `timestamp_ms`, `distance`
  - `save(path: Path)` / `load(path: Path)` — persist/restore the index
- Internally convert pHash hex → numpy binary vector for FAISS `IndexFlatL2`
- Track `(episode_id, timestamp_ms)` metadata in a parallel list

**Acceptance criteria**:
- [ ] Can add hashes and search for near-duplicates
- [ ] Save/load round-trip preserves the index
- [ ] Search returns results within threshold and excludes those outside
- [ ] `ruff check` and `pytest` pass

---

### Task 3.4 — Flashback Detector

**Goal**: Use frame hash matches to detect flashback/recap segments (consecutive duplicate frames).

**Scope**: Create these files:
```
src/unrealitytv/detectors/flashback_detector.py
tests/test_flashback_detector.py
```

**Details**:
- Create function `detect_flashbacks(current_episode_id: int, current_hashes: list[tuple[int, str]], index: FrameIndex, min_duration_ms: int = 3000) -> list[SkipSegment]`
- Logic:
  1. For each frame hash in the current episode, search the index
  2. Filter out self-matches (same episode)
  3. Group consecutive matched frames (within 2s gap tolerance)
  4. Groups spanning >= `min_duration_ms` are flagged as flashbacks
  5. Confidence based on average hamming distance (lower distance = higher confidence)
  6. `reason` field: `"phash_match(S{season}E{episode}@{time}s, distance={d})"`

**Acceptance criteria**:
- [ ] Detects a run of 5+ consecutive duplicate frames as a flashback
- [ ] Ignores isolated single-frame matches
- [ ] Confidence scales with match quality
- [ ] `ruff check` and `pytest` pass

---

## Phase 4: Plex Integration — Marker Injection

> **Dependencies**: Phase 0 complete. Phase 1 or 3 for actual segments to inject.

### Task 4.1 — Plex Server Connection

**Goal**: Establish an authenticated connection to a Plex Media Server.

**Scope**: Create these files:
```
src/unrealitytv/plex/connection.py
src/unrealitytv/plex/__init__.py
tests/test_plex_connection.py
```

**Details**:
- Add `plexapi` to project dependencies
- Create class `PlexConnection`:
  - `__init__(self, url: str, token: str)`
  - `connect() -> PlexServer` — validates connection, raises clear error on failure
  - `find_episode(show_name: str, season: int, episode: int) -> Episode | None` — search the Plex library
  - `get_rating_key(show_name: str, season: int, episode: int) -> int | None` — returns the Plex `ratingKey`
- Handle common errors: connection refused, invalid token, show not found

**Acceptance criteria**:
- [ ] Connection errors produce clear error messages
- [ ] `find_episode` searches correct library sections
- [ ] Tests mock `PlexServer` to avoid needing a real Plex instance
- [ ] `ruff check` and `pytest` pass

---

### Task 4.2 — Marker CRUD Operations

**Goal**: Create, read, update, and delete skip markers on Plex episodes.

**Scope**: Create these files:
```
src/unrealitytv/plex/markers.py
tests/test_plex_markers.py
```

**Details**:
- Create class `MarkerManager`:
  - `__init__(self, plex: PlexServer)`
  - `create_marker(rating_key: int, marker_type: str, start_ms: int, end_ms: int) -> None`
    - `marker_type` is one of: `"intro"`, `"credits"`, `"commercial"`
    - Uses `POST :/markers` API endpoint
  - `get_markers(rating_key: int) -> list[dict]` — returns existing markers
  - `delete_markers(rating_key: int) -> None` — removes all custom markers
  - `sync_segments(rating_key: int, segments: list[SkipSegment]) -> None`
    - Maps `SkipSegment.segment_type` to Plex marker types:
      - `"recap"` → `"intro"` (triggers native skip button)
      - `"preview"` → `"credits"`
      - everything else → `"commercial"`
    - Deletes existing markers first, then creates new ones

**Acceptance criteria**:
- [ ] `create_marker` sends correct API request
- [ ] `sync_segments` maps segment types to marker types correctly
- [ ] `sync_segments` deletes old markers before creating new ones
- [ ] Tests mock Plex API calls
- [ ] `ruff check` and `pytest` pass

---

### Task 4.3 — Wire Up the `inject` CLI Command

**Goal**: Replace the `inject` stub with real marker injection.

**Scope**: Modify `src/unrealitytv/cli.py`

**Details**:
- The `inject` command should:
  1. Load `Settings` for Plex URL and token
  2. Look up the episode in the database (by file path)
  3. Connect to Plex and find the matching episode
  4. Inject markers for all skip segments
  5. Print a summary of injected markers
- Add `--dry-run` flag that shows what would be injected without doing it
- Add an `inject-all` subcommand that injects markers for all analyzed episodes in the DB

**Acceptance criteria**:
- [ ] `unrealitytv inject episode.mkv` injects markers
- [ ] `--dry-run` prints markers without injecting
- [ ] Missing Plex config gives a clear error
- [ ] Episode not in DB gives a clear error
- [ ] `ruff check` and `pytest` pass

---

### Task 4.4 — Marker Re-injection Job

**Goal**: Create a job that periodically re-injects markers after Plex reanalysis events.

**Scope**: Create these files:
```
src/unrealitytv/plex/rejector.py
tests/test_reinjector.py
```

**Details**:
- Create function `reinject_all(db: Database, plex: PlexServer) -> dict` that:
  1. Gets all episodes with segments from the DB
  2. For each, checks if markers exist in Plex
  3. If markers are missing, re-injects them
  4. Returns a summary dict: `{"checked": N, "reinjected": M, "errors": []}`
- Create function `needs_reinjection(plex: PlexServer, rating_key: int, segments: list[SkipSegment]) -> bool`
- Add a `reinject` CLI subcommand

**Acceptance criteria**:
- [ ] Only re-injects where markers are actually missing
- [ ] Reports errors without stopping the whole batch
- [ ] CLI subcommand prints the summary
- [ ] `ruff check` and `pytest` pass

---

## Phase 5: Audio Fingerprinting

> **Dependencies**: Phase 0 and Phase 1 complete.

### Task 5.1 — Music/Speech Segmentation

**Goal**: Classify audio segments as speech, music, or noise.

**Scope**: Create these files:
```
src/unrealitytv/audio/segmentation.py
tests/test_segmentation.py
```

**Details**:
- Add `inaSpeechSegmenter` as optional dependency
- Create function `segment_audio(audio_path: Path) -> list[AudioSegment]`
- Define `AudioSegment` model:
  ```python
  class AudioSegment(BaseModel):
      start_ms: int
      end_ms: int
      label: Literal["speech", "music", "noise"]
  ```
- Wrap `inaSpeechSegmenter` output into `AudioSegment` list
- Handle import error with clear message

**Acceptance criteria**:
- [ ] Returns typed `AudioSegment` list
- [ ] Test mocks the segmenter
- [ ] Missing dependency gives clear error
- [ ] `ruff check` and `pytest` pass

---

### Task 5.2 — Audio Fingerprint Storage

**Goal**: Store and query audio fingerprints for repeated music cue detection.

**Scope**: Create these files:
```
src/unrealitytv/audio/fingerprint.py
src/unrealitytv/migrations/002_audio_fingerprints.sql
tests/test_fingerprint.py
```

**Details**:
- Add a new migration creating an `audio_fingerprints` table:
  ```sql
  CREATE TABLE IF NOT EXISTS audio_fingerprints (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      episode_id INTEGER NOT NULL REFERENCES episodes(id),
      start_ms INTEGER NOT NULL,
      end_ms INTEGER NOT NULL,
      fingerprint BLOB NOT NULL,
      label TEXT
  );
  ```
- Create class `FingerprintStore`:
  - `save(episode_id: int, start_ms: int, end_ms: int, fingerprint: bytes, label: str | None)`
  - `find_matches(fingerprint: bytes, threshold: float) -> list[FingerprintMatch]`
- Use `chromaprint` / `pyacoustid` for actual fingerprint computation (add as dependency)
- Create function `fingerprint_segment(audio_path: Path, start_ms: int, end_ms: int) -> bytes`

**Acceptance criteria**:
- [ ] Migration adds the new table without breaking existing ones
- [ ] Can store and retrieve fingerprints
- [ ] `ruff check` and `pytest` pass

---

## Phase 6: CLIP Scene Classification

> **Dependencies**: Phase 0 and Phase 2 complete.

### Task 6.1 — CLIP Model Wrapper

**Goal**: Wrap OpenCLIP for zero-shot scene classification.

**Scope**: Create these files:
```
src/unrealitytv/visual/classifier.py
tests/test_classifier.py
```

**Details**:
- Add `open-clip-torch` as optional dependency (under `gpu` extras)
- Create class `SceneClassifier`:
  - `__init__(self, model_name: str = "ViT-B-32", pretrained: str = "openai")`
  - Lazily load model
  - `classify(frame_path: Path, labels: list[str]) -> list[tuple[str, float]]` — returns `(label, confidence)` pairs sorted by confidence descending
- Default labels (from research):
  ```python
  DEFAULT_LABELS = [
      "a confessional interview with one person talking to camera",
      "an establishing shot of a building exterior",
      "people arguing or having a dramatic confrontation",
      "a recap or flashback sequence with different color grading",
      "an airport or travel scene",
      "a title card or text overlay",
  ]
  ```

**Acceptance criteria**:
- [ ] Classifier loads lazily (no model download on import)
- [ ] Returns labels sorted by confidence
- [ ] Test mocks the CLIP model
- [ ] `ruff check` and `pytest` pass

---

### Task 6.2 — Scene Type Detector

**Goal**: Classify all scenes in an episode and flag skippable types.

**Scope**: Create these files:
```
src/unrealitytv/detectors/scene_type_detector.py
tests/test_scene_type_detector.py
```

**Details**:
- Create function `detect_skippable_scenes(scenes: list[SceneBoundary], frames_dir: Path, classifier: SceneClassifier, skip_types: list[str] | None = None) -> list[SkipSegment]`
- Default `skip_types`: `["establishing shot", "title card", "recap"]`
- For each scene, classify the middle frame
- If top classification matches a skip type with confidence > 0.5, create a `SkipSegment`
- `reason` field: `"clip_classification({label}, confidence={conf})"`

**Acceptance criteria**:
- [ ] Flags scenes matching skip types above confidence threshold
- [ ] Ignores scenes below threshold
- [ ] Custom `skip_types` override works
- [ ] `ruff check` and `pytest` pass

---

## Phase 7: WebSocket Auto-Skip

> **Dependencies**: Phase 4 complete.

### Task 7.1 — Playback Monitor

**Goal**: Monitor Plex playback via WebSocket and detect when a skip segment is reached.

**Scope**: Create these files:
```
src/unrealitytv/plex/monitor.py
tests/test_monitor.py
```

**Details**:
- Create class `PlaybackMonitor`:
  - `__init__(self, plex: PlexServer, db: Database)`
  - `start()` — begins listening via `AlertListener`
  - `stop()` — stops the listener
  - Internal callback processes `playing` events:
    1. Extract `sessionKey` and `viewOffset` from notification
    2. Look up the playing media's file path
    3. Query DB for skip segments for that file
    4. If `viewOffset` is within a skip segment's range, emit a skip event
- Create dataclass `SkipEvent(session_key: str, target_ms: int, segment: SkipSegment)`
- Use a callback pattern: `on_skip: Callable[[SkipEvent], None]`

**Acceptance criteria**:
- [ ] Callback is invoked when playback enters a skip segment
- [ ] Callback is NOT invoked when playback is outside skip segments
- [ ] Monitor can be started and stopped
- [ ] Test mocks `AlertListener`
- [ ] `ruff check` and `pytest` pass

---

### Task 7.2 — Auto-Skip Daemon

**Goal**: Combine playback monitoring with seek commands for automatic skipping.

**Scope**: Create these files:
```
src/unrealitytv/plex/autoskip.py
tests/test_autoskip.py
```

**Details**:
- Create class `AutoSkipDaemon`:
  - `__init__(self, plex: PlexServer, db: Database)`
  - `run()` — blocking. Starts the `PlaybackMonitor` and handles skip events.
  - On `SkipEvent`: find the Plex player session and issue a seek command to `target_ms`
  - Add cooldown: don't skip the same segment twice within 30 seconds (prevents skip loops)
  - Log all skip actions
- Add a `watch` CLI subcommand that runs the daemon

**Acceptance criteria**:
- [ ] Sends seek command when a skip event fires
- [ ] Cooldown prevents repeated skips
- [ ] `watch` CLI command starts the daemon
- [ ] `ruff check` and `pytest` pass

---

## Phase 8: Folder Scanner

> **Dependencies**: Phase 1 complete.

### Task 8.1 — File System Watcher

**Goal**: Watch a directory for new video files and trigger analysis.

**Scope**: Create these files:
```
src/unrealitytv/scanner.py
tests/test_scanner.py
```

**Details**:
- Add `watchdog` to project dependencies
- Create class `FolderScanner`:
  - `__init__(self, watch_dir: Path, extensions: list[str] = [".mkv", ".mp4", ".avi"])`
  - `start(on_new_file: Callable[[Path], None])` — uses `watchdog` to monitor directory
  - `stop()`
  - Ignores files that don't match the extensions list
  - Debounce: wait 5 seconds after last file-system event before calling callback (files may still be copying)
- Wire into the `scan` CLI command:
  1. Start folder scanner
  2. On new file: run `analyze_episode` pipeline
  3. If Plex config is set: auto-inject markers

**Acceptance criteria**:
- [ ] Detects new `.mkv` files in watched directory
- [ ] Ignores non-video files
- [ ] Debounce prevents triggering on partial copies
- [ ] `scan` CLI command starts watching and processes new files
- [ ] `ruff check` and `pytest` pass

---

## Phase 9: Enhanced Pipeline & Polish

> **Dependencies**: Multiple previous phases.

### Task 9.1 — Combined Analysis Pipeline

**Goal**: Integrate all detectors into the full analysis pipeline.

**Scope**: Modify `src/unrealitytv/pipeline.py`

**Details**:
- Update `analyze_episode` to run all available detectors:
  1. Audio extraction
  2. Transcription → keyword detection (Phase 1)
  3. Scene boundary detection (Phase 2)
  4. Frame extraction → hashing → flashback detection (Phase 3)
  5. CLIP scene classification (Phase 6, if available)
  6. Audio segmentation (Phase 5, if available)
- Merge overlapping skip segments from different detectors
- Boost confidence when multiple detectors agree
- Each detector should be optional — if its dependencies aren't installed, skip it with a warning
- Create helper `merge_segments(segments: list[SkipSegment]) -> list[SkipSegment]` that:
  - Merges overlapping segments
  - Takes the highest confidence and concatenates reasons

**Acceptance criteria**:
- [ ] Pipeline runs all available detectors
- [ ] Missing optional detectors are skipped gracefully
- [ ] Overlapping segments are merged correctly
- [ ] Confidence boosting works when detectors agree
- [ ] `ruff check` and `pytest` pass

---

### Task 9.2 — Progress Reporting

**Goal**: Add progress reporting to the CLI for long-running analysis.

**Scope**: Modify `src/unrealitytv/cli.py` and `src/unrealitytv/pipeline.py`

**Details**:
- Add `rich` to project dependencies
- Use `rich.progress` for a progress bar during analysis
- Show steps: "Extracting audio", "Transcribing", "Detecting scenes", etc.
- Add `--quiet` flag to suppress progress output
- Add `--verbose` flag for debug-level logging

**Acceptance criteria**:
- [ ] Progress bar shows during `analyze` command
- [ ] `--quiet` suppresses all non-essential output
- [ ] `--verbose` shows detailed debug logs
- [ ] `ruff check` and `pytest` pass

---

## Summary: Dependency Graph

```
Phase 0 (Scaffolding)
  ├── Phase 1 (MVP: Transcript Detection)
  │     ├── Phase 5 (Audio Fingerprinting)
  │     └── Phase 8 (Folder Scanner)
  ├── Phase 2 (Scene Detection)
  │     ├── Phase 3 (Visual Duplicates)
  │     └── Phase 6 (CLIP Classification)
  └── Phase 4 (Plex Markers)
        └── Phase 7 (WebSocket Auto-Skip)

Phase 9 (Combined Pipeline) ← requires Phases 1-6
```

## Quick Reference: Task Count per Phase

| Phase | Name | Tasks | Estimated Complexity |
|-------|------|-------|---------------------|
| 0 | Scaffolding | 5 | Low |
| 1 | MVP Transcript Detection | 6 | Medium |
| 2 | Scene Boundary Detection | 2 | Low |
| 3 | Visual Duplicate Detection | 4 | Medium |
| 4 | Plex Marker Injection | 4 | Medium |
| 5 | Audio Fingerprinting | 2 | Medium |
| 6 | CLIP Classification | 2 | Medium |
| 7 | WebSocket Auto-Skip | 2 | Medium |
| 8 | Folder Scanner | 1 | Low |
| 9 | Enhanced Pipeline | 2 | Medium |
| **Total** | | **30 tasks** | |
