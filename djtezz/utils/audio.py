"""Audio file utilities."""

from pathlib import Path

from mutagen import File as MutagenFile
from mutagen.easyid3 import EasyID3
from mutagen.mp3 import MP3
from mutagen.flac import FLAC
from mutagen.mp4 import MP4

from ..config import AUDIO_EXTENSIONS


def is_audio_file(path: Path) -> bool:
    """Check if a file is a supported audio file."""
    return path.suffix.lower() in AUDIO_EXTENSIONS


def scan_directory(path: Path, recursive: bool = True) -> list[Path]:
    """Scan a directory for audio files.

    Args:
        path: Directory to scan
        recursive: Whether to scan subdirectories

    Returns:
        List of audio file paths
    """
    audio_files = []

    if recursive:
        for file_path in path.rglob("*"):
            if file_path.is_file() and is_audio_file(file_path):
                audio_files.append(file_path)
    else:
        for file_path in path.iterdir():
            if file_path.is_file() and is_audio_file(file_path):
                audio_files.append(file_path)

    return sorted(audio_files)


def get_audio_metadata(path: Path) -> dict:
    """Extract metadata from an audio file.

    Returns dict with: artist, title, album, duration_sec, file_size_mb
    """
    result = {
        "artist": None,
        "title": None,
        "album": None,
        "duration_sec": None,
        "file_size_mb": round(path.stat().st_size / (1024 * 1024), 2),
    }

    try:
        audio = MutagenFile(path, easy=True)
        if audio is None:
            return result

        # Get duration
        if hasattr(audio.info, "length"):
            result["duration_sec"] = round(audio.info.length, 1)

        # Get tags
        if audio.tags:
            result["artist"] = _get_tag(audio, ["artist", "albumartist"])
            result["title"] = _get_tag(audio, ["title"])
            result["album"] = _get_tag(audio, ["album"])

    except Exception:
        pass  # Return partial results on error

    # Fallback: parse filename for artist - title
    if not result["title"]:
        name = path.stem
        if " - " in name:
            parts = name.split(" - ", 1)
            if not result["artist"]:
                result["artist"] = parts[0].strip()
            result["title"] = parts[1].strip()
        else:
            result["title"] = name

    return result


def _get_tag(audio, tag_names: list[str]) -> str | None:
    """Get first available tag from list of tag names."""
    for tag_name in tag_names:
        try:
            value = audio.get(tag_name)
            if value:
                if isinstance(value, list):
                    return value[0]
                return str(value)
        except Exception:
            continue
    return None
