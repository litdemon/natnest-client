import signal
import subprocess
import sys
import time

from .config import Config


class Watchdog:
    def run(self, ssh_cmd):
        def log(msg):
            with open(Config.LOG_FILE, "a") as f:
                f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}\n")

        log(f"Watchdog started for command: {' '.join(ssh_cmd)}")

        def handle_stop(signum, frame):
            log("Watchdog received stop signal, exiting...")
            sys.exit(0)

        if Config.IS_WINDOWS:
            # SIGBREAK is the closest equivalent to SIGTERM on Windows
            try:
                signal.signal(signal.SIGBREAK, handle_stop)
            except (OSError, AttributeError):
                pass
        else:
            signal.signal(signal.SIGTERM, handle_stop)

        signal.signal(signal.SIGINT, signal.SIG_IGN)

        while True:
            log("Attempting to open SSH tunnel...")
            try:
                result = subprocess.run(
                    ssh_cmd,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                log(f"SSH process exited with code {result.returncode}")
            except Exception as e:
                log(f"Error running SSH: {e}")

            log("Waiting 5 seconds before reconnecting...")
            time.sleep(5)
