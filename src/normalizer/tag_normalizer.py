"""Normalisation des métadonnées : casse, feat, accents, écriture tags."""
from __future__ import annotations

import re
from pathlib import Path

from mutagen.id3 import (
    ID3, TIT2, TPE1, TPE2, TALB, TDRC, TRCK, TPOS, TCON,
    ID3NoHeaderError, TYER,
)
from mutagen.flac import FLAC
from mutagen.mp4 import MP4
from mutagen.oggvorbis import OggVorbis

from src.metadata.reader import TrackMetadata
from src.utils.logger import get_logger

logger = get_logger(__name__)

# Variantes de "featuring" à normaliser
FEAT_PATTERN = re.compile(
    r"\s*[\(\[]?\s*(?:feat(?:uring)?|ft|with|w/)\s*[.:]?\s*",
    re.IGNORECASE,
)

# Mots à ne PAS mettre en majuscule (articles/prépositions anglais et français)
LOWERCASE_WORDS = {
    "a", "an", "the", "and", "but", "or", "nor", "as", "at", "by",
    "for", "in", "of", "on", "to", "up", "yet", "so",
    "le", "la", "les", "de", "du", "des", "un", "une", "et", "en",
}


def normalize_feat(text: str) -> str:
    """Transforme toutes les variantes de feat. en '(feat. Artist)'."""
    match = FEAT_PATTERN.search(text)
    if not match:
        return text
    base = text[: match.start()].strip()
    feat_part = text[match.end():].strip().rstrip(")").rstrip("]")
    return f"{base} (feat. {feat_part})"


def title_case(text: str) -> str:
    """Title case qui respecte les articles."""
    if not text:
        return text
    words = text.split()
    result = []
    for i, word in enumerate(words):
        if i == 0 or word.lower() not in LOWERCASE_WORDS:
            result.append(word.capitalize())
        else:
            result.append(word.lower())
    return " ".join(result)


def normalize_year(year: str) -> str:
    """Garde uniquement les 4 premiers chiffres."""
    match = re.search(r"\d{4}", year)
    return match.group(0) if match else ""


def normalize_track_number(num: int, total: int = 0) -> str:
    if total:
        return f"{num}/{total}"
    return str(num)


class TagNormalizer:
    def normalize(self, meta: TrackMetadata, source_meta: dict) -> TrackMetadata:
        """Fusionne les données source dans meta et normalise les valeurs."""
        merged = TrackMetadata(path=meta.path)

        merged.title = title_case(normalize_feat(source_meta.get("title") or meta.title))
        merged.artist = normalize_feat(source_meta.get("artist") or meta.artist)
        merged.album_artist = source_meta.get("album_artist") or meta.album_artist or merged.artist
        merged.album = source_meta.get("album") or meta.album
        merged.year = normalize_year(source_meta.get("year") or meta.year)
        merged.track_number = source_meta.get("track_number") or meta.track_number
        merged.track_total = source_meta.get("track_total") or meta.track_total
        merged.disc_number = source_meta.get("disc_number") or meta.disc_number or 1
        merged.disc_total = meta.disc_total
        merged.genre = source_meta.get("genre") or meta.genre
        merged.has_cover = meta.has_cover
        merged.raw = meta.raw

        return merged

    def write(self, meta: TrackMetadata, dry_run: bool = False) -> bool:
        """Écrit les métadonnées normalisées dans le fichier audio."""
        ext = meta.path.suffix.lower()
        if dry_run:
            logger.info(f"[DRY-RUN] Écriture ignorée pour {meta.path.name}")
            return True
        try:
            if ext == ".mp3":
                return self._write_id3(meta)
            elif ext == ".flac":
                return self._write_flac(meta)
            elif ext in (".m4a", ".aac"):
                return self._write_mp4(meta)
            elif ext in (".ogg", ".opus"):
                return self._write_ogg(meta)
        except Exception as exc:
            logger.error(f"Erreur écriture tags {meta.path.name}: {exc}")
            return False
        return False

    def _write_id3(self, meta: TrackMetadata) -> bool:
        try:
            tags = ID3(meta.path)
        except ID3NoHeaderError:
            tags = ID3()

        tags.delall("TIT2"); tags.add(TIT2(encoding=3, text=meta.title))
        tags.delall("TPE1"); tags.add(TPE1(encoding=3, text=meta.artist))
        tags.delall("TPE2"); tags.add(TPE2(encoding=3, text=meta.album_artist))
        tags.delall("TALB"); tags.add(TALB(encoding=3, text=meta.album))
        tags.delall("TDRC"); tags.add(TDRC(encoding=3, text=meta.year))
        tags.delall("TYER"); tags.add(TYER(encoding=3, text=meta.year))

        trck = normalize_track_number(meta.track_number, meta.track_total)
        tags.delall("TRCK"); tags.add(TRCK(encoding=3, text=trck))

        if meta.disc_number:
            tpos = normalize_track_number(meta.disc_number, meta.disc_total)
            tags.delall("TPOS"); tags.add(TPOS(encoding=3, text=tpos))

        tags.save(meta.path, v2_version=3)
        return True

    def _write_flac(self, meta: TrackMetadata) -> bool:
        audio = FLAC(meta.path)
        audio["title"] = meta.title
        audio["artist"] = meta.artist
        audio["albumartist"] = meta.album_artist
        audio["album"] = meta.album
        audio["date"] = meta.year
        audio["tracknumber"] = str(meta.track_number)
        if meta.track_total:
            audio["totaltracks"] = str(meta.track_total)
        if meta.disc_number:
            audio["discnumber"] = str(meta.disc_number)
        audio.save()
        return True

    def _write_mp4(self, meta: TrackMetadata) -> bool:
        audio = MP4(meta.path)
        audio["\xa9nam"] = meta.title
        audio["\xa9ART"] = meta.artist
        audio["aART"] = meta.album_artist
        audio["\xa9alb"] = meta.album
        audio["\xa9day"] = meta.year
        audio["trkn"] = [(meta.track_number, meta.track_total)]
        if meta.disc_number:
            audio["disk"] = [(meta.disc_number, meta.disc_total)]
        audio.save()
        return True

    def _write_ogg(self, meta: TrackMetadata) -> bool:
        audio = OggVorbis(meta.path)
        audio["title"] = meta.title
        audio["artist"] = meta.artist
        audio["albumartist"] = meta.album_artist
        audio["album"] = meta.album
        audio["date"] = meta.year
        audio["tracknumber"] = str(meta.track_number)
        if meta.disc_number:
            audio["discnumber"] = str(meta.disc_number)
        audio.save()
        return True
