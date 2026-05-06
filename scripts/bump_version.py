#!/usr/bin/env python3
"""Version bump utility.

Usage:
    python scripts/bump_version.py patch   # 0.5.0 -> 0.5.1  (default)
    python scripts/bump_version.py minor   # 0.5.0 -> 0.6.0
    python scripts/bump_version.py major   # 0.5.0 -> 1.0.0
    python scripts/bump_version.py 1.2.3   # set explicit version
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
VERSION_FILE = ROOT / "VERSION"


def read_version() -> str:
    return VERSION_FILE.read_text(encoding="utf-8").strip()


def bump(current: str, part: str) -> str:
    major, minor, patch = map(int, current.split("."))
    if part == "major":
        return f"{major + 1}.0.0"
    elif part == "minor":
        return f"{major}.{minor + 1}.0"
    else:
        return f"{major}.{minor}.{patch + 1}"


def write_version(new_version: str) -> None:
    # Validate semver format
    if not re.fullmatch(r"\d+\.\d+\.\d+", new_version):
        print(f"Error: '{new_version}' is not a valid semver (e.g. 1.2.3)")
        sys.exit(1)

    VERSION_FILE.write_text(new_version + "\n", encoding="utf-8")
    print(f"VERSION file updated: {new_version}")


def main() -> None:
    current = read_version()
    part = sys.argv[1] if len(sys.argv) > 1 else "patch"

    if re.fullmatch(r"\d+\.\d+\.\d+", part):
        new_version = part
    elif part in ("major", "minor", "patch"):
        new_version = bump(current, part)
    else:
        print(__doc__)
        sys.exit(1)

    write_version(new_version)
    print(f"  {current} -> {new_version}")
    print(f"\nNext steps:")
    print(f"  git add VERSION")
    print(f"  git commit -m 'chore: bump version to {new_version}'")
    print(f"  git tag v{new_version}")


if __name__ == "__main__":
    main()
