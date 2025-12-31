"""Tier 3: Qwen2-Audio for rich semantic analysis via local API."""

import base64
import json
import re
from pathlib import Path
from typing import Any

import httpx

from .base import BaseAnalyzer
from ..config import QWEN_ANALYSIS_PROMPT


class QwenAudioAnalyzer(BaseAnalyzer):
    """Rich semantic analysis using Qwen2-Audio via local API server."""

    tier_name = "tier3"

    def __init__(
        self,
        gpu_id: int | None = 0,
        api_base: str = "http://192.168.1.167:1234",
        model_name: str = "qwen2-audio-7b-instruct",
    ):
        """Initialize Qwen2-Audio analyzer.

        Args:
            gpu_id: Unused (model runs on remote server)
            api_base: Base URL for the API server
            model_name: Model name as shown in server
        """
        super().__init__(gpu_id)
        self.api_base = api_base.rstrip("/")
        self.model_name = model_name
        self._client = None

    def load_model(self) -> None:
        """Initialize HTTP client (model is already loaded on server)."""
        self._client = httpx.Client(timeout=300.0)  # 5 min timeout for long audio

        # Verify server is accessible
        try:
            response = self._client.get(f"{self.api_base}/v1/models")
            response.raise_for_status()
            models = response.json()
            model_ids = [m["id"] for m in models.get("data", [])]

            if self.model_name not in model_ids:
                available = ", ".join(model_ids[:5])
                raise RuntimeError(
                    f"Model '{self.model_name}' not found. Available: {available}"
                )
        except httpx.RequestError as e:
            raise RuntimeError(f"Cannot connect to API server at {self.api_base}: {e}")

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

        # Determine MIME type
        suffix = file_path.suffix.lower()
        mime_types = {
            ".mp3": "audio/mpeg",
            ".wav": "audio/wav",
            ".flac": "audio/flac",
            ".m4a": "audio/mp4",
            ".ogg": "audio/ogg",
            ".aac": "audio/aac",
        }
        mime_type = mime_types.get(suffix, "audio/mpeg")

        # Build request with audio content
        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "audio_url",
                        "audio_url": {
                            "url": f"data:{mime_type};base64,{audio_b64}"
                        }
                    },
                    {
                        "type": "text",
                        "text": QWEN_ANALYSIS_PROMPT
                    }
                ]
            }
        ]

        # Send request to API
        try:
            response = self._client.post(
                f"{self.api_base}/v1/chat/completions",
                json={
                    "model": self.model_name,
                    "messages": messages,
                    "max_tokens": 512,
                    "temperature": 0.7,
                },
            )
            response.raise_for_status()
            result_json = response.json()
            response_text = result_json["choices"][0]["message"]["content"]

        except httpx.HTTPStatusError as e:
            raise RuntimeError(f"API request failed: {e.response.status_code} - {e.response.text}")
        except (KeyError, IndexError) as e:
            raise RuntimeError(f"Unexpected API response format: {e}")

        # Parse JSON response
        result = self._parse_response(response_text)
        return result

    def _parse_response(self, response_text: str) -> dict[str, Any]:
        """Parse the model's response into structured data."""
        try:
            result = json.loads(response_text)
        except json.JSONDecodeError:
            # Try to extract JSON from response if wrapped in other text
            json_match = re.search(r"\{[\s\S]*\}", response_text)
            if json_match:
                try:
                    result = json.loads(json_match.group())
                except json.JSONDecodeError:
                    result = {"raw_response": response_text, "vibe_description": response_text[:500]}
            else:
                result = {"raw_response": response_text, "vibe_description": response_text[:500]}

        # Ensure expected keys exist with defaults
        defaults = {
            "subgenre": None,
            "mood": [],
            "energy_description": None,
            "instruments": [],
            "similar_artists": [],
            "best_setting": None,
            "vibe_description": None,
            "mix_notes": {},
        }

        for key, default in defaults.items():
            if key not in result:
                result[key] = default

        return result

    def unload_model(self) -> None:
        """Close HTTP client."""
        if self._client is not None:
            self._client.close()
            self._client = None
