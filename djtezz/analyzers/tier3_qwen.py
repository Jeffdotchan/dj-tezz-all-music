"""Tier 3: Qwen2-Audio for rich semantic analysis via custom FastAPI server."""

import base64
import json
import re
from pathlib import Path
from typing import Any

import httpx

from .base import BaseAnalyzer


class QwenAudioAnalyzer(BaseAnalyzer):
    """Rich semantic analysis using Qwen2-Audio via custom FastAPI server."""

    tier_name = "tier3"

    def __init__(
        self,
        gpu_id: int | None = 0,
        api_base: str = "http://192.168.1.167:8765",
    ):
        """Initialize Qwen2-Audio analyzer.

        Args:
            gpu_id: Unused (model runs on remote server)
            api_base: Base URL for the Qwen2-Audio FastAPI server
        """
        super().__init__(gpu_id)
        self.api_base = api_base.rstrip("/")
        self._client = None

    def load_model(self) -> None:
        """Initialize HTTP client and verify server is running."""
        self._client = httpx.Client(timeout=600.0)  # 10 min timeout for long audio

        # Verify server is accessible
        try:
            response = self._client.get(f"{self.api_base}/health")
            response.raise_for_status()
            health = response.json()
            print(f"Connected to Qwen2-Audio server: {health.get('model')}")
            print(f"Device: {health.get('device')}, VRAM: {health.get('vram_used_gb', 0):.1f} GB")
        except httpx.RequestError as e:
            raise RuntimeError(
                f"Cannot connect to Qwen2-Audio server at {self.api_base}\n"
                f"Start the server with: python server/qwen_audio_server.py\n"
                f"Error: {e}"
            )

    def analyze(self, file_path: Path) -> dict[str, Any]:
        """Analyze audio file with Qwen2-Audio for rich semantic understanding.

        Returns dict with: subgenre, mood, energy_description, instruments,
                         similar_artists, best_setting, vibe_description, mix_notes
        """
        if self._client is None:
            raise RuntimeError("Client not initialized. Call load_model() first.")

        # Read and encode audio file as base64
        with open(file_path, "rb") as f:
            audio_bytes = f.read()
        audio_b64 = base64.b64encode(audio_bytes).decode("utf-8")

        # Send request to our custom server
        try:
            response = self._client.post(
                f"{self.api_base}/analyze",
                json={"audio_base64": audio_b64},
            )
            response.raise_for_status()
            result = response.json()
            return result

        except httpx.HTTPStatusError as e:
            error_detail = e.response.text
            try:
                error_json = e.response.json()
                error_detail = error_json.get("detail", error_detail)
            except Exception:
                pass
            raise RuntimeError(f"API request failed: {e.response.status_code} - {error_detail}")

    def unload_model(self) -> None:
        """Close HTTP client."""
        if self._client is not None:
            self._client.close()
            self._client = None
