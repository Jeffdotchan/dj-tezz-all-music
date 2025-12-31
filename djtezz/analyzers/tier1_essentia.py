"""Tier 1: Essentia-based audio analysis for BPM, key, energy, genre."""

from pathlib import Path
from typing import Any

from .base import BaseAnalyzer
from ..config import KEY_TO_CAMELOT


class EssentiaAnalyzer(BaseAnalyzer):
    """Fast audio analysis using Essentia."""

    tier_name = "tier1"

    def __init__(self, gpu_id: int | None = 0):
        super().__init__(gpu_id)
        self._rhythm_extractor = None
        self._key_extractor = None
        self._models = {}

    def load_model(self) -> None:
        """Load Essentia models."""
        try:
            import essentia.standard as es
            from essentia.standard import (
                MonoLoader,
                RhythmExtractor2013,
                KeyExtractor,
                Energy,
                Danceability,
                DynamicComplexity,
            )
        except ImportError:
            raise ImportError(
                "Essentia not installed. Install with: pip install essentia-tensorflow"
            )

        self._es = es
        self._MonoLoader = MonoLoader
        self._RhythmExtractor = RhythmExtractor2013
        self._KeyExtractor = KeyExtractor
        self._Energy = Energy
        self._Danceability = Danceability
        self._DynamicComplexity = DynamicComplexity

        # Try to load genre classifier if available
        try:
            from essentia.standard import TensorflowPredictEffnetDiscogs, TensorflowPredict2D

            self._genre_available = True
        except ImportError:
            self._genre_available = False

    def analyze(self, file_path: Path) -> dict[str, Any]:
        """Analyze audio file with Essentia.

        Returns dict with: bpm, key, key_camelot, energy, danceability, loudness_db, genre
        """
        # Load audio
        audio = self._MonoLoader(filename=str(file_path), sampleRate=44100)()

        # BPM extraction
        rhythm_extractor = self._RhythmExtractor()
        bpm, beats, beats_confidence, _, beats_intervals = rhythm_extractor(audio)

        # Key extraction
        key_extractor = self._KeyExtractor()
        key, scale, key_strength = key_extractor(audio)
        key_string = f"{key} {scale}"
        key_camelot = KEY_TO_CAMELOT.get(key_string, "")

        # Energy (RMS-based)
        energy_extractor = self._Energy()
        energy_value = energy_extractor(audio)
        # Normalize to 0-1 range (typical music energy is 0.01-0.3)
        energy_normalized = min(1.0, energy_value / 0.2)

        # Danceability
        danceability_extractor = self._Danceability()
        danceability, _ = danceability_extractor(audio)

        # Dynamic complexity (proxy for energy variation)
        dc_extractor = self._DynamicComplexity()
        dynamic_complexity, loudness = dc_extractor(audio)

        # Genre classification (if model available)
        genre = None
        genre_confidence = None
        if self._genre_available:
            try:
                genre, genre_confidence = self._classify_genre(audio)
            except Exception:
                pass  # Genre classification failed, continue without it

        result = {
            "bpm": round(bpm, 1),
            "key": key_string,
            "key_camelot": key_camelot,
            "energy": round(energy_normalized, 2),
            "danceability": round(danceability, 2),
            "loudness_db": round(loudness, 1),
        }

        if genre:
            result["genre"] = genre
            result["genre_confidence"] = round(genre_confidence, 2)

        return result

    def _classify_genre(self, audio) -> tuple[str, float]:
        """Classify genre using Essentia's pre-trained model."""
        # This is a simplified version - full implementation would use
        # TensorflowPredictEffnetDiscogs or similar pre-trained models
        # For now, return placeholder
        return None, None

    def unload_model(self) -> None:
        """Unload models from memory."""
        self._es = None
        self._MonoLoader = None
        self._RhythmExtractor = None
        self._KeyExtractor = None
        self._Energy = None
        self._Danceability = None
        self._DynamicComplexity = None
        self._genre_available = False
