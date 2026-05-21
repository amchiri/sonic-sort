"""Lecture des métadonnées audio via mutagen (ID3v2, Vorbis, MP4)."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import mutagen
from mutagen.id3 import ID3, ID3NoHeaderError
from mutagen.flac import FLAC
from mutagen.mp4 import MP4
from mutagen.oggvorbis import OggVorbis

from src.utils.logger import get_logger

logger = get_logger(__name__)


def _parse_num_pair(raw: str) -> tuple[int, int]:
    if not raw:
        return 0, 0
    parts = raw.split("/")
    try:
        num = int(parts[0])
        tot = int(parts[1]) if len(parts) > 1 else 0
        return num, tot
    except ValueError:
        return 0, 0


@dataclass
class TrackMetadata:
    path: Path
    title: str = ""
    artist: str = ""
    album_artist: str = ""
    album: str = ""
    year: str = ""
    track_number: int = 0
    track_total: int = 0
    disc_number: int = 0
    disc_total: int = 0
    genre: str = ""
    has_cover: bool = False
    raw: dict[str, Any] = field(default_factory=dict)

    @property
    def missing_fields(self) -> list[str]:
        required = {
            "title": self.title,
            "artist": self.artist,
            "album_artist": self.album_artist,
            "album": self.album,
            "year": self.year,
            "track_number": self.track_number,
        }
        return [k for k, v in required.items() if not v]

    @property
    def is_complete(self) -> bool:
        return len(self.missing_fields) == 0

    def __repr__(self) -> str:
        return f"<{self.artist} – {self.album} – {self.track_number:02d}. {self.title}>"


class MetadataReader:
    def read(self, path: Path) -> TrackMetadata:
        ext = path.suffix.lower()
        try:
            if ext == ".mp3":
                return self._read_id3(path)
            elif ext == ".flac":
                return self._read_flac(path)
            elif ext in (".m4a", ".aac"):
                return self._read_mp4(path)
            elif ext in (".ogg", ".opus"):
                return self._read_ogg(path)
            else:
                return self._read_generic(path)
        except Exception as exc:
            logger.warning(f"Erreur lecture métadonnées {path.name}: {exc}")
            return TrackMetadata(path=path)

    # --- MP3 / ID3v2 ---

    def _read_id3(self, path: Path) -> TrackMetadata:
        try:
            tags = ID3(path)
        except ID3NoHeaderError:
            tags = {}

        def get(tag: str) -> str:
            val = tags.get(tag)
            return str(val.text[0]) if val and hasattr(val, "text") else ""

        def get_num(tag: str) -> tuple[int, int]:
            val = tags.get(tag)
            return _parse_num_pair(str(val.text[0])) if val else (0, 0)

        track_num, track_tot = get_num("TRCK")
        disc_num, disc_tot = get_num("TPOS")

        has_cover = any(k.startswith("APIC") for k in tags)

        return TrackMetadata(
            path=path,
            title=get("TIT2"),
            artist=get("TPE1"),
            album_artist=get("TPE2"),
            album=get("TALB"),
            year=get("TDRC") or get("TYER"),
            track_number=track_num,
            track_total=track_tot,
            disc_number=disc_num,
            disc_total=disc_tot,
            genre=get("TCON"),
            has_cover=has_cover,
            raw=dict(tags),
        )

    # --- FLAC / Vorbis Comments ---

    def _read_flac(self, path: Path) -> TrackMetadata:
        audio = FLAC(path)
        tags = audio.tags or {}

        def get(key: str) -> str:
            vals = tags.get(key.lower()) or tags.get(key.upper()) or []
            return vals[0] if vals else ""

        track_num, track_tot = _parse_num_pair(get("tracknumber"))
        disc_num, disc_tot = _parse_num_pair(get("discnumber"))

        return TrackMetadata(
            path=path,
            title=get("title"),
            artist=get("artist"),
            album_artist=get("albumartist"),
            album=get("album"),
            year=get("date") or get("year"),
            track_number=track_num,
            track_total=track_tot,
            disc_number=disc_num,
            disc_total=disc_tot,
            genre=get("genre"),
            has_cover=len(audio.pictures) > 0,
            raw=dict(tags),
        )

    # --- MP4 / M4A atoms ---

    def _read_mp4(self, path: Path) -> TrackMetadata:
        audio = MP4(path)
        tags = audio.tags or {}

        def get(key: str) -> str:
            val = tags.get(key)
            if not val:
                return ""
            return str(val[0]) if isinstance(val, list) else str(val)

        def get_num(key: str) -> tuple[int, int]:
            val = tags.get(key)
            if not val:
                return 0, 0
            item = val[0]
            if isinstance(item, tuple):
                return item[0], item[1]
            try:
                return int(item), 0
            except (ValueError, TypeError):
                return 0, 0

        track_num, track_tot = get_num("trkn")
        disc_num, disc_tot = get_num("disk")

        return TrackMetadata(
            path=path,
            title=get("\xa9nam"),
            artist=get("\xa9ART"),
            album_artist=get("aART"),
            album=get("\xa9alb"),
            year=get("\xa9day"),
            track_number=track_num,
            track_total=track_tot,
            disc_number=disc_num,
            disc_total=disc_tot,
            genre=get("\xa9gen"),
            has_cover="covr" in tags,
            raw=dict(tags),
        )

    # --- OGG / Opus ---

    def _read_ogg(self, path: Path) -> TrackMetadata:
        audio = OggVorbis(path)
        tags = audio.tags or {}

        def get(key: str) -> str:
            vals = tags.get(key.lower()) or tags.get(key.upper()) or []
            return vals[0] if vals else ""

        track_num, track_tot = _parse_num_pair(get("tracknumber"))
        disc_num, disc_tot = _parse_num_pair(get("discnumber"))

        return TrackMetadata(
            path=path,
            title=get("title"),
            artist=get("artist"),
            album_artist=get("albumartist"),
            album=get("album"),
            year=get("date") or get("year"),
            track_number=track_num,
            track_total=track_tot,
            disc_number=disc_num,
            disc_total=disc_tot,
            genre=get("genre"),
            has_cover=False,
            raw=dict(tags),
        )

    def _read_generic(self, path: Path) -> TrackMetadata:
        audio = mutagen.File(path, easy=True)
        if audio is None:
            return TrackMetadata(path=path)
        tags = audio.tags or {}

        def get(key: str) -> str:
            val = tags.get(key, [])
            return val[0] if val else ""

        return TrackMetadata(
            path=path,
            title=get("title"),
            artist=get("artist"),
            album=get("album"),
            year=get("date"),
            raw=dict(tags),
        )
