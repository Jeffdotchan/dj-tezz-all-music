"""Tier 3: Qwen2-Audio for rich semantic analysis."""

import json
from pathlib import Path
from typing import Any

from .base import BaseAnalyzer
from ..config import QWEN_ANALYSIS_PROMPT


class QwenAudioAnalyzer(BaseAnalyzer):
    """Rich semantic analysis using Qwen2-Audio."""

    tier_name = "tier3"

    def __init__(self, gpu_id: int | None = 0, model_name: str = "Qwen/Qwen2-Audio-7B-Instruct"):
        """Initialize Qwen2-Audio analyzer.

        Args:
            gpu_id: GPU device ID, or None for CPU
            model_name: HuggingFace model name
        """
        super().__init__(gpu_id)
        self.model_name = model_name

    def load_model(self) -> None:
        """Load Qwen2-Audio model."""
        try:
            import torch
            from transformers import AutoProcessor, Qwen2AudioForConditionalGeneration
        except ImportError:
            raise ImportError(
                "Required packages not installed. Install with: "
                "pip install transformers torch accelerate"
            )

        device = f"cuda:{self.gpu_id}" if self.gpu_id is not None else "cpu"

        # Load with appropriate precision for memory efficiency
        self._processor = AutoProcessor.from_pretrained(self.model_name)
        self._model = Qwen2AudioForConditionalGeneration.from_pretrained(
            self.model_name,
            torch_dtype=torch.float16 if "cuda" in device else torch.float32,
            device_map=device,
            low_cpu_mem_usage=True,
        )
        self._device = device
        self._torch = torch

    def analyze(self, file_path: Path) -> dict[str, Any]:
        """Analyze audio file with Qwen2-Audio for rich semantic understanding.

        Returns dict with: subgenre, mood, energy_description, instruments,
                         similar_artists, best_setting, vibe_description, mix_notes
        """
        if self._model is None:
            raise RuntimeError("Model not loaded. Call load_model() first.")

        import librosa

        # Load audio at 16kHz (Qwen2-Audio's expected sample rate)
        audio, sr = librosa.load(str(file_path), sr=16000)

        # Prepare inputs
        conversation = [
            {
                "role": "user",
                "content": [
                    {"type": "audio", "audio": audio},
                    {"type": "text", "text": QWEN_ANALYSIS_PROMPT},
                ],
            }
        ]

        text = self._processor.apply_chat_template(
            conversation, add_generation_prompt=True, tokenize=False
        )

        inputs = self._processor(
            text=text,
            audios=[audio],
            sampling_rate=sr,
            return_tensors="pt",
        ).to(self._device)

        # Generate response
        with self._torch.no_grad():
            generated_ids = self._model.generate(
                **inputs,
                max_new_tokens=512,
                temperature=0.7,
                do_sample=True,
            )

        # Decode response
        response = self._processor.batch_decode(
            generated_ids[:, inputs.input_ids.shape[1]:],
            skip_special_tokens=True,
        )[0]

        # Parse JSON response
        try:
            result = json.loads(response)
        except json.JSONDecodeError:
            # Try to extract JSON from response if wrapped in other text
            import re

            json_match = re.search(r"\{[\s\S]*\}", response)
            if json_match:
                result = json.loads(json_match.group())
            else:
                # Return raw response if JSON parsing fails
                result = {
                    "raw_response": response,
                    "vibe_description": response[:500],
                }

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
        """Unload model from memory."""
        if self._model is not None:
            del self._model
            del self._processor
            self._model = None
            self._processor = None

            # Clear CUDA cache
            try:
                import torch

                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
            except ImportError:
                pass
