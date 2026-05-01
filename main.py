import json
import shutil
import sys

from src.auth import AuthManager
from src.autostart import AutostartManager
from src.config import Config
from src.tunnel import TunnelManager
from src.updater import Updater
from src.watchdog import Watchdog


def print_usage():
    print(f"NatNest Client v{Config.VERSION}")
    print("\nUsage:")
    print("  natnest <port>                 # Open a background tunnel")
    print("  natnest start <port>           # Alias for opening a tunnel")
    print("  natnest <port> <custom_domain> # Open a tunnel with custom subdomain")
    print("  natnest status                 # List all active tunnels")
    print("  natnest stop <port|all>        # Stop tunnels")
    print("  natnest setup                  # Link Google account")
    print("  natnest autostart              # Enable auto-start on reboot")
    print("  natnest update                 # Update to latest version")


def check_ssh():
    if not shutil.which("ssh"):
        print("Error: 'ssh' is not installed or not in PATH.")
        print("On Windows 10/11, enable OpenSSH in Settings > Optional features.")
        sys.exit(1)


def require_session(auth):
    user_data = auth.get_session()
    if not user_data:
        print("\nError: Not authenticated. Run 'natnest setup' first.")
        sys.exit(1)
    return user_data


def main():
    if len(sys.argv) < 2:
        print_usage()
        sys.exit(1)

    command = sys.argv[1]

    if command in ["--version", "-v"]:
        print(f"NatNest Client v{Config.VERSION}")
        sys.exit(0)

    # Internal watchdog subprocess entry point
    if command == "_watchdog":
        if len(sys.argv) < 3:
            sys.exit(1)
        ssh_cmd = json.loads(sys.argv[2])
        Watchdog().run(ssh_cmd)
        sys.exit(0)

    if command == "restore":
        TunnelManager().restore()
        sys.exit(0)

    if command == "update":
        updater = Updater()
        available, url, version = updater.check()
        if available:
            updater.perform(url)
        else:
            print("You are already using the latest version.")
        sys.exit(0)

    # Silent update check on interactive terminal
    if sys.stdout.isatty():
        available, url, version = Updater().check()
        if available:
            print(f"A new version of NatNest is available: {version}")
            print("   Run 'natnest update' to upgrade.\n")

    check_ssh()

    auth = AuthManager()
    tunnels = TunnelManager()

    if command == "setup":
        print("\n[Setup] Initializing NatNest...")
        pub_key = auth.ensure_ssh_key()
        user_data = auth.get_session()
        if user_data:
            print(f"Already authenticated as {user_data['email']}.")
        else:
            auth.authenticate(pub_key)
            print("\nSetup complete!")
        sys.exit(0)

    elif command == "status":
        tunnels.status()
        sys.exit(0)

    elif command == "stop":
        if len(sys.argv) < 3:
            print("Error: Specify port or 'all'")
            sys.exit(1)
        tunnels.stop(sys.argv[2])
        sys.exit(0)

    elif command == "autostart":
        AutostartManager().setup()
        sys.exit(0)

    elif command == "start":
        if len(sys.argv) < 3:
            print("Error: Specify port to expose (e.g. natnest start 8080)")
            sys.exit(1)
        user_data = require_session(auth)
        local_port = sys.argv[2]
        custom_domain = sys.argv[3] if len(sys.argv) > 3 else None
        tunnels.start(user_data["username"], user_data["subdomain"], local_port, custom_domain)
        sys.exit(0)

    elif command.isdigit():
        user_data = require_session(auth)
        local_port = command
        custom_domain = sys.argv[2] if len(sys.argv) > 2 else None
        tunnels.start(user_data["username"], user_data["subdomain"], local_port, custom_domain)

    else:
        print(f"Error: Invalid argument: {command}")
        print_usage()
        sys.exit(1)


if __name__ == "__main__":
    main()
