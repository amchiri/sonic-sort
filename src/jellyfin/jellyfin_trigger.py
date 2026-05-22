"""Déclenchement optionnel d'un scan Jellyfin après traitement."""
from __future__ import annotations

import requests

from src.utils.config import config
from src.utils.logger import get_logger

logger = get_logger(__name__)


class JellyfinTrigger:
    def __init__(self):
        self.url = config.jellyfin_url
        self.api_key = config.jellyfin_api_key

    def _headers(self) -> dict:
        return {
            "X-Emby-Token": self.api_key,
            "Accept": "application/json",
        }

    def trigger_scan(self, library_id: str = "") -> bool:
        """
        Si library_id fourni, refresh cette library uniquement.
        Sinon, refresh global (toutes les libraries).
        """
        if not self.url or not self.api_key:
            logger.info("Jellyfin non configuré — scan automatique ignoré")
            return False

        if library_id:
            endpoint = f"{self.url}/Items/{library_id}/Refresh"
            params = {"Recursive": "true", "MetadataRefreshMode": "FullRefresh"}
        else:
            endpoint = f"{self.url}/Library/Refresh"
            params = {}

        try:
            resp = requests.post(endpoint, headers=self._headers(), params=params, timeout=10)
            if resp.status_code in (200, 204):
                target = f"library {library_id}" if library_id else "global"
                logger.info(f"[green]Scan Jellyfin déclenché ({target})[/green]")
                return True
            logger.warning(f"Jellyfin répondu {resp.status_code}: {resp.text[:200]}")
            return False
        except requests.RequestException as exc:
            logger.warning(f"Impossible de joindre Jellyfin: {exc}")
            return False

    def list_libraries(self) -> list[dict]:
        if not self.url or not self.api_key:
            return []
        try:
            resp = requests.get(
                f"{self.url}/Library/MediaFolders",
                headers=self._headers(),
                timeout=10,
            )
            resp.raise_for_status()
            data = resp.json()
            return data.get("Items", [])
        except Exception as exc:
            logger.warning(f"Erreur liste libraries Jellyfin: {exc}")
            return []
