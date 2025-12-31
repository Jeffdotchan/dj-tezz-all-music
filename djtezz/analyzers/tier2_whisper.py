"""Tier 2: Whisper-based vocal/lyrics detection and transcription."""

from pathlib import Path
from typing import Any

from .base import BaseAnalyzer


class WhisperAnalyzer(BaseAnalyzer):
    """Vocal detection and lyrics transcription using faster-whisper."""

    tier_name = "tier2"

    def __init__(self, gpu_id: int | None = 0, model_size: str = "large-v3"):
        """Initialize Whisper analyzer.

        Args:
            gpu_id: GPU device ID, or None for CPU
            model_size: Whisper model size (tiny, base, small, medium, large-v3)
        """
        super().__init__(gpu_id)
        self.model_size = model_size

    def load_model(self) -> None:
        """Load faster-whisper model."""
        try:
            from faster_whisper import WhisperModel
        except ImportError:
            raise ImportError(
                "faster-whisper not installed. Install with: pip install faster-whisper"
            )

        device = "cuda" if self.gpu_id is not None else "cpu"
        compute_type = "float16" if device == "cuda" else "int8"

        self._model = WhisperModel(
            self.model_size,
            device=device,
            device_index=self.gpu_id or 0,
            compute_type=compute_type,
        )

    def analyze(self, file_path: Path) -> dict[str, Any]:
        """Analyze audio file for vocals and lyrics.

        Returns dict with: has_vocals, lyrics, language, vocal_percentage
        """
        if self._model is None:
            raise RuntimeError("Model not loaded. Call load_model() first.")

        # Transcribe the audio
        segments, info = self._model.transcribe(
            str(file_path),
            beam_size=5,
            vad_filter=True,  # Filter out non-speech
            vad_parameters=dict(
                min_silence_duration_ms=500,
                speech_pad_ms=400,
            ),
        )

        # Collect segments
        segments_list = list(segments)

        # Calculate vocal coverage
        total_duration = info.duration
        vocal_duration = sum(seg.end - seg.start for seg in segments_list)
        vocal_percentage = vocal_duration / total_duration if total_duration > 0 else 0

        # Combine lyrics
        lyrics = " ".join(seg.text.strip() for seg in segments_list)

        # Determine if track has meaningful vocals
        # Consider it vocal if >10% of track has detected speech with reasonable text
        has_vocals = vocal_percentage > 0.1 and len(lyrics) > 20

        return {
            "has_vocals": has_vocals,
            "lyrics": lyrics if has_vocals else None,
            "language": info.language if has_vocals else None,
            "vocal_percentage": round(vocal_percentage, 2),
        }

    def unload_model(self) -> None:
        """Unload model from memory."""
        if self._model is not None:
            del self._model
            self._model = None

            # Clear CUDA cache if available
            try:
                import torch

                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
            except ImportError:
                pass
