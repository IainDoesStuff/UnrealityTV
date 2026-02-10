# Scene Detection & Segment Skipping: Research

Research into approaches for automatically detecting repetitive/unwanted segments in reality TV shows (e.g. 90 Day Fiance) and skipping them during Plex playback.

## High-Level Architecture

```
Episode Video File
    │
    ▼
┌──────────────────────────────────┐
│  PREPROCESSING PIPELINE          │
│                                  │
│  1. Scene boundary detection     │
│  2. Frame extraction (1 fps)     │
│  3. Visual analysis (parallel):  │
│     - Perceptual hashing         │
│     - CLIP scene classification  │
│     - Near-duplicate search      │
│  4. Audio analysis (parallel):   │
│     - Speech-to-text (Whisper)   │
│     - Music/speech segmentation  │
│     - Audio fingerprinting       │
│  5. Aggregation & decision       │
│     → Output: skip-list JSON     │
└──────────────┬───────────────────┘
               │
               ▼
┌──────────────────────────────────┐
│  PLEX INTEGRATION                │
│                                  │
│  Option A: Marker injection      │
│    POST :/markers API            │
│    → Native "Skip" button in UI  │
│                                  │
│  Option B: WebSocket monitor     │
│    AlertListener + seekTo        │
│    → Auto-skip (LAN only)        │
└──────────────────────────────────┘
```

---

## Part 1: Video Scene Detection

### Scene Boundary Detection

| Tool | Approach | Speed | GPU? | Notes |
|------|----------|-------|------|-------|
| [PySceneDetect](https://github.com/Breakthrough/PySceneDetect) | HSV frame diff (Adaptive/Content/Threshold detectors) | 2-5 min/ep (CPU) | No | Mature, easy to use. AdaptiveDetector best for reality TV. |
| [TransNetV2](https://github.com/soCzech/TransNetV2) | Deep learning shot boundary detection | 30-60s/ep (GPU) | Yes | Most accurate. Detects gradual transitions too. Best choice if GPU available. |
| FFmpeg `scdet` filter | Built-in scene change detection | 1-3 min/ep (CPU) | No | Lightweight, no Python deps. Good for quick passes. |

**Recommendation**: TransNetV2 (GPU) or PySceneDetect AdaptiveDetector (CPU fallback).

```python
# PySceneDetect example
from scenedetect import detect, AdaptiveDetector
scene_list = detect('episode.mp4', AdaptiveDetector())

# TransNetV2 example
from transnetv2 import TransNetV2
model = TransNetV2()
_, preds, _ = model.predict_video("episode.mp4")
scenes = model.predictions_to_scenes(preds)
```

### Perceptual Hashing (Repeated Shot Detection)

For finding the same establishing shot used across episodes, or repeated interview backdrops.

| Tool | Technique | Best For |
|------|-----------|----------|
| [imagehash](https://github.com/JohannesBuchner/imagehash) (`phash`) | DCT-based perceptual hash | Fast near-duplicate frames. Hamming distance <= 8 = match. |
| [videohash](https://github.com/akamhy/videohash) | Whole-clip wavelet hash | Comparing pre-segmented scene clips across episodes. |
| [Meta SSCD](https://github.com/facebookresearch/sscd-copy-detection) | Self-supervised 512-dim descriptors | High-accuracy copy detection. Robust to color grading changes. |

**Strategy**: Two-pass approach. Fast pHash for candidate finding, SSCD for verification. Store descriptors in a [FAISS](https://github.com/facebookresearch/faiss) index for efficient season-wide search.

### Scene Classification (CLIP Zero-Shot)

Classify each scene without any training data by defining text prompts:

```python
import open_clip

labels = [
    "a confessional interview with one person talking to camera",
    "an establishing shot of a building exterior",
    "people arguing or having a dramatic confrontation",
    "a recap or flashback sequence with different color grading",
    "an airport or travel scene",
    "a title card or text overlay",
]

# CLIP computes similarity between frame and each label
# → scene type with highest confidence wins
```

| Model | Speed (GPU) | Speed (CPU) | Notes |
|-------|-------------|-------------|-------|
| [OpenCLIP](https://github.com/mlfoundations/open_clip) ViT-B/32 | ~200 fps | ~3-5 fps | Good default |
| SigLIP 2 | Similar | Similar | Better spatial understanding |

### Flashback / Recap Detection

Reality shows heavily pad runtime with replayed content. Detection approaches:

1. **Frame-level near-duplicate search**: Index all frames at 1fps across a season (pHash or SSCD in FAISS). For each new episode, query the index. Consecutive matches (3-5 seconds) = flashback.
2. **[VCSL](https://github.com/ant-research/VCSL)** (Video Copy Segment Localization): Full pipeline for finding copied segments between videos, including temporal alignment.
3. **"Previously on..." detection**: Combine visual duplicate search on first 5 minutes + Whisper transcript keyword matching.

---

## Part 2: Audio Analysis

### Speech-to-Text

| Tool | Speed | GPU VRAM | Notes |
|------|-------|----------|-------|
| [faster-whisper](https://github.com/SYSTRAN/faster-whisper) | 2-4 min/ep (GPU), 20-45 min (CPU) | ~4-8 GB | CTranslate2 backend. Best default. |
| [WhisperX](https://github.com/m-bain/whisperX) | 70x realtime (GPU) | <8 GB | Adds word-level timestamps + speaker diarization. |

Key transcript patterns to detect:
- `"Previously on..."` → recap segment
- `"Coming up..."` → teaser/preview
- `"When we left off..."` → recap
- Narrator voice (consistent speaker embedding via [pyannote](https://github.com/pyannote/pyannote-audio))

### Music / Speech Segmentation

| Tool | What It Does |
|------|-------------|
| [inaSpeechSegmenter](https://github.com/ina-foss/inaSpeechSegmenter) | CNN-based speech/music/noise classification. Purpose-built for broadcast media. |
| [PANNs](https://github.com/qiuqiangkong/panns_inference) | 527-class audio tagging ("background music", "jingle", "suspense", etc.) |
| [audio-separator](https://github.com/nomadkaraoke/python-audio-separator) | Source separation (isolate music from dialogue). Actively maintained. |

### Audio Fingerprinting (Repeated Music Cues)

Reality shows reuse the same background music/stings/jingles constantly.

| Tool | Speed | Storage | Notes |
|------|-------|---------|-------|
| [Olaf](https://github.com/JorenSix/Olaf) | 500-1200x realtime | LMDB (embedded) | Fastest. C with CLI. Best for bulk processing. |
| [Dejavu](https://github.com/worldveil/dejavu) | Moderate | MySQL/PostgreSQL/SQLite | Pure Python. 96% accuracy at 2s clips. [SQLite fork](https://github.com/bcollazo/dejavu). |
| [Chromaprint/pyacoustid](https://github.com/beetbox/pyacoustid) | Fast | Compact fingerprints | Most established. Good for whole-file ID. |

### Silence / Transition Detection

- `librosa.effects.split` — dynamic threshold silence detection
- `librosa.onset.onset_strength` — spectral flux novelty for any significant audio change
- `librosa.segment.recurrence_matrix` — self-similarity matrix reveals repeated audio segments as off-diagonal stripes

---

## Part 3: Plex Integration

### Current State of Plex Extensibility

The old Plex plugin framework was **deprecated in 2018**. The current approach is standalone services communicating via the Plex HTTP API.

- [python-plexapi](https://github.com/pkkid/python-plexapi) (v4.18.0) — primary Python interface
- PMS exposes WebSocket endpoint for real-time playback events
- New Custom Metadata Providers framework (Dec 2025) — for metadata only, not playback control

### Option A: Plex Marker Injection (Recommended Primary)

Plex's intro/credits skip stores markers in the `taggings` table. The API supports CRUD:

```
POST   :/markers   — Create marker
PUT    :/markers   — Edit marker
DELETE :/markers   — Delete marker
```

Parameters: `ratingKey`, `type` (intro|credits|commercial), `startTimeOffset` (ms), `endTimeOffset` (ms).

```python
from plexapi.server import PlexServer

plex = PlexServer('http://localhost:32400', token)
episode = plex.library.section('TV Shows').get('90 Day Fiance').episode(s=1, e=1)

# Inject a "commercial" marker for a recap segment
plex.query(':/markers', method=plex._session.post, params={
    'ratingKey': episode.ratingKey,
    'type': 'commercial',
    'startTimeOffset': 0,       # start of episode
    'endTimeOffset': 120000     # 2 minutes (recap ends)
})
```

**Pros**: Works on ALL clients (including remote). Triggers native skip button UI. No extra software on clients.
**Cons**: Limited to 3 marker types. Markers get wiped when Plex reanalyzes (need periodic re-injection). Only one intro + one credits marker reliably supported per item.

### Option B: WebSocket Playback Monitor (Auto-Skip)

Like [PlexAutoSkip](https://github.com/mdhiggins/PlexAutoSkip) — a daemon that monitors playback and issues seek commands.

```python
from plexapi.server import PlexServer
from plexapi.alert import AlertListener

plex = PlexServer('http://localhost:32400', token)

def callback(data):
    if data['type'] == 'playing':
        session_key = data['PlaySessionStateNotification'][0]['sessionKey']
        view_offset = int(data['PlaySessionStateNotification'][0]['viewOffset'])
        # Check if current position is in a skip segment
        # If so: issue seekTo via player API

listener = AlertListener(plex, callback)
listener.start()
```

**Pros**: Can skip arbitrary number of segments. Full control over skip logic. Can auto-skip without user interaction.
**Cons**: LAN only (Plex blocks remote seek commands). Requires always-running daemon.

### Option C: Chapter Markers via FFmpeg

Embed chapters in video files for manual navigation:

```bash
ffmpeg -i input.mp4 -i chapters.txt -map_metadata 1 -codec copy output.mp4
```

**Pros**: No external services. Works everywhere. Permanent.
**Cons**: Manual skip only (no auto-skip). Requires remuxing files.

### Existing Projects

| Project | What It Does |
|---------|-------------|
| [PlexAutoSkip](https://github.com/mdhiggins/PlexAutoSkip) | WebSocket-based auto-skip daemon. Supports custom segments via JSON. Maintenance mode. |
| [MarkerEditorForPlex](https://github.com/danrahn/MarkerEditorForPlex) | Web UI for viewing/editing/adding markers. Manipulates Plex DB directly. |
| [bw_plex](https://github.com/Hellowlol/bw_plex) | Audio fingerprint-based intro detection for Plex. |

### Recommended Hybrid Approach

1. **Marker injection via API** as primary — gives native skip buttons everywhere
2. **WebSocket auto-skip** as optional enhancement — for hands-free LAN viewing
3. **Periodic re-injection job** — to restore markers after Plex reanalysis events

---

## Part 4: Performance Budget

### Per-Episode Processing (45 min episode)

| Stage | GPU (RTX 3060+) | CPU Only |
|-------|-----------------|----------|
| Scene boundary detection | 30-60s | 2-5 min |
| Frame extraction (1 fps) | 30-60s | 30-60s |
| pHash computation (2700 frames) | 5-10s | 5-10s |
| SSCD descriptors | 30-60s | 10-20 min |
| CLIP classification | 20-40s | 8-15 min |
| FAISS similarity search | <1s | <1s |
| Whisper transcription | 2-4 min | 20-45 min |
| Audio feature extraction | 1-3 min | 1-3 min |
| **Total** | **~5-10 min** | **~45-90 min** |

### Hardware Requirements

- **Minimum**: 8 GB RAM, 4-core CPU. ~1 hour per episode.
- **Recommended**: 16 GB RAM, NVIDIA GPU 8 GB+ VRAM (RTX 3060+). ~5-10 min per episode.

### Key Optimizations

- Two-pass: fast pHash first, SSCD only on candidates
- ONNX Runtime / OpenVINO for 2-3x CPU speedup on CLIP/SSCD
- Build season index once, query incrementally per episode
- `IndexIVFFlat` or `IndexHNSWFlat` in FAISS for large indices

---

## Part 5: Proposed System Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    UnrealityTV                           │
│                                                         │
│  ┌─────────────┐    ┌──────────────┐    ┌────────────┐ │
│  │  Scanner     │    │  Analyzer    │    │  Plex      │ │
│  │             │    │              │    │  Bridge    │ │
│  │ Watch folder│───▶│ Scene detect │───▶│            │ │
│  │ New episodes│    │ Audio anal.  │    │ Inject     │ │
│  │ Trigger     │    │ Visual match │    │ markers    │ │
│  │ analysis    │    │ Classification│   │ Auto-skip  │ │
│  └─────────────┘    └──────┬───────┘    └────────────┘ │
│                            │                            │
│                     ┌──────▼───────┐                    │
│                     │   Database   │                    │
│                     │              │                    │
│                     │ Frame hashes │                    │
│                     │ SSCD index   │                    │
│                     │ Audio FPs    │                    │
│                     │ Skip segments│                    │
│                     └──────────────┘                    │
└─────────────────────────────────────────────────────────┘
```

### Components

1. **Scanner** — Watches a folder for new episodes. Triggers analysis pipeline.
2. **Analyzer** — Runs detection pipeline. Outputs skip-segment JSON per episode.
3. **Database** — Stores frame hashes, audio fingerprints, SSCD/FAISS index, and skip decisions.
4. **Plex Bridge** — Injects markers via API + optional WebSocket auto-skip daemon.

### Skip Segment Output Format

```json
{
  "file": "90.Day.Fiance.S10E05.mkv",
  "duration_ms": 2700000,
  "segments": [
    {
      "start_ms": 0,
      "end_ms": 135000,
      "type": "recap",
      "confidence": 0.94,
      "reason": "visual_duplicate + transcript_match('Previously on')"
    },
    {
      "start_ms": 892000,
      "end_ms": 910000,
      "type": "repeated_establishing_shot",
      "confidence": 0.87,
      "reason": "phash_match(S10E02@1200s, distance=4)"
    },
    {
      "start_ms": 2580000,
      "end_ms": 2700000,
      "type": "preview",
      "confidence": 0.91,
      "reason": "transcript_match('Coming up') + visual_duplicate"
    }
  ]
}
```

---

## Recommended Implementation Order

1. **MVP: Recap/preview detection** — Whisper transcription + keyword matching for "Previously on" / "Coming up". Lowest complexity, highest value.
2. **Scene boundary detection** — PySceneDetect or TransNetV2. Foundation for everything else.
3. **Visual duplicate detection** — pHash index across season. Catches flashbacks and repeated establishing shots.
4. **Plex marker injection** — Wire up skip segments to Plex API markers.
5. **Audio fingerprinting** — Detect recurring music cues for finer-grained segment classification.
6. **CLIP scene classification** — Label scene types (confessional, drama, establishing) for user-configurable skip rules.
7. **WebSocket auto-skip** — Optional daemon for hands-free skipping.

## Key Libraries Summary

| Library | Purpose | Install |
|---------|---------|---------|
| PySceneDetect | Scene boundaries | `pip install scenedetect[opencv]` |
| TransNetV2 | Scene boundaries (ML) | `pip install transnetv2` |
| imagehash | Perceptual hashing | `pip install ImageHash` |
| SSCD | Copy detection | torch model from FB repo |
| FAISS | Similarity search | `pip install faiss-cpu` or `faiss-gpu` |
| OpenCLIP | Zero-shot classification | `pip install open-clip-torch` |
| faster-whisper | Transcription | `pip install faster-whisper` |
| WhisperX | Transcription + diarization | `pip install whisperx` |
| pyannote.audio | Speaker diarization | `pip install pyannote.audio` |
| inaSpeechSegmenter | Speech/music/noise | `pip install inaSpeechSegmenter` |
| Olaf | Audio fingerprinting | C binary, CLI |
| Dejavu | Audio fingerprinting | `pip install dejavu` |
| librosa | Audio features | `pip install librosa` |
| python-plexapi | Plex API client | `pip install plexapi` |
