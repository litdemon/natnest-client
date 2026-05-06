import os
import platform
import sys
from pathlib import Path


def _read_version() -> str:
    if getattr(sys, "frozen", False):
        # _MEIPASS: PyInstaller's extraction dir (datas live here)
        # Fallback: directory containing the executable
        candidates = [
            Path(getattr(sys, "_MEIPASS", "")),
            Path(sys.executable).parent,
        ]
    else:
        candidates = [Path(__file__).parent.parent]

    for base in candidates:
        try:
            return (base / "VERSION").read_text(encoding="utf-8").strip()
        except OSError:
            continue
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
