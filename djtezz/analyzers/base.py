"""Base analyzer class."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any


class BaseAnalyzer(ABC):
    """Base class for all analyzers."""

    tier_name: str = "base"

    def __init__(self, gpu_id: int | None = 0):
        """Initialize the analyzer.

        Args:
            gpu_id: GPU device ID to use, or None for CPU
        """
        self.gpu_id = gpu_id
        self._model = None

    @abstractmethod
    def load_model(self) -> None:
        """Load the analysis model into memory."""
        pass

    @abstractmethod
    def analyze(self, file_path: Path) -> dict[str, Any]:
        """Analyze a single audio file.

        Args:
            file_path: Path to the audio file

        Returns:
            Dictionary of analysis results
        """
        pass

    def unload_model(self) -> None:
        """Unload the model from memory."""
        self._model = None

    def __enter__(self):
        """Context manager entry."""
        self.load_model()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.unload_model()
