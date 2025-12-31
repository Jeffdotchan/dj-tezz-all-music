"""File hashing utilities."""

import hashlib
from pathlib import Path


def hash_file(path: Path, chunk_size: int = 8192) -> str:
    """Compute SHA-256 hash of a file.

    Args:
        path: Path to file
        chunk_size: Size of chunks to read

    Returns:
        Hex string of SHA-256 hash
    """
    sha256 = hashlib.sha256()

    with open(path, "rb") as f:
        while chunk := f.read(chunk_size):
            sha256.update(chunk)

    return sha256.hexdigest()


def hash_file_quick(path: Path, sample_size: int = 65536) -> str:
    """Compute a quick hash using file size + samples from start/end.

    Much faster than full hash for large audio files. Good for
    change detection, not cryptographic purposes.

    Args:
        path: Path to file
        sample_size: Bytes to sample from start and end

    Returns:
        Hex string of hash
    """
    file_size = path.stat().st_size
    sha256 = hashlib.sha256()

    # Include file size in hash
    sha256.update(str(file_size).encode())

    with open(path, "rb") as f:
        # Read from start
        sha256.update(f.read(sample_size))

        # Read from end if file is large enough
        if file_size > sample_size * 2:
            f.seek(-sample_size, 2)  # Seek from end
            sha256.update(f.read(sample_size))

    return sha256.hexdigest()[:16]  # Truncate for brevity
