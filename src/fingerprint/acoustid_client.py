"""Génération d'empreinte audio via fpcalc + soumission à AcoustID."""
from __future__ import annotations

import subprocess
import time
from pathlib import Path
from typing import Optional

import acoustid
import requests

from src.utils.config import config
from src.utils.logger import get_logger

logger = get_logger(__name__)

ACOUSTID_LOOKUP_URL = "https://api.acoustid.org/v2/lookup"


class AcoustIDClient:
    def __init__(self, api_key: str = ""):
        self.api_key = api_key or config.acoustid_api_key
        self._last_call = 0.0

    def _throttle(self) -> None:
        elapsed = time.time() - self._last_call
        if elapsed < 0.34:  # AcoustID: max 3 req/s
            time.sleep(0.34 - elapsed)
        self._last_call = time.time()

    def fingerprint(self, path: Path) -> Optional[tuple[float, str]]:
        """Retourne (duration, fingerprint) ou None si fpcalc absent."""
        try:
            duration, fp = acoustid.fingerprint_file(str(path))
            return float(duration), fp.decode() if isinstance(fp, bytes) else fp
        except acoustid.FingerprintGenerationError as exc:
            logger.warning(f"fpcalc indisponible pour {path.name}: {exc}")
            return None
        except FileNotFoundError:
            logger.error("fpcalc non trouvé — installez chromaprint: https://acoustid.org/chromaprint")
            return None

    def lookup(self, path: Path) -> list[dict]:
        """Interroge AcoustID et retourne une liste de résultats triés par score."""
        if not self.api_key:
            logger.warning("ACOUSTID_API_KEY manquante — fingerprint ignoré")
            return []

        result = self.fingerprint(path)
        if result is None:
            return []

        duration, fp = result
        self._throttle()

        try:
            matches = []
            for score, rid, title, artist in acoustid.parse_lookup_result(
                acoustid.lookup(self.api_key, fp, duration, meta="recordings releases releasegroups")
            ):
                if score >= config.acoustid_threshold:
                    matches.append(
                        {
                            "score": score,
                            "recording_id": rid,
                            "title": title,
                            "artist": artist,
                        }
                    )
            matches.sort(key=lambda x: x["score"], reverse=True)
            return matches
        except acoustid.WebServiceError as exc:
            logger.warning(f"AcoustID erreur réseau: {exc}")
            return []
        except Exception as exc:
            logger.warning(f"AcoustID erreur inattendue: {exc}")
            return []
