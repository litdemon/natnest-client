import json
import os
import re
import signal
import subprocess
import sys
import time
import uuid

import requests

from .config import Config


def _spawn_watchdog(watchdog_cmd):
    if Config.IS_WINDOWS:
        return subprocess.Popen(
            watchdog_cmd,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS,
        )
    else:
        return subprocess.Popen(
            watchdog_cmd,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )


def _kill_process(pid):
    if Config.IS_WINDOWS:
        subprocess.run(
            ["taskkill", "/F", "/T", "/PID", str(pid)],
            capture_output=True,
        )
    else:
        try:
            os.killpg(int(pid), signal.SIGTERM)
        except OSError:
            os.kill(int(pid), signal.SIGTERM)


class TunnelManager:
    def load(self):
        if Config.TUNNELS_FILE.exists():
            try:
                with open(Config.TUNNELS_FILE, "r") as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    def save(self, tunnels):
        with open(Config.TUNNELS_FILE, "w") as f:
            json.dump(tunnels, f)

    def is_pid_running(self, pid):
        try:
            if Config.IS_WINDOWS:
                result = subprocess.run(
                    ["tasklist", "/FI", f"PID eq {pid}", "/NH"],
                    capture_output=True,
                    text=True,
                )
                return str(pid) in result.stdout
            else:
                os.kill(int(pid), 0)
                return True
        except OSError:
            return False

    def clean_dead(self):
        tunnels = self.load()
        active = {}
        changed = False
        for pid, info in tunnels.items():
            if self.is_pid_running(pid):
                active[pid] = info
            else:
                changed = True
        if changed:
            self.save(active)
        return active

    def status(self):
        tunnels = self.clean_dead()
        print(f"NatNest Active Tunnels (v{Config.VERSION})")
        print("-" * 75)
        if not tunnels:
            print("No active tunnels running.")
            if Config.LOG_FILE.exists():
                print(f"\nTip: Check logs at: {Config.LOG_FILE}")
            return
        print(f"{'PID':<8} | {'Local Port':<12} | {'Public URL'}")
        print("-" * 75)
        for pid, info in tunnels.items():
            print(f"{pid:<8} | {info['local_port']:<12} | {info['url']}")
        print("-" * 75)

    def stop(self, target):
        tunnels = self.clean_dead()
        if not tunnels:
            print("No active tunnels to stop.")
            return

        stopped = 0
        for pid, info in list(tunnels.items()):
            if target == "all" or str(info["local_port"]) == str(target):
                try:
                    _kill_process(int(pid))
                    print(f"Stopped tunnel for port {info['local_port']} (PID: {pid})")
                    del tunnels[pid]
                    stopped += 1
                except Exception:
                    pass

        if stopped > 0:
            self.save(tunnels)
        else:
            print(f"No tunnel found matching: {target}")

    def _make_watchdog_cmd(self, ssh_cmd):
        if getattr(sys, "frozen", False):
            return [sys.executable, "_watchdog", json.dumps(ssh_cmd)]
        else:
            return [sys.executable, sys.argv[0], "_watchdog", json.dumps(ssh_cmd)]

    def restore(self):
        tunnels = self.load()
        if not tunnels:
            return

        print(f"Restoring {len(tunnels)} tunnel(s)...")
        new_tunnels = {}
        for _, info in tunnels.items():
            try:
                process = _spawn_watchdog(self._make_watchdog_cmd(info["ssh_cmd"]))
                new_tunnels[str(process.pid)] = info
            except Exception:
                pass

        self.save(new_tunnels)
        print("Restoration complete.")

    def start(self, username, default_subdomain, local_port, custom_domain=None):
        self.clean_dead()

        if custom_domain and custom_domain != username:
            custom_domain = self._check_domain(custom_domain, username)

        target_domain = custom_domain if custom_domain else default_subdomain
        full_url = f"https://{target_domain}.natnest.site"
        tunnel_uuid = str(uuid.uuid4())

        ssh_cmd = [
            "ssh",
            "-o", "StrictHostKeyChecking=no",
            "-o", "ExitOnForwardFailure=yes",
            "-o", "ServerAliveInterval=15",
            "-o", "ServerAliveCountMax=3",
            "-o", "PreferredAuthentications=publickey",
            "-o", "IdentitiesOnly=yes",
            "-o", "PasswordAuthentication=no",
            "-i", str(Config.KEY_FILE),
            "-p", "2222",
            "-N", "-T",
            "-R", f"0:127.0.0.1:{local_port}",
            f"{username}#{target_domain}#{tunnel_uuid}@{Config.SERVER_URL.replace('https://', '').replace('http://', '')}",
        ]

        print(f"Opening tunnel for port {local_port}...")
        assigned_server_port = self._preflight(ssh_cmd)

        watchdog_cmd = self._make_watchdog_cmd(ssh_cmd)
        process = _spawn_watchdog(watchdog_cmd)

        time.sleep(1.0)
        if process.poll() is not None:
            print("Error: Watchdog process failed to start.")
            print(f"Check logs at {Config.LOG_FILE} for details.")
            sys.exit(1)

        tunnels = self.load()
        tunnels[str(process.pid)] = {
            "local_port": local_port,
            "domain": target_domain,
            "url": full_url,
            "ssh_cmd": ssh_cmd,
            "start_time": time.time(),
        }
        self.save(tunnels)

        actual_url, actual_domain = self._verify_domain(
            full_url, target_domain, tunnel_uuid, assigned_server_port
        )

        tunnels = self.load()
        if str(process.pid) in tunnels:
            tunnels[str(process.pid)]["url"] = actual_url
            tunnels[str(process.pid)]["domain"] = actual_domain
            self.save(tunnels)

        print(f"\nTunnel established successfully! (PID: {process.pid})")
        print("\n" + "=" * 70)
        print(f" {'Internet':<25} {'NatNest Server':<20} {'Your Machine':<20}")
        print("-" * 70)
        print(f" {'[ External User ]':<22} =>  [ {actual_url} ]  =>  [ localhost:{local_port} ]")
        print(f" {'':<22}      (Encrypted Auto-reconnecting Tunnel)")
        print("=" * 70 + "\n")
        print("Use 'natnest status' to view active tunnels, or 'natnest stop all' to close.")

    def _check_domain(self, custom_domain, username):
        try:
            print(f"Checking availability for domain '{custom_domain}'...")
            resp = requests.get(
                f"{Config.SERVER_URL}/api/domain/check",
                params={"domain": custom_domain, "username": username},
                timeout=10,
            )
            if resp.status_code == 200:
                data = resp.json()
                if not data.get("available", False):
                    suggestion = data.get("suggestion", f"{custom_domain}-{username}")
                    print(f"Domain '{custom_domain}' is already in use.")
                    choice = input(f"Would you like to use '{suggestion}' instead? [Y/n]: ").strip().lower()
                    if choice in ("", "y", "yes"):
                        return suggestion
                    else:
                        print("Aborted.")
                        sys.exit(0)
                else:
                    return data.get("domain", custom_domain)
            else:
                print(f"Warning: Could not verify domain availability (HTTP {resp.status_code}). Proceeding...")
        except Exception as e:
            print(f"Warning: Domain check error: {e}. Proceeding...")
        return custom_domain

    def _preflight(self, ssh_cmd):
        assigned_server_port = None
        try:
            result = subprocess.run(ssh_cmd, capture_output=True, text=True, timeout=3.0)
            print("Failed to establish SSH connection.")
            if result.stderr:
                print(f"Server response:\n{result.stderr.strip()}")
            sys.exit(1)
        except subprocess.TimeoutExpired as e:
            err_output = e.stderr or ""
            if isinstance(err_output, bytes):
                err_output = err_output.decode("utf-8", errors="ignore")
            match = re.search(r"Allocated port (\d+)", err_output)
            if match:
                assigned_server_port = match.group(1)
        except Exception as e:
            print(f"Error verifying SSH connection: {e}")
            sys.exit(1)
        return assigned_server_port

    def _verify_domain(self, full_url, target_domain, tunnel_uuid, assigned_server_port):
        print("Verifying assigned domain...")
        time.sleep(3.0)
        actual_url = full_url
        actual_domain = target_domain
        try:
            from .auth import AuthManager
            user_data = AuthManager().get_session()
            headers = {}
            if user_data and user_data.get("token"):
                headers["Authorization"] = f"Bearer {user_data['token']}"
            resp = requests.get(f"{Config.SERVER_URL}/api/tunnels/me", headers=headers, timeout=5)
            if resp.status_code == 200:
                tunnels_data = resp.json().get("tunnels", [])
                for t in tunnels_data:
                    if tunnel_uuid and t.get("client_uuid") == tunnel_uuid:
                        actual_domain = t["domain"]
                        actual_url = f"https://{actual_domain}"
                        break
                    elif assigned_server_port and str(t.get("port")) == str(assigned_server_port):
                        actual_domain = t["domain"]
                        actual_url = f"https://{actual_domain}"
                        break
                    elif t.get("is_mine"):
                        actual_domain = t["domain"]
                        actual_url = f"https://{actual_domain}"
                        break
                    elif len(tunnels_data) == 1:
                        actual_domain = t["domain"]
                        actual_url = f"https://{actual_domain}"
                        break
        except Exception:
            pass
        return actual_url, actual_domain
