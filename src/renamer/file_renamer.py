"""Renommage et déplacement des fichiers selon la structure Plex recommandée."""
from __future__ import annotations

import re
import shutil
from pathlib import Path

from src.metadata.reader import TrackMetadata
from src.utils.logger import get_logger

logger = get_logger(__name__)

# Caractères interdits dans les noms de fichiers (Windows + Linux safe)
ILLEGAL_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def sanitize(text: str) -> str:
    """Supprime les caractères illégaux et trim."""
    return ILLEGAL_CHARS.sub("_", text).strip(" .")


def build_target_path(meta: TrackMetadata, root: Path) -> Path:
    """
    Construit le chemin cible selon la convention Plex :
      root/Artist/Album (Year)/DiscDisc TrackNum - Title.ext
    """
    artist = sanitize(meta.album_artist or meta.artist or "Unknown Artist")
    album = sanitize(meta.album or "Unknown Album")
    year = sanitize(meta.year or "")
    album_dir = f"{album} ({year})" if year else album

    track = f"{meta.track_number:02d}" if meta.track_number else "00"
    disc_prefix = f"{meta.disc_number}-" if meta.disc_number and meta.disc_number > 1 else ""
    title = sanitize(meta.title or meta.path.stem)

    filename = f"{disc_prefix}{track} - {title}{meta.path.suffix.lower()}"

    return root / artist / album_dir / filename


class FileRenamer:
    def __init__(self, output_root: Path):
        self.output_root = output_root

    def rename(self, meta: TrackMetadata, dry_run: bool = False) -> tuple[Path, bool]:
        """
        Déplace/renomme le fichier vers la structure Plex.
        Retourne (new_path, moved).
        """
        target = build_target_path(meta, self.output_root)

        if target == meta.path:
            logger.debug(f"Déjà bien nommé : {meta.path.name}")
            return target, False

        if dry_run:
            logger.info(f"[DRY-RUN] {meta.path} → {target}")
            return target, False

        target.parent.mkdir(parents=True, exist_ok=True)

        if target.exists():
            logger.warning(f"Cible déjà existante, ignoré : {target}")
            return target, False

        shutil.move(str(meta.path), str(target))
        logger.info(f"Déplacé : [cyan]{meta.path.name}[/cyan] → [green]{target}[/green]")
        return target, True
