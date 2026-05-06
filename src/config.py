import os
import platform
import sys
from pathlib import Path


def _read_version() -> str:
    # Frozen binary: VERSION file is bundled next to the executable
    if getattr(sys, "frozen", False):
        base = Path(sys.executable).parent
    else:
        base = Path(__file__).parent.parent
    version_file = base / "VERSION"
    try:
        return version_file.read_text(encoding="utf-8").strip()
    except OSError:
        return "0.0.0"


class Config:
    VERSION: str = _read_version()
    SERVER_URL: str = os.getenv("NATNEST_SERVER_URL", "https://natnest.site")
    CONFIG_DIR: Path = Path.home() / ".natnest"
    KEY_FILE: Path = CONFIG_DIR / "id_ed25519"
    SESSION_FILE: Path = CONFIG_DIR / "session.json"
    TUNNELS_FILE: Path = CONFIG_DIR / "tunnels.json"
    LOG_FILE: Path = CONFIG_DIR / "natnest.log"
    IS_WINDOWS: bool = platform.system() == "Windows"
