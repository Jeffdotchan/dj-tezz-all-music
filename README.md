# DJ Tezz Music Analyzer

A tiered music analysis pipeline for EDM collections. Extracts BPM, key, energy, mood, and rich semantic descriptions to help with DJ workflows.

## Quick Start

```bash
# Install base package
pip install -e .

# Install specific tiers
pip install -e ".[tier1]"      # Essentia (BPM, key, energy)
pip install -e ".[tier2]"      # Whisper (vocals, lyrics)
pip install -e ".[tier3]"      # Qwen2-Audio (rich descriptions)
pip install -e ".[all]"        # Everything
```

## Usage

### Analyze Tracks

```bash
# Fast analysis (Essentia) - BPM, key, energy
djtezz analyze --tier1

# Add vocal detection (Whisper)
djtezz analyze --tier2

# Rich AI descriptions (Qwen2-Audio) - run overnight
djtezz analyze --tier3

# Run all tiers
djtezz analyze --all

# Options
djtezz analyze --tier1 --path ./my-folder   # Specific folder
djtezz analyze --tier1 --force              # Re-analyze all
djtezz analyze --tier1 --new-only           # Only new tracks
```

### Search & Filter

```bash
djtezz search "melodic"                    # Text search
djtezz search --bpm 124-128               # BPM range
djtezz search --key Am,Cm                 # Harmonic keys
djtezz search --energy 0.7-1.0            # High energy
djtezz search --vocals                    # Only vocal tracks
```

### Find Compatible Tracks

```bash
djtezz compatible "track_name"            # Find mixable tracks
djtezz compatible "track" --bpm-tolerance 5
```

### View Track Details

```bash
djtezz show "track_name"
djtezz stats
```

## Analysis Tiers

| Tier | Tool | Speed | Output |
|------|------|-------|--------|
| 1 | Essentia | ~3 sec/track | BPM, key, energy, danceability |
| 2 | Whisper | ~20 sec/track | Vocals, lyrics, language |
| 3 | Qwen2-Audio | ~90 sec/track | Subgenre, mood, vibe, mix notes |

## Hardware Requirements

- **Tier 1**: CPU or any GPU
- **Tier 2**: 6GB+ VRAM (RTX 2060+)
- **Tier 3**: 10GB+ VRAM (RTX 3080+)

## Roadmap

- [ ] Web dashboard for browsing
- [ ] Rekordbox USB export
- [ ] Mix transition suggestions
- [ ] Set builder with energy curves
