"""FastAPI server for Qwen2-Audio analysis."""

import base64
import io
import json
import re
from contextlib import asynccontextmanager

import torch
import librosa
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from transformers import AutoProcessor, Qwen2AudioForConditionalGeneration

# Configuration
MODEL_NAME = "Qwen/Qwen2-Audio-7B-Instruct"
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

# Global model references
model = None
processor = None


ANALYSIS_PROMPT = """Analyze this EDM/electronic music track and provide a JSON response with:
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


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load model on startup, cleanup on shutdown."""
    global model, processor

    print(f"Loading {MODEL_NAME} on {DEVICE}...")

    processor = AutoProcessor.from_pretrained(MODEL_NAME)
    model = Qwen2AudioForConditionalGeneration.from_pretrained(
        MODEL_NAME,
        torch_dtype=torch.float16 if DEVICE == "cuda" else torch.float32,
        device_map="auto",
        low_cpu_mem_usage=True,
    )

    print(f"Model loaded! VRAM used: {torch.cuda.memory_allocated() / 1024**3:.1f} GB")
    yield

    # Cleanup
    del model, processor
    if torch.cuda.is_available():
        torch.cuda.empty_cache()


app = FastAPI(
    title="Qwen2-Audio Analysis Server",
    description="Analyze music tracks with Qwen2-Audio",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class AnalyzeRequest(BaseModel):
    """Request body for audio analysis."""
    audio_base64: str  # Base64 encoded audio file
    prompt: str | None = None  # Optional custom prompt


class AnalyzeResponse(BaseModel):
    """Response from audio analysis."""
    subgenre: str | None = None
    mood: list[str] = []
    energy_description: str | None = None
    instruments: list[str] = []
    similar_artists: list[str] = []
    best_setting: str | None = None
    vibe_description: str | None = None
    mix_notes: dict = {}
    raw_response: str | None = None


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "ok",
        "model": MODEL_NAME,
        "device": DEVICE,
        "vram_used_gb": torch.cuda.memory_allocated() / 1024**3 if torch.cuda.is_available() else 0,
    }


@app.post("/analyze", response_model=AnalyzeResponse)
async def analyze_audio(request: AnalyzeRequest):
    """Analyze an audio file with Qwen2-Audio."""
    global model, processor

    if model is None:
        raise HTTPException(status_code=503, detail="Model not loaded")

    try:
        # Decode base64 audio
        audio_bytes = base64.b64decode(request.audio_base64)

        # Load audio with librosa (handles most formats)
        audio, sr = librosa.load(io.BytesIO(audio_bytes), sr=16000)

        # Use custom prompt or default
        prompt = request.prompt or ANALYSIS_PROMPT

        # Prepare conversation
        conversation = [
            {
                "role": "user",
                "content": [
                    {"type": "audio", "audio": audio},
                    {"type": "text", "text": prompt},
                ],
            }
        ]

        # Process with model
        text = processor.apply_chat_template(
            conversation, add_generation_prompt=True, tokenize=False
        )

        inputs = processor(
            text=text,
            audios=[audio],
            sampling_rate=16000,
            return_tensors="pt",
        ).to(DEVICE)

        # Generate
        with torch.no_grad():
            generated_ids = model.generate(
                **inputs,
                max_new_tokens=512,
                temperature=0.7,
                do_sample=True,
            )

        # Decode response
        response_text = processor.batch_decode(
            generated_ids[:, inputs.input_ids.shape[1]:],
            skip_special_tokens=True,
        )[0]

        # Parse JSON
        result = parse_response(response_text)
        return AnalyzeResponse(**result)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def parse_response(response_text: str) -> dict:
    """Parse model response into structured data."""
    try:
        result = json.loads(response_text)
    except json.JSONDecodeError:
        # Try to extract JSON from response
        json_match = re.search(r"\{[\s\S]*\}", response_text)
        if json_match:
            try:
                result = json.loads(json_match.group())
            except json.JSONDecodeError:
                result = {"raw_response": response_text, "vibe_description": response_text[:500]}
        else:
            result = {"raw_response": response_text, "vibe_description": response_text[:500]}

    # Ensure all expected keys exist
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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8765)
