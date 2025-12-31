"""Dashboard server for DJ Tezz Music Analyzer."""

import json
from pathlib import Path

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

# Paths
BASE_DIR = Path(__file__).parent.parent
CATALOG_PATH = BASE_DIR / "catalog.json"

app = FastAPI(title="DJ Tezz Dashboard")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def load_catalog() -> dict:
    """Load the catalog from disk."""
    if CATALOG_PATH.exists():
        with open(CATALOG_PATH) as f:
            return json.load(f)
    return {"tracks": {}}


@app.get("/")
async def index():
    """Serve the dashboard HTML."""
    return FileResponse(Path(__file__).parent / "index.html")


@app.get("/api/tracks")
async def get_tracks(
    q: str = Query(None, description="Search query"),
    bpm_min: float = Query(None),
    bpm_max: float = Query(None),
    key: str = Query(None, description="Camelot key (e.g., 8A, 10B)"),
    energy_min: float = Query(None),
    energy_max: float = Query(None),
    sort_by: str = Query("title", description="Sort field"),
    sort_order: str = Query("asc", description="asc or desc"),
):
    """Get tracks with optional filtering."""
    catalog = load_catalog()
    tracks = []

    for hash_id, track in catalog.get("tracks", {}).items():
        tier1 = track.get("tier1", {})
        tier3 = track.get("tier3", {})

        # Build searchable text
        searchable = " ".join([
            track.get("title", ""),
            track.get("artist", ""),
            track.get("filename", ""),
            tier1.get("genre", ""),
            tier3.get("subgenre", ""),
            tier3.get("vibe_description", ""),
            " ".join(tier3.get("mood", [])),
            " ".join(tier3.get("similar_artists", [])),
        ]).lower()

        # Apply filters
        if q and q.lower() not in searchable:
            continue

        bpm = tier1.get("bpm")
        if bpm_min and (not bpm or bpm < bpm_min):
            continue
        if bpm_max and (not bpm or bpm > bpm_max):
            continue

        track_key = tier1.get("key_camelot", "")
        if key and track_key != key:
            continue

        energy = tier1.get("energy")
        if energy_min and (not energy or energy < energy_min):
            continue
        if energy_max and (not energy or energy > energy_max):
            continue

        # Build response object
        tracks.append({
            "id": hash_id,
            "title": track.get("title", track.get("filename", "Unknown")),
            "artist": track.get("artist"),
            "filename": track.get("filename"),
            "file_path": track.get("file_path"),
            "duration_sec": track.get("duration_sec"),
            "bpm": tier1.get("bpm"),
            "key": tier1.get("key"),
            "key_camelot": tier1.get("key_camelot"),
            "energy": tier1.get("energy"),
            "danceability": tier1.get("danceability"),
            "subgenre": tier3.get("subgenre"),
            "mood": tier3.get("mood", []),
            "vibe_description": tier3.get("vibe_description"),
            "similar_artists": tier3.get("similar_artists", []),
            "best_setting": tier3.get("best_setting"),
            "mix_notes": tier3.get("mix_notes", {}),
            "has_tier3": bool(tier3),
        })

    # Sort
    def sort_key(t):
        val = t.get(sort_by) or ""
        if isinstance(val, (int, float)):
            return val if sort_order == "asc" else -val
        return str(val).lower()

    reverse = sort_order == "desc"
    if sort_by in ["bpm", "energy", "danceability", "duration_sec"]:
        reverse = sort_order == "desc"
        tracks.sort(key=lambda t: t.get(sort_by) or 0, reverse=reverse)
    else:
        tracks.sort(key=lambda t: str(t.get(sort_by) or "").lower(), reverse=reverse)

    return {"tracks": tracks, "total": len(tracks)}


@app.get("/api/stats")
async def get_stats():
    """Get catalog statistics."""
    catalog = load_catalog()
    tracks = list(catalog.get("tracks", {}).values())

    bpms = [t.get("tier1", {}).get("bpm") for t in tracks if t.get("tier1", {}).get("bpm")]
    keys = {}
    for t in tracks:
        k = t.get("tier1", {}).get("key_camelot")
        if k:
            keys[k] = keys.get(k, 0) + 1

    return {
        "total_tracks": len(tracks),
        "tier1_count": sum(1 for t in tracks if t.get("tier1")),
        "tier2_count": sum(1 for t in tracks if t.get("tier2")),
        "tier3_count": sum(1 for t in tracks if t.get("tier3")),
        "bpm_range": [min(bpms), max(bpms)] if bpms else None,
        "bpm_avg": sum(bpms) / len(bpms) if bpms else None,
        "keys": dict(sorted(keys.items(), key=lambda x: -x[1])[:10]),
    }


@app.get("/api/audio/{track_id}")
async def get_audio(track_id: str):
    """Stream audio file for preview."""
    catalog = load_catalog()
    track = catalog.get("tracks", {}).get(track_id)

    if not track:
        return {"error": "Track not found"}

    file_path = Path(track.get("file_path", ""))
    if not file_path.exists():
        return {"error": "File not found"}

    return FileResponse(
        file_path,
        media_type="audio/wav",
        filename=track.get("filename"),
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
