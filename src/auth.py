import json
import subprocess
import sys
import time

import requests

from .config import Config


class AuthManager:
    def ensure_ssh_key(self):
        Config.CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        if not Config.KEY_FILE.exists():
            print("Generating new SSH key pair...")
            subprocess.run(
                ["ssh-keygen", "-t", "ed25519", "-f", str(Config.KEY_FILE), "-N", ""],
                check=True,
                capture_output=True,
            )
        with open(str(Config.KEY_FILE) + ".pub", "r") as f:
            return f.read().strip()

    def get_session(self):
        if Config.SESSION_FILE.exists():
            try:
                with open(Config.SESSION_FILE, "r") as f:
                    return json.load(f)
            except Exception:
                return None
        return None

    def save_session(self, data):
        with open(Config.SESSION_FILE, "w") as f:
            json.dump(data, f)

    def authenticate(self, public_key):
        print("Connecting to NatNest for authentication...")
        try:
            resp = requests.post(
                f"{Config.SERVER_URL}/api/auth/device",
                json={"public_key": public_key},
                timeout=10,
            )
            resp.raise_for_status()
            auth_data = resp.json()
        except Exception as e:
            print(f"Failed to connect to server: {e}")
            sys.exit(1)

        print("\n" + "=" * 50)
        print("  GOOGLE LOGIN REQUIRED")
        print("=" * 50)
        print(f"1. Open this URL in your browser:\n   {auth_data['verification_url']}")
        print(f"\n2. Enter this code:\n   {auth_data['user_code']}")
        print("=" * 50)
        print("\nWaiting for approval...")

        device_code = auth_data["device_code"]
        interval = auth_data.get("interval", 5)

        while True:
            try:
                resp = requests.post(
                    f"{Config.SERVER_URL}/api/auth/token",
                    json={"device_code": device_code},
                    timeout=10,
                )
                if resp.status_code == 200:
                    user_data = resp.json()
                    print(f"\nAuthentication successful! Welcome, {user_data['email']}.")
                    self.save_session(user_data)
                    return user_data

                error = resp.json().get("error")
                if error == "authorization_pending":
                    time.sleep(interval)
                    continue
                else:
                    print(f"Authentication failed: {error}")
                    sys.exit(1)
            except Exception as e:
                print(f"Error: {e}")
                sys.exit(1)
