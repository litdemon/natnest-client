import os
import platform
from pathlib import Path


class Config:
    VERSION = "0.5.0"
    SERVER_URL = os.getenv("NATNEST_SERVER_URL", "https://natnest.site")
    CONFIG_DIR = Path.home() / ".natnest"
    KEY_FILE = CONFIG_DIR / "id_ed25519"
    SESSION_FILE = CONFIG_DIR / "session.json"
    TUNNELS_FILE = CONFIG_DIR / "tunnels.json"
    LOG_FILE = CONFIG_DIR / "natnest.log"
    IS_WINDOWS = platform.system() == "Windows"
