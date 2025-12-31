# DJ Tezz Music Analyzer

## Overview

A tiered music analysis pipeline for EDM collections that extracts metadata, categorizes tracks, and (future) provides DJ workflow tools.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         CLI Interface                           │
│   djtezz analyze --tier1 --tier2 --tier3 --all                 │
└─────────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                     ▼
┌───────────────┐   ┌─────────────────┐   ┌─────────────────────┐
│   TIER 1      │   │     TIER 2      │   │       TIER 3        │
│   Essentia    │   │     Whisper     │   │    Qwen2-Audio      │
│   (Fast)      │   │   (Medium)      │   │      (Rich)         │
│               │   │                 │   │                     │
│ - BPM         │   │ - Lyrics        │   │ - Vibe description  │
│ - Key         │   │ - Has vocals?   │   │ - Sub-genre detail  │
│ - Energy      │   │ - Language      │   │ - Similar artists   │
│ - Genre       │   │                 │   │ - Mix suggestions   │
│ - Danceability│   │                 │   │ - Best setting      │
│ - Loudness    │   │                 │   │ - Instruments       │
└───────┬───────┘   └────────┬────────┘   └──────────┬──────────┘
        │                    │                       │
        └────────────────────┼───────────────────────┘
                             ▼
                   ┌───────────────────┐
                   │   catalog.json    │
                   │   (Track Database)│
                   └─────────┬─────────┘
                             │
              ┌──────────────┼──────────────┐
              ▼              ▼              ▼
        ┌──────────┐  ┌────────────┐  ┌──────────┐
        │   CLI    │  │ Dashboard  │  │ Rekordbox│
        │  Query   │  │   (Web)    │  │  Export  │
        └──────────┘  └────────────┘  └──────────┘
```

## CLI Commands

### Analyze

```bash
# Run specific tiers
djtezz analyze --tier1                    # Essentia only (fast)
djtezz analyze --tier2                    # Whisper only
djtezz analyze --tier3                    # Qwen2-Audio only
djtezz analyze --tier1 --tier2            # Essentia + Whisper
djtezz analyze --all                      # All tiers

# Options
djtezz analyze --all --path ./my-tracks   # Specific folder
djtezz analyze --all --force              # Re-analyze everything
djtezz analyze --tier1 --new-only         # Only unanalyzed tracks
djtezz analyze --tier3 --gpu-id 0         # Specify GPU
```

### Query

```bash
# Search and filter
djtezz search "melodic techno"
djtezz search --bpm 120-128 --key Am
djtezz search --energy high --mood euphoric
djtezz list --sort-by bpm
```

### Export

```bash
# Export to DJ software
djtezz export --rekordbox --output /Volumes/USB
djtezz export --playlist "peak-time" --rekordbox
```

## Data Schema

### catalog.json

```json
{
  "version": "1.0",
  "last_updated": "2025-12-30T12:00:00Z",
  "tracks": {
    "sha256hash": {
      "file_path": "/path/to/track.mp3",
      "filename": "track.mp3",
      "artist": "Artist Name",
      "title": "Track Title",
      "duration_sec": 245,
      "file_size_mb": 12.4,

      "tier1": {
        "analyzed_at": "2025-12-30T12:00:00Z",
        "bpm": 128.0,
        "key": "Am",
        "key_camelot": "8A",
        "energy": 0.78,
        "danceability": 0.85,
        "loudness_db": -6.2,
        "genre": "house",
        "genre_confidence": 0.89
      },

      "tier2": {
        "analyzed_at": "2025-12-30T12:30:00Z",
        "has_vocals": true,
        "lyrics": "Feel the rhythm...",
        "language": "en",
        "vocal_percentage": 0.35
      },

      "tier3": {
        "analyzed_at": "2025-12-30T14:00:00Z",
        "subgenre": "melodic progressive house",
        "mood": ["euphoric", "uplifting", "dreamy"],
        "energy_description": "peak-time anthem",
        "instruments": ["synth pad", "piano", "kick", "hi-hats"],
        "similar_artists": ["Lane 8", "Ben Bohmer", "Tinlicker"],
        "best_setting": "festival sunset slot",
        "vibe_description": "Euphoric progressive house with lush pads and emotional piano hooks. Perfect for golden hour moments.",
        "mix_notes": {
          "intro_bars": 16,
          "outro_bars": 16,
          "breakdown_at_sec": 142,
          "drop_at_sec": 174,
          "best_mix_in": "Mix in during intro, blend over 32 bars",
          "best_mix_out": "Let outro play, bring next track in at drop"
        }
      }
    }
  }
}
```

## Project Structure

```
dj-tezz-all-music/
├── djtezz/
│   ├── __init__.py
│   ├── cli.py                 # Click CLI entry point
│   ├── config.py              # Settings, paths
│   ├── catalog.py             # Track database operations
│   │
│   ├── analyzers/
│   │   ├── __init__.py
│   │   ├── base.py            # Base analyzer class
│   │   ├── tier1_essentia.py  # Essentia analysis
│   │   ├── tier2_whisper.py   # Whisper transcription
│   │   └── tier3_qwen.py      # Qwen2-Audio analysis
│   │
│   ├── exporters/
│   │   ├── __init__.py
│   │   ├── rekordbox.py       # pyrekordbox integration
│   │   └── serato.py          # Serato tags (future)
│   │
│   └── utils/
│       ├── __init__.py
│       ├── audio.py           # Audio file utilities
│       └── hash.py            # File hashing
│
├── dashboard/                  # Future: web UI
│   └── (backlog)
│
├── catalog.json               # Track database
├── pyproject.toml             # Dependencies
├── README.md
└── SPEC.md                    # This file
```

## Dependencies

```toml
[project]
dependencies = [
    "click>=8.0",           # CLI framework
    "essentia-tensorflow",  # Tier 1 analysis
    "faster-whisper",       # Tier 2 transcription
    "transformers",         # Tier 3 Qwen2-Audio
    "torch",                # GPU acceleration
    "mutagen",              # Audio metadata reading
    "rich",                 # Pretty terminal output
    "pyrekordbox",          # Rekordbox export
]
```

## Backlog / Future Features

### Dashboard (Priority: High)
- [ ] Web UI to browse/filter tracks
- [ ] Audio waveform display
- [ ] Play preview in browser
- [ ] Visual BPM/key grid (Camelot wheel)
- [ ] Drag tracks to create playlists

### Mix Assistant (Priority: Medium)
- [ ] Suggest compatible tracks (BPM ±3, harmonic key)
- [ ] Show optimal blend points
- [ ] Generate set suggestions based on energy curve
- [ ] "Journey builder" - warm-up to peak to cooldown

### Smart Features (Priority: Low)
- [ ] Auto-cue point detection
- [ ] Phrase detection for mix points
- [ ] Duplicate detection (same track, different files)
- [ ] "Sounds like" similarity search

### Integrations (Priority: Low)
- [ ] Sync with Spotify/Beatport for additional metadata
- [ ] Discord bot for crew to browse collection
- [ ] Mobile companion app

## Hardware Requirements

| Tier | GPU VRAM | Time per Track |
|------|----------|----------------|
| 1 (Essentia) | CPU or 2GB | 2-5 sec |
| 2 (Whisper large-v3) | 6GB | 15-30 sec |
| 3 (Qwen2-Audio) | 10GB | 60-120 sec |

RTX 3080 (10-12GB) can run all tiers.

## Usage Examples

```bash
# Initial setup - fast analysis of everything
djtezz analyze --tier1

# Overnight - rich analysis
djtezz analyze --tier2 --tier3

# Find tracks for a set
djtezz search --bpm 124-128 --key Am,Cm --energy high

# Export to USB for gig
djtezz export --rekordbox --playlist "saturday-set" --output /Volumes/DJ_USB
```
