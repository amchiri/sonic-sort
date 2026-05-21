"""Interrogation MusicBrainz pour récupérer les métadonnées enrichies."""
from __future__ import annotations

from typing import Optional

import musicbrainzngs as mb

from src.utils.config import config
from src.utils.logger import get_logger

logger = get_logger(__name__)


class MusicBrainzClient:
    def __init__(self):
        mb.set_useragent(config.mb_app_name, config.mb_app_version, config.mb_contact)
        mb.set_rate_limit(limit_or_interval=config.mb_rate_limit)

    def get_recording(self, recording_id: str) -> Optional[dict]:
        """Récupère une recording MusicBrainz par son MBID."""
        try:
            result = mb.get_recording_by_id(
                recording_id,
                includes=["artists", "releases", "media"],
            )
            return result.get("recording")
        except mb.ResponseError as exc:
            logger.warning(f"MusicBrainz ResponseError [{recording_id}]: {exc}")
            return None
        except mb.NetworkError as exc:
            logger.warning(f"MusicBrainz réseau [{recording_id}]: {exc}")
            return None

    def search_recording(self, title: str, artist: str = "", album: str = "") -> list[dict]:
        """Recherche textuelle dans MusicBrainz."""
        query_parts = [f'recording:"{title}"']
        if artist:
            query_parts.append(f'artist:"{artist}"')
        if album:
            query_parts.append(f'release:"{album}"')
        query = " AND ".join(query_parts)

        try:
            result = mb.search_recordings(query=query, limit=5)
            return result.get("recording-list", [])
        except Exception as exc:
            logger.warning(f"MusicBrainz search erreur: {exc}")
            return []

    def extract_metadata(self, recording: dict) -> dict:
        """Extrait les champs Plex-critiques depuis une recording MusicBrainz."""
        meta: dict = {}

        meta["title"] = recording.get("title", "")

        # Artiste principal
        credits = recording.get("artist-credit", [])
        artists = []
        for credit in credits:
            if isinstance(credit, dict) and "artist" in credit:
                artists.append(credit["artist"].get("name", ""))
        meta["artist"] = "; ".join(artists)

        # Choisir la meilleure release (officielle, non-bootleg)
        releases = recording.get("release-list", [])
        release = self._pick_best_release(releases)

        if release:
            meta["album"] = release.get("title", "")
            meta["year"] = self._extract_year(release)
            meta["album_artist"] = self._extract_album_artist(release)
            meta["track_number"] = self._extract_track_number(recording, release)
            meta["disc_number"] = self._extract_disc_number(recording, release)
        else:
            meta.update({"album": "", "year": "", "album_artist": meta["artist"], "track_number": 0, "disc_number": 1})

        return meta

    def _pick_best_release(self, releases: list[dict]) -> Optional[dict]:
        if not releases:
            return None

        def score(r: dict) -> int:
            s = 0
            status = r.get("status", "")
            rg = r.get("release-group", {})
            primary = rg.get("primary-type", "")
            if status == "Official":
                s += 10
            if primary == "Album":
                s += 5
            elif primary == "Single":
                s += 2
            return s

        return max(releases, key=score)

    def _extract_year(self, release: dict) -> str:
        date = release.get("date", "")
        return date[:4] if date else ""

    def _extract_album_artist(self, release: dict) -> str:
        credits = release.get("artist-credit", [])
        artists = []
        for credit in credits:
            if isinstance(credit, dict) and "artist" in credit:
                artists.append(credit["artist"].get("name", ""))
        return "; ".join(artists) if artists else ""

    def _extract_track_number(self, recording: dict, release: dict) -> int:
        media_list = release.get("medium-list", [])
        rid = recording.get("id", "")
        for medium in media_list:
            for track in medium.get("track-list", []):
                if track.get("recording", {}).get("id") == rid:
                    try:
                        return int(track.get("number", 0))
                    except ValueError:
                        return 0
        return 0

    def _extract_disc_number(self, recording: dict, release: dict) -> int:
        media_list = release.get("medium-list", [])
        rid = recording.get("id", "")
        for i, medium in enumerate(media_list, start=1):
            for track in medium.get("track-list", []):
                if track.get("recording", {}).get("id") == rid:
                    return i
        return 1
