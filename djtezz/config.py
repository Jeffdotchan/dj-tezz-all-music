"""Configuration and settings."""

from pathlib import Path

# Audio file extensions to scan
AUDIO_EXTENSIONS = {".mp3", ".wav", ".flac", ".aiff", ".aif", ".m4a", ".ogg", ".wma", ".aac"}

# Default paths
DEFAULT_MUSIC_PATH = Path(__file__).parent.parent
CATALOG_PATH = DEFAULT_MUSIC_PATH / "catalog.json"

# Camelot wheel mapping for harmonic mixing
KEY_TO_CAMELOT = {
    "C major": "8B", "A minor": "8A",
    "G major": "9B", "E minor": "9A",
    "D major": "10B", "B minor": "10A",
    "A major": "11B", "F# minor": "11A",
    "E major": "12B", "C# minor": "12A",
    "B major": "1B", "G# minor": "1A",
    "F# major": "2B", "D# minor": "2A",
    "Db major": "3B", "Bb minor": "3A",
    "Ab major": "4B", "F minor": "4A",
    "Eb major": "5B", "C minor": "5A",
    "Bb major": "6B", "G minor": "6A",
    "F major": "7B", "D minor": "7A",
}

# Simplified key mapping (essentia output -> standard)
KEY_SIMPLIFY = {
    "C": "C major", "Cm": "C minor",
    "C#": "C# major", "C#m": "C# minor",
    "Db": "Db major", "Dbm": "Db minor",
    "D": "D major", "Dm": "D minor",
    "D#": "D# major", "D#m": "D# minor",
    "Eb": "Eb major", "Ebm": "Eb minor",
    "E": "E major", "Em": "E minor",
    "F": "F major", "Fm": "F minor",
    "F#": "F# major", "F#m": "F# minor",
    "Gb": "Gb major", "Gbm": "Gb minor",
    "G": "G major", "Gm": "G minor",
    "G#": "G# major", "G#m": "G# minor",
    "Ab": "Ab major", "Abm": "Ab minor",
    "A": "A major", "Am": "A minor",
    "A#": "A# major", "A#m": "A# minor",
    "Bb": "Bb major", "Bbm": "Bb minor",
    "B": "B major", "Bm": "B minor",
}

# Tier 3 Qwen2-Audio prompt
QWEN_ANALYSIS_PROMPT = """Analyze this EDM/electronic music track and provide a JSON response with:
{
  "subgenre": "specific subgenre (e.g., 'melodic techno', 'progressive house', 'deep house')",
  "mood": ["list", "of", "mood", "words"],
  "energy_description": "warm-up / building / peak-time / cooldown",
  "instruments": ["detected", "instruments"],
  "similar_artists": ["artist1", "artist2", "artist3"],
  "best_setting": "where this track fits best (club, festival, afterparty, etc.)",
  "vibe_description": "2-3 sentence description of the track's vibe and feel",
  "mix_notes": {
    "best_mix_in": "suggestion for mixing into this track",
    "best_mix_out": "suggestion for mixing out of this track"
  }
}

Only respond with valid JSON, no other text."""
