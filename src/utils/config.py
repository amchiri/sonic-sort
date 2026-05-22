import os
from dataclasses import dataclass, field
from dotenv import load_dotenv

load_dotenv()


@dataclass
class Config:
    acoustid_api_key: str = field(default_factory=lambda: os.getenv("ACOUSTID_API_KEY", ""))
    mb_app_name: str = field(default_factory=lambda: os.getenv("MB_APP_NAME", "SonicSort"))
    mb_app_version: str = field(default_factory=lambda: os.getenv("MB_APP_VERSION", "1.0.0"))
    mb_contact: str = field(default_factory=lambda: os.getenv("MB_CONTACT", "user@example.com"))
    mb_rate_limit: float = field(default_factory=lambda: float(os.getenv("MB_RATE_LIMIT_DELAY", "1.0")))
    acoustid_threshold: float = field(
        default_factory=lambda: float(os.getenv("ACOUSTID_CONFIDENCE_THRESHOLD", "0.8"))
    )
    plex_url: str = field(default_factory=lambda: os.getenv("PLEX_URL", ""))
    plex_token: str = field(default_factory=lambda: os.getenv("PLEX_TOKEN", ""))
    jellyfin_url: str = field(default_factory=lambda: os.getenv("JELLYFIN_URL", ""))
    jellyfin_api_key: str = field(default_factory=lambda: os.getenv("JELLYFIN_API_KEY", ""))


config = Config()
