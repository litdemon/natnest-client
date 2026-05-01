import subprocess
import sys
from pathlib import Path

import requests

from .config import Config


class Updater:
    def check(self):
        try:
            resp = requests.get(f"{Config.SERVER_URL}/api/version", timeout=2)
            resp.raise_for_status()
            data = resp.json()
            latest = data.get("version")
            if latest:
                v_latest = [int(x) for x in latest.split(".")]
                v_current = [int(x) for x in Config.VERSION.split(".")]
                if v_latest > v_current:
                    return True, data.get("url"), latest
        except Exception:
            pass
        return False, None, None

    def perform(self, download_url):
        print("Updating NatNest to latest version...")
        try:
            exe_path = Path(sys.executable).resolve()
            new_exe = exe_path.with_suffix(".new" if not Config.IS_WINDOWS else ".new.exe")

            print(f"Downloading from {download_url}...")
            resp = requests.get(download_url, stream=True, timeout=30)
            resp.raise_for_status()
            with open(new_exe, "wb") as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    f.write(chunk)

            if Config.IS_WINDOWS:
                self._swap_windows(exe_path, new_exe)
            else:
                self._swap_unix(exe_path, new_exe)

        except Exception as e:
            print(f"Update failed: {e}")
            if "new_exe" in dir() and new_exe.exists():
                try:
                    new_exe.unlink()
                except Exception:
                    pass
            sys.exit(1)

    def _swap_unix(self, exe_path, new_exe):
        old_exe = exe_path.with_suffix(".old")
        new_exe.chmod(0o755)
        if old_exe.exists():
            try:
                old_exe.unlink()
            except Exception:
                pass
        exe_path.rename(old_exe)
        new_exe.rename(exe_path)
        print("\nUpdate successful!")
        print("   The binary has been replaced. Please run your command again.")
        sys.exit(0)

    def _swap_windows(self, exe_path, new_exe):
        # Cannot replace a running .exe on Windows directly; use a bat script
        swap_bat = exe_path.parent / "_natnest_update.bat"
        swap_bat.write_text(
            f"@echo off\r\n"
            f"timeout /t 2 /nobreak > nul\r\n"
            f'move /Y "{new_exe}" "{exe_path}"\r\n'
            f'del "%~f0"\r\n',
            encoding="utf-8",
        )
        subprocess.Popen(
            ["cmd", "/c", str(swap_bat)],
            creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP,
            close_fds=True,
        )
        print("\nUpdate downloaded!")
        print("   The binary will be replaced when NatNest exits. Please re-run your command.")
        sys.exit(0)
