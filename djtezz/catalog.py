"""Track catalog/database operations."""

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from .config import CATALOG_PATH


class Catalog:
    """Manages the track database."""

    def __init__(self, path: Path = CATALOG_PATH):
        self.path = path
        self.data = self._load()

    def _load(self) -> dict:
        """Load catalog from disk."""
        if self.path.exists():
            with open(self.path, "r") as f:
                return json.load(f)
        return {
            "version": "1.0",
            "last_updated": None,
            "tracks": {},
        }

    def save(self) -> None:
        """Save catalog to disk."""
        self.data["last_updated"] = datetime.utcnow().isoformat() + "Z"
        with open(self.path, "w") as f:
            json.dump(self.data, f, indent=2)

    def get_track(self, track_hash: str) -> dict | None:
        """Get a track by its hash."""
        return self.data["tracks"].get(track_hash)

    def set_track(self, track_hash: str, track_data: dict) -> None:
        """Set/update a track."""
        self.data["tracks"][track_hash] = track_data

    def update_tier(self, track_hash: str, tier: str, tier_data: dict) -> None:
        """Update a specific tier for a track."""
        if track_hash not in self.data["tracks"]:
            raise KeyError(f"Track {track_hash} not found in catalog")

        tier_data["analyzed_at"] = datetime.utcnow().isoformat() + "Z"
        self.data["tracks"][track_hash][tier] = tier_data

    def has_tier(self, track_hash: str, tier: str) -> bool:
        """Check if a track has been analyzed for a specific tier."""
        track = self.get_track(track_hash)
        if not track:
            return False
        return tier in track and track[tier] is not None

    def get_all_tracks(self) -> list[dict]:
        """Get all tracks as a list."""
        return list(self.data["tracks"].values())

    def search(
        self,
        query: str | None = None,
        bpm_min: float | None = None,
        bpm_max: float | None = None,
        keys: list[str] | None = None,
        energy_min: float | None = None,
        energy_max: float | None = None,
        genre: str | None = None,
        has_vocals: bool | None = None,
    ) -> list[dict]:
        """Search tracks with filters."""
        results = []

        for track in self.get_all_tracks():
            tier1 = track.get("tier1", {})
            tier2 = track.get("tier2", {})
            tier3 = track.get("tier3", {})

            # Text query (searches multiple fields)
            if query:
                query_lower = query.lower()
                searchable = " ".join([
                    track.get("artist", ""),
                    track.get("title", ""),
                    track.get("filename", ""),
                    tier1.get("genre", ""),
                    tier3.get("subgenre", ""),
                    tier3.get("vibe_description", ""),
                    " ".join(tier3.get("mood", [])),
                ]).lower()
                if query_lower not in searchable:
                    continue

            # BPM filter
            if bpm_min is not None or bpm_max is not None:
                bpm = tier1.get("bpm")
                if bpm is None:
                    continue
                if bpm_min is not None and bpm < bpm_min:
                    continue
                if bpm_max is not None and bpm > bpm_max:
                    continue

            # Key filter
            if keys:
                track_key = tier1.get("key")
                if track_key not in keys:
                    continue

            # Energy filter
            if energy_min is not None or energy_max is not None:
                energy = tier1.get("energy")
                if energy is None:
                    continue
                if energy_min is not None and energy < energy_min:
                    continue
                if energy_max is not None and energy > energy_max:
                    continue

            # Genre filter
            if genre:
                track_genre = tier1.get("genre", "").lower()
                subgenre = tier3.get("subgenre", "").lower()
                if genre.lower() not in track_genre and genre.lower() not in subgenre:
                    continue

            # Vocals filter
            if has_vocals is not None:
                track_has_vocals = tier2.get("has_vocals")
                if track_has_vocals != has_vocals:
                    continue

            results.append(track)

        return results

    def find_compatible(
        self,
        track_hash: str,
        bpm_tolerance: float = 3.0,
        harmonic: bool = True,
    ) -> list[dict]:
        """Find tracks compatible for mixing with the given track."""
        source = self.get_track(track_hash)
        if not source or "tier1" not in source:
            return []

        source_bpm = source["tier1"].get("bpm")
        source_key = source["tier1"].get("key_camelot")

        if not source_bpm:
            return []

        # Harmonic keys (same, +1, -1 on camelot wheel)
        harmonic_keys = set()
        if source_key and harmonic:
            num = int(source_key[:-1])
            letter = source_key[-1]
            harmonic_keys.add(source_key)
            harmonic_keys.add(f"{(num % 12) + 1}{letter}")
            harmonic_keys.add(f"{((num - 2) % 12) + 1}{letter}")
            # Same number, different letter (relative major/minor)
            other_letter = "A" if letter == "B" else "B"
            harmonic_keys.add(f"{num}{other_letter}")

        results = []
        for track in self.get_all_tracks():
            if track.get("file_path") == source.get("file_path"):
                continue

            tier1 = track.get("tier1", {})
            track_bpm = tier1.get("bpm")
            track_key = tier1.get("key_camelot")

            if not track_bpm:
                continue

            # BPM check (also check half/double time)
            bpm_match = (
                abs(track_bpm - source_bpm) <= bpm_tolerance
                or abs(track_bpm * 2 - source_bpm) <= bpm_tolerance
                or abs(track_bpm - source_bpm * 2) <= bpm_tolerance
            )
            if not bpm_match:
                continue

            # Key check
            if harmonic and harmonic_keys and track_key not in harmonic_keys:
                continue

            results.append(track)

        return results

    def stats(self) -> dict[str, Any]:
        """Get catalog statistics."""
        tracks = self.get_all_tracks()
        tier1_count = sum(1 for t in tracks if "tier1" in t)
        tier2_count = sum(1 for t in tracks if "tier2" in t)
        tier3_count = sum(1 for t in tracks if "tier3" in t)

        return {
            "total_tracks": len(tracks),
            "tier1_analyzed": tier1_count,
            "tier2_analyzed": tier2_count,
            "tier3_analyzed": tier3_count,
        }
