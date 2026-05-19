"""Déclenchement optionnel d'un scan Plex après traitement."""
from __future__ import annotations

import requests

from src.utils.config import config
from src.utils.logger import get_logger

logger = get_logger(__name__)


class PlexTrigger:
    def __init__(self):
        self.url = config.plex_url
        self.token = config.plex_token

    def trigger_scan(self, section_id: int = 1) -> bool:
        if not self.url or not self.token:
            logger.info("Plex non configuré — scan automatique ignoré")
            return False

        endpoint = f"{self.url}/library/sections/{section_id}/refresh"
        try:
            resp = requests.get(endpoint, headers={"X-Plex-Token": self.token}, timeout=10)
            if resp.status_code == 200:
                logger.info(f"[green]Scan Plex déclenché (section {section_id})[/green]")
                return True
            logger.warning(f"Plex répondu {resp.status_code}")
            return False
        except requests.RequestException as exc:
            logger.warning(f"Impossible de joindre Plex: {exc}")
            return False

    def list_sections(self) -> list[dict]:
        if not self.url or not self.token:
            return []
        try:
            resp = requests.get(
                f"{self.url}/library/sections",
                headers={"X-Plex-Token": self.token, "Accept": "application/json"},
                timeout=10,
            )
            resp.raise_for_status()
            data = resp.json()
            return data.get("MediaContainer", {}).get("Directory", [])
        except Exception as exc:
            logger.warning(f"Erreur liste sections Plex: {exc}")
            return []
