"""Scan récursif de la bibliothèque musicale."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterator

from src.utils.logger import get_logger

logger = get_logger(__name__)

AUDIO_EXTENSIONS = {".mp3", ".flac", ".m4a", ".ogg", ".opus", ".wav", ".aiff"}


@dataclass
class AudioFile:
    path: Path
    extension: str = field(init=False)
    size_bytes: int = field(init=False)

    def __post_init__(self):
        self.extension = self.path.suffix.lower()
        self.size_bytes = self.path.stat().st_size

    @property
    def relative_path(self) -> str:
        return str(self.path)

    def __repr__(self) -> str:
        return f"AudioFile({self.path.name})"


class LibraryScanner:
    def __init__(self, root: str | Path):
        self.root = Path(root).resolve()
        if not self.root.exists():
            raise FileNotFoundError(f"Dossier introuvable : {self.root}")

    def scan(self) -> list[AudioFile]:
        files = list(self._walk())
        logger.info(f"[bold green]{len(files)} fichiers audio trouvés[/bold green] dans {self.root}")
        return files

    def _walk(self) -> Iterator[AudioFile]:
        for dirpath, _, filenames in os.walk(self.root):
            for filename in sorted(filenames):
                path = Path(dirpath) / filename
                if path.suffix.lower() in AUDIO_EXTENSIONS:
                    try:
                        yield AudioFile(path)
                    except Exception as exc:
                        logger.warning(f"Impossible de lire {path}: {exc}")
