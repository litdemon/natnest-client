import os
import sys
import subprocess
import time
import requests
import json
import shutil
import signal
import uuid
from pathlib import Path

# Configuration
VERSION = "0.5.0"
SERVER_URL = os.getenv("NATNEST_SERVER_URL", "https://natnest.site")
CONFIG_DIR = Path.home() / ".natnest"
KEY_FILE = CONFIG_DIR / "id_ed25519"
SESSION_FILE = CONFIG_DIR / "session.json"
TUNNELS_FILE = CONFIG_DIR / "tunnels.json"
LOG_FILE = CONFIG_DIR / "natnest.log"

def check_for_updates():
    """Checks if a new version is available on the server."""
    try:
        resp = requests.get(f"{SERVER_URL}/api/version", timeout=2)
        resp.raise_for_status()
        data = resp.json()
        latest_version = data.get("version")
        
        if latest_version:
            # Proper version comparison (e.g., 0.4.6 > 0.4.4)
            v_latest = [int(x) for x in latest_version.split('.')]
            v_current = [int(x) for x in VERSION.split('.')]
            if v_latest > v_current:
                return True, data.get("url"), latest_version
    except:
        pass
    return False, None, None

def perform_update(download_url):
    """Downloads the new binary and replaces the current one."""
    print("🚀 Updating NatNest to latest version...")
    try:
        # Resolve the path to the current executable
        exe_path = Path(sys.executable).resolve()
        new_exe = exe_path.with_suffix(".new")
        old_exe = exe_path.with_suffix(".old")

        # 1. Download the new binary
        print(f"📥 Downloading from {download_url}...")
        resp = requests.get(download_url, stream=True, timeout=30)
        resp.raise_for_status()
        with open(new_exe, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)
        
        # 2. Make it executable
        new_exe.chmod(0o755)

        # 3. Rename current to .old, move new to current (Safe on Linux/macOS)
        if old_exe.exists(): 
            try: old_exe.unlink()
            except: pass
            
        exe_path.rename(old_exe)
        new_exe.rename(exe_path)

        print("\n✨ Update successful!")
        print("   The binary has been replaced. Please run your command again.")
        sys.exit(0)
    except Exception as e:
        print(f"❌ Update failed: {e}")
        if 'new_exe' in locals() and new_exe.exists():
            try: new_exe.unlink()
            except: pass
        sys.exit(1)

def check_dependencies():
    if not shutil.which("ssh"):
        print("❌ Error: 'ssh' is not installed.")
        sys.exit(1)

def ensure_ssh_key():
    CONFIG_DIR.mkdir(mode=0o700, parents=True, exist_ok=True)
    if not KEY_FILE.exists():
        print("🔨 Generating new SSH key pair...")
        subprocess.run([
            "ssh-keygen", "-t", "ed25519", "-f", str(KEY_FILE), "-N", ""
        ], check=True, capture_output=True)
    with open(str(KEY_FILE) + ".pub", "r") as f:
        return f.read().strip()

def get_session():
    if SESSION_FILE.exists():
        try:
            with open(SESSION_FILE, "r") as f:
                return json.load(f)
        except:
            return None
    return None

def save_session(data):
    with open(SESSION_FILE, "w") as f:
        json.dump(data, f)

def load_tunnels():
    if TUNNELS_FILE.exists():
        try:
            with open(TUNNELS_FILE, "r") as f:
                return json.load(f)
        except:
            pass
    return {}

def save_tunnels(tunnels):
    with open(TUNNELS_FILE, "w") as f:
        json.dump(tunnels, f)

def is_pid_running(pid):
    try:
        os.kill(int(pid), 0)
        return True
    except OSError:
        return False

def clean_dead_tunnels():
    tunnels = load_tunnels()
    active_tunnels = {}
    changed = False
    for pid, info in tunnels.items():
        if is_pid_running(pid):
            active_tunnels[pid] = info
        else:
            changed = True
    if changed:
        save_tunnels(active_tunnels)
    return active_tunnels

def authenticate(public_key):
    print("🌐 Connecting to NatNest for authentication...")
    try:
        resp = requests.post(f"{SERVER_URL}/api/auth/device", json={"public_key": public_key}, timeout=10)
        resp.raise_for_status()
        auth_data = resp.json()
    except Exception as e:
        print(f"❌ Failed to connect to server: {e}")
        sys.exit(1)

    print("\n" + "="*50)
    print("  GOOGLE LOGIN REQUIRED")
    print("="*50)
    print(f"1. Open this URL in your browser:\n   {auth_data['verification_url']}")
    print(f"\n2. Enter this code:\n   {auth_data['user_code']}")
    print("="*50)
    print("\nWaiting for approval...")

    device_code = auth_data['device_code']
    interval = auth_data.get('interval', 5)
    
    while True:
        try:
            resp = requests.post(f"{SERVER_URL}/api/auth/token", json={"device_code": device_code}, timeout=10)
            if resp.status_code == 200:
                user_data = resp.json()
                print(f"\n✅ Authentication successful! Welcome, {user_data['email']}.")
                save_session(user_data)
                return user_data
            
            error = resp.json().get('error')
            if error == "authorization_pending":
                time.sleep(interval)
                continue
            else:
                print(f"❌ Authentication failed: {error}")
                sys.exit(1)
        except Exception as e:
            print(f"❌ Error: {e}")
            sys.exit(1)

def run_watchdog(ssh_cmd):
    """SSH 연결을 감시하고 재시작하는 백그라운드 루프"""
    # 로그 파일 설정
    def log(msg):
        with open(LOG_FILE, "a") as f:
            f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}\n")

    log(f"Watchdog started for command: {' '.join(ssh_cmd)}")
    
    # 시그널 핸들러
    def handle_sigterm(signum, frame):
        log("Watchdog received SIGTERM, exiting...")
        sys.exit(0)
    
    signal.signal(signal.SIGTERM, handle_sigterm)
    signal.signal(signal.SIGINT, signal.SIG_IGN)

    while True:
        log("Attempting to open SSH tunnel...")
        try:
            # -o ServerAliveInterval 등을 통해 연결 끊김을 감지하면 ssh 프로세스가 종료됨
            result = subprocess.run(ssh_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            log(f"SSH process exited with code {result.returncode}")
        except Exception as e:
            log(f"Error running SSH: {e}")
        
        log("Waiting 5 seconds before reconnecting...")
        time.sleep(5)

def start_tunnel(username, default_subdomain, local_port, custom_domain=None):
    clean_dead_tunnels()
    
    # Check custom domain availability with the server
    if custom_domain and custom_domain != username:
        try:
            print(f"🔍 Checking availability for domain '{custom_domain}'...")
            resp = requests.get(f"{SERVER_URL}/api/domain/check", params={"domain": custom_domain, "username": username}, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                if not data.get("available", False):
                    suggestion = data.get("suggestion", f"{custom_domain}-{username}")
                    print(f"⚠️  Domain '{custom_domain}' is already in use.")
                    choice = input(f"Would you like to use '{suggestion}' instead? [Y/n]: ").strip().lower()
                    if choice in ('', 'y', 'yes'):
                        custom_domain = suggestion
                    else:
                        print("❌ Aborted.")
                        sys.exit(0)
                else:
                    custom_domain = data.get("domain", custom_domain)
            else:
                print(f"⚠️ Failed to verify domain availability (HTTP {resp.status_code}). Proceeding anyway...")
        except Exception as e:
            print(f"⚠️ Error checking domain availability: {e}. Proceeding anyway...")

    target_domain = custom_domain if custom_domain else default_subdomain
    full_url = f"https://{target_domain}.natnest.site"
    tunnel_uuid = str(uuid.uuid4())

    # Use 0 as listen port to let server assign a random port
    ssh_cmd = [
        "ssh", "-o", "StrictHostKeyChecking=no", "-o", "ExitOnForwardFailure=yes",
        "-o", "ServerAliveInterval=15", "-o", "ServerAliveCountMax=3",
        "-o", "PreferredAuthentications=publickey", "-o", "IdentitiesOnly=yes",
        "-o", "PasswordAuthentication=no",
        "-i", str(KEY_FILE), "-p", "2222",
        "-N", "-T",
        "-R", f"0:127.0.0.1:{local_port}", f"{username}#{target_domain}#{tunnel_uuid}@{SERVER_URL.replace('https://', '')}"
    ]

    try:
        # We need to capture the assigned port from SSH output
        # But since we run it in background via watchdog, we'll try to parse it from the log or initial run
        # Pre-flight check: Run the actual SSH command for 3 seconds to verify authentication
        assigned_server_port = None
        print(f"🚀 Opening tunnel for port {local_port}...")
        try:
            # If it fails authentication, it will exit immediately.
            # If it succeeds, it will block forever, and we catch the TimeoutExpired.
            result = subprocess.run(ssh_cmd, capture_output=True, text=True, timeout=3.0)
            print(f"❌ Failed to establish SSH connection.")
            if result.stderr:
                print(f"Server response:\n{result.stderr.strip()}")
            sys.exit(1)
        except subprocess.TimeoutExpired as e:
            # Tunnel is alive and authenticated successfully
            err_output = e.stderr if e.stderr else ""
            if isinstance(err_output, bytes):
                err_output = err_output.decode('utf-8', errors='ignore')
            import re
            match = re.search(r"Allocated port (\d+)", err_output)
            if match:
                assigned_server_port = match.group(1)
        except Exception as e:
            print(f"❌ Error verifying SSH connection: {e}")
            sys.exit(1)

        # PyInstaller 환경과 일반 Python 환경 모두 대응
        if getattr(sys, 'frozen', False):
            watchdog_cmd = [sys.executable, "_watchdog", json.dumps(ssh_cmd)]
        else:
            watchdog_cmd = [sys.executable, sys.argv[0], "_watchdog", json.dumps(ssh_cmd)]

        process = subprocess.Popen(
            watchdog_cmd,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True
        )
        
        # 잠시 대기하며 프로세스가 즉시 죽는지 확인
        time.sleep(1.0)
        if process.poll() is not None:
            print("❌ Error: Watchdog process failed to start.")
            print(f"Check logs at {LOG_FILE} for details.")
            sys.exit(1)

        tunnels = load_tunnels()
        tunnels[str(process.pid)] = {
            "local_port": local_port,
            "domain": target_domain,
            "url": full_url,
            "ssh_cmd": ssh_cmd,
            "start_time": time.time()
        }
        save_tunnels(tunnels)

        # Wait a moment for server-side registration, then fetch actual domain
        print("⏳ Verifying assigned domain...")
        time.sleep(3.0)
        actual_url = full_url
        actual_domain = target_domain
        try:
            user_data = get_session()
            headers = {}
            if user_data and user_data.get('token'):
                headers["Authorization"] = f"Bearer {user_data['token']}"
            resp = requests.get(f"{SERVER_URL}/api/tunnels/me", headers=headers, timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                tunnels_data = data.get("tunnels", [])
                for t in tunnels_data:
                    # Priority 1: Match by client_uuid
                    if tunnel_uuid and t.get("client_uuid") == tunnel_uuid:
                        actual_domain = t['domain']
                        actual_url = f"https://{actual_domain}"
                        break
                    # Priority 2: Match by server-assigned port
                    elif assigned_server_port and str(t.get("port")) == str(assigned_server_port):
                        actual_domain = t['domain']
                        actual_url = f"https://{actual_domain}"
                        break
                    # Priority 3: Marked as mine by server (IP match)
                    elif t.get("is_mine"):
                        actual_domain = t['domain']
                        actual_url = f"https://{actual_domain}"
                        break
                    # Priority 4: Fallback for single tunnel
                    elif len(tunnels_data) == 1:
                        actual_domain = t['domain']
                        actual_url = f"https://{actual_domain}"
                        break
        except Exception:
            pass

        # Update saved tunnel info with actual URL/domain
        tunnels = load_tunnels()
        if str(process.pid) in tunnels:
            tunnels[str(process.pid)]["url"] = actual_url
            tunnels[str(process.pid)]["domain"] = actual_domain
            save_tunnels(tunnels)

        print(f"\n✅ Tunnel established successfully! (PID: {process.pid})")
        print("\n" + "=" * 70)
        print(f" {'🌐 Internet':<25} {'🛡️ NatNest Server':<20} {'💻 Your Machine':<20}")
        print("-" * 70)
        print(f" {'[ External User ]':<22} =>  [ {actual_url} ]  =>  [ localhost:{local_port} ]")
        print(f" {'':<22}      (Encrypted Auto-reconnecting Tunnel)")
        print("=" * 70 + "\n")
        print("Use 'natnest status' to view active tunnels, or 'natnest stop all' to close.")

    except Exception as e:
        print(f"❌ Error starting tunnel: {e}")

def restore_tunnels():
    tunnels = load_tunnels()
    if not tunnels:
        return
    
    print(f"🔄 Restoring {len(tunnels)} tunnels...")
    new_tunnels = {}
    
    for _, info in tunnels.items():
        try:
            if getattr(sys, 'frozen', False):
                watchdog_cmd = [sys.executable, "_watchdog", json.dumps(info["ssh_cmd"])]
            else:
                watchdog_cmd = [sys.executable, sys.argv[0], "_watchdog", json.dumps(info["ssh_cmd"])]
                
            process = subprocess.Popen(
                watchdog_cmd,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True
            )
            new_tunnels[str(process.pid)] = info
            new_tunnels[str(process.pid)]["ssh_cmd"] = info["ssh_cmd"]
        except:
            pass
    
    save_tunnels(new_tunnels)
    print(f"✅ Restoration complete.")

def setup_autostart():
    exe_path = os.path.abspath(sys.argv[0])
    
    if sys.platform.startswith("linux"):
        service_dir = Path.home() / ".config" / "systemd" / "user"
        service_dir.mkdir(parents=True, exist_ok=True)
        service_file = service_dir / "natnest.service"
        
        content = f"""[Unit]
Description=NatNest Tunnel Restorer
After=network.target

[Service]
Type=oneshot
ExecStart={exe_path} restore
RemainAfterExit=yes

[Install]
WantedBy=default.target
"""
        with open(service_file, "w") as f:
            f.write(content)
        
        try:
            subprocess.run(["systemctl", "--user", "daemon-reload"], check=True)
            subprocess.run(["systemctl", "--user", "enable", "natnest.service"], check=True)
            print("✅ Auto-start enabled for Linux (Systemd).")
        except Exception as e:
            print(f"❌ Failed: {e}")

    elif sys.platform == "darwin":
        plist_dir = Path.home() / "Library" / "LaunchAgents"
        plist_dir.mkdir(parents=True, exist_ok=True)
        plist_file = plist_dir / "com.natnest.tunnel.plist"
        
        content = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.natnest.tunnel</string>
    <key>ProgramArguments</key>
    <array>
        <string>{exe_path}</string>
        <string>restore</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
</dict>
</plist>
"""
        with open(plist_file, "w") as f:
            f.write(content)
        print("✅ Auto-start enabled for macOS.")
    else:
        print("❌ Unsupported OS.")

def print_status():
    tunnels = clean_dead_tunnels()
    print(f"🦉 NatNest Active Tunnels (v{VERSION})")
    print("-" * 75)
    if not tunnels:
        print("No active tunnels running.")
        if LOG_FILE.exists():
            print(f"\nTip: If you expected tunnels to be running, check: {LOG_FILE}")
        return

    print(f"{'PID':<8} | {'Local Port':<12} | {'Public URL'}")
    print("-" * 75)
    for pid, info in tunnels.items():
        print(f"{pid:<8} | {info['local_port']:<12} | {info['url']}")
    print("-" * 75)

def stop_tunnel(target):
    tunnels = clean_dead_tunnels()
    if not tunnels:
        print("No active tunnels to stop.")
        return

    stopped = 0
    for pid, info in list(tunnels.items()):
        if target == "all" or str(info['local_port']) == str(target):
            try:
                # 프로세스 그룹 전체 종료 (Watchdog + SSH)
                os.killpg(int(pid), signal.SIGTERM)
                print(f"🛑 Stopped tunnel for port {info['local_port']} (PID: {pid})")
                del tunnels[pid]
                stopped += 1
            except OSError:
                try:
                    os.kill(int(pid), signal.SIGTERM)
                    del tunnels[pid]
                    stopped += 1
                except:
                    pass
    
    if stopped > 0:
        save_tunnels(tunnels)
    else:
        print(f"⚠️ No tunnel found matching: {target}")

def print_usage():
    print(f"🦉 NatNest Client v{VERSION}")
    print("\nUsage:")
    print("  natnest <port>                 # Open a background tunnel")
    print("  natnest start <port>           # Alias for opening a tunnel")
    print("  natnest <port> <custom_domain> # Open a tunnel with custom subdomain")
    print("  natnest status                 # List all active tunnels")
    print("  natnest stop <port|all>        # Stop tunnels")
    print("  natnest setup                  # Link Google account")
    print("  natnest autostart              # Enable auto-start on reboot")
    print("  natnest update                 # Update to latest version")

def main():
    if len(sys.argv) < 2:
        print_usage()
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command in ["--version", "-v"]:
        print(f"🦉 NatNest Client v{VERSION}")
        sys.exit(0)

    if command == "_watchdog":
        if len(sys.argv) < 3: sys.exit(1)
        ssh_cmd = json.loads(sys.argv[2])
        run_watchdog(ssh_cmd)
        sys.exit(0)

    if command == "restore":
        restore_tunnels()
        sys.exit(0)

    if command == "update":
        available, url, version = check_for_updates()
        if available:
            perform_update(url)
        else:
            print("✨ You are already using the latest version.")
        sys.exit(0)

    # Auto-check for updates (silent if no update)
    if command != "_watchdog" and sys.stdout.isatty():
        available, url, version = check_for_updates()
        if available:
            print(f"🔔 A new version of NatNest is available: {version}")
            print(f"   Run 'natnest update' to upgrade.\n")

    check_dependencies()

    if command == "setup":
        print("\n[Setup] Initializing NatNest...")
        pub_key = ensure_ssh_key()
        user_data = get_session()
        if user_data:
            print(f"✨ Already authenticated as {user_data['email']}.")
        else:
            user_data = authenticate(pub_key)
            print("\n🎉 Setup complete!")
        sys.exit(0)

    elif command == "status":
        print_status()
        sys.exit(0)

    elif command == "stop":
        if len(sys.argv) < 3:
            print("❌ Specify port or 'all'")
            sys.exit(1)
        stop_tunnel(sys.argv[2])
        sys.exit(0)
        
    elif command == "autostart":
        setup_autostart()
        sys.exit(0)

    elif command == "start":
        if len(sys.argv) < 3:
            print("❌ Specify port to expose (e.g. 8080)")
            sys.exit(1)
        
        local_port = sys.argv[2]
        custom_domain = sys.argv[3] if len(sys.argv) > 3 else None
        
        user_data = get_session()
        if not user_data:
            print("\n❌ Error: Not authenticated. Run 'natnest setup' first.")
            sys.exit(1)
            
        start_tunnel(user_data['username'], user_data['subdomain'], local_port, custom_domain)
        sys.exit(0)

    if not command.isdigit():
        print(f"❌ Invalid argument: {command}")
        sys.exit(1)

    local_port = command
    custom_domain = sys.argv[2] if len(sys.argv) > 2 else None
    
    user_data = get_session()
    if not user_data:
        print("\n❌ Error: Not authenticated. Run 'natnest setup' first.")
        sys.exit(1)
        
    start_tunnel(user_data['username'], user_data['subdomain'], local_port, custom_domain)

if __name__ == "__main__":
    main()
