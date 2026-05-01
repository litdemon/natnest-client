import subprocess
import sys
from pathlib import Path

from .config import Config


class AutostartManager:
    def setup(self):
        exe_path = sys.executable if getattr(sys, "frozen", False) else sys.argv[0]
        exe_path = str(Path(exe_path).resolve())

        if Config.IS_WINDOWS:
            self._setup_windows(exe_path)
        elif sys.platform.startswith("linux"):
            self._setup_linux(exe_path)
        elif sys.platform == "darwin":
            self._setup_macos(exe_path)
        else:
            print("Unsupported OS for autostart.")

    def _setup_windows(self, exe_path):
        try:
            import winreg
            key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE)
            winreg.SetValueEx(key, "NatNest", 0, winreg.REG_SZ, f'"{exe_path}" restore')
            winreg.CloseKey(key)
            print("Auto-start enabled for Windows (Registry).")
        except Exception as e:
            print(f"Failed to configure auto-start: {e}")

    def _setup_linux(self, exe_path):
        service_dir = Path.home() / ".config" / "systemd" / "user"
        service_dir.mkdir(parents=True, exist_ok=True)
        service_file = service_dir / "natnest.service"

        content = (
            "[Unit]\n"
            "Description=NatNest Tunnel Restorer\n"
            "After=network.target\n\n"
            "[Service]\n"
            "Type=oneshot\n"
            f"ExecStart={exe_path} restore\n"
            "RemainAfterExit=yes\n\n"
            "[Install]\n"
            "WantedBy=default.target\n"
        )
        with open(service_file, "w") as f:
            f.write(content)

        try:
            subprocess.run(["systemctl", "--user", "daemon-reload"], check=True)
            subprocess.run(["systemctl", "--user", "enable", "natnest.service"], check=True)
            print("Auto-start enabled for Linux (systemd).")
        except Exception as e:
            print(f"Failed to enable systemd service: {e}")

    def _setup_macos(self, exe_path):
        plist_dir = Path.home() / "Library" / "LaunchAgents"
        plist_dir.mkdir(parents=True, exist_ok=True)
        plist_file = plist_dir / "com.natnest.tunnel.plist"

        content = (
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"'
            ' "http://www.apple.com/DTDs/PropertyList-1.0.dtd">\n'
            '<plist version="1.0">\n'
            "<dict>\n"
            "    <key>Label</key>\n"
            "    <string>com.natnest.tunnel</string>\n"
            "    <key>ProgramArguments</key>\n"
            "    <array>\n"
            f"        <string>{exe_path}</string>\n"
            "        <string>restore</string>\n"
            "    </array>\n"
            "    <key>RunAtLoad</key>\n"
            "    <true/>\n"
            "</dict>\n"
            "</plist>\n"
        )
        with open(plist_file, "w") as f:
            f.write(content)
        print("Auto-start enabled for macOS (LaunchAgent).")
