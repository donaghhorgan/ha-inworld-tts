#!/usr/bin/env python3
"""
Script to sync manifest.json with pyproject.toml

This script reads the version and dependencies from pyproject.toml and updates
the corresponding fields in the Home Assistant custom component manifest.json file.

Can run in two modes:
- Sync mode (default): Updates manifest.json with data from pyproject.toml
- Check mode (--check): Validates that manifest.json is in sync, exits 1 if not
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any

try:
    import tomllib
except ImportError:
    # Python < 3.11 fallback
    try:
        import tomli as tomllib  # type: ignore
    except ImportError:
        print("Error: tomli package required for Python < 3.11")
        print("Install with: pip install tomli")
        sys.exit(1)


def load_pyproject_toml(pyproject_path: Path) -> dict[str, Any]:
    """Load and parse pyproject.toml file."""
    try:
        with open(pyproject_path, "rb") as f:
            return tomllib.load(f)
    except FileNotFoundError:
        print(f"Error: {pyproject_path} not found!")
        sys.exit(1)
    except Exception as e:
        print(f"Error reading {pyproject_path}: {e}")
        sys.exit(1)


def load_manifest_json(manifest_path: Path) -> dict[str, Any]:
    """Load and parse manifest.json file."""
    try:
        with open(manifest_path, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: {manifest_path} not found!")
        sys.exit(1)
    except Exception as e:
        print(f"Error reading {manifest_path}: {e}")
        sys.exit(1)


def extract_requirements_from_dependencies(dependencies: list[str]) -> list[str]:
    """
    Extract requirements for manifest.json from pyproject.toml dependencies.

    Filters out homeassistant and other Home Assistant specific packages.
    """
    ha_packages = {"homeassistant", "voluptuous"}
    requirements = []

    for dep in dependencies:
        # Split package name from version constraint
        package_name = (
            dep.split(">=")[0]
            .split("==")[0]
            .split("~")[0]
            .split("<")[0]
            .split(">")[0]
            .strip()
        )

        # Skip Home Assistant specific packages
        if package_name.lower() not in ha_packages:
            requirements.append(dep)

    return sorted(requirements)


def check_manifest_sync_with_pyproject(project_root: Path) -> bool:
    """
    Check if manifest.json is in sync with pyproject.toml.

    Returns True if in sync, False otherwise.
    """
    pyproject_path = project_root / "pyproject.toml"
    manifest_path = project_root / "custom_components" / "inworld_tts" / "manifest.json"

    # Load files
    pyproject_data = load_pyproject_toml(pyproject_path)
    manifest_data = load_manifest_json(manifest_path)

    # Extract data from pyproject.toml
    project_config = pyproject_data.get("project", {})
    version = project_config.get("version", "")
    dependencies = project_config.get("dependencies", [])

    if not version:
        print("Warning: No version found in pyproject.toml")
        return False

    # Check current values in manifest.json
    current_version = manifest_data.get("version", "")
    current_requirements = manifest_data.get("requirements", [])

    expected_requirements = extract_requirements_from_dependencies(dependencies)

    # Compare values
    version_in_sync = current_version == version
    requirements_in_sync = current_requirements == expected_requirements

    if not version_in_sync:
        print(
            f"❌ Version mismatch: manifest.json has '{current_version}', pyproject.toml has '{version}'"
        )

    if not requirements_in_sync:
        print("❌ Requirements mismatch:")
        for req in current_requirements:
            if req not in expected_requirements:
                print(f"  - {req} (in manifest.json but not expected)")
        for req in expected_requirements:
            if req not in current_requirements:
                print(f"  + {req} (expected but not in manifest.json)")

    is_in_sync = version_in_sync and requirements_in_sync

    if is_in_sync:
        print("✅ manifest.json is in sync with pyproject.toml")

    return is_in_sync


def sync_manifest_with_pyproject(project_root: Path) -> None:
    """
    Sync manifest.json with pyproject.toml.

    Updates version and requirements in manifest.json based on pyproject.toml.
    """
    pyproject_path = project_root / "pyproject.toml"
    manifest_path = project_root / "custom_components" / "inworld_tts" / "manifest.json"

    # Load files
    pyproject_data = load_pyproject_toml(pyproject_path)
    manifest_data = load_manifest_json(manifest_path)

    # Extract data from pyproject.toml
    project_config = pyproject_data.get("project", {})
    version = project_config.get("version", "")
    dependencies = project_config.get("dependencies", [])

    if not version:
        print("Warning: No version found in pyproject.toml")
        return

    # Update manifest.json
    old_version = manifest_data.get("version", "")
    old_requirements = manifest_data.get("requirements", [])

    new_requirements = extract_requirements_from_dependencies(dependencies)

    manifest_data["version"] = version
    manifest_data["requirements"] = new_requirements

    # Save updated manifest.json
    try:
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest_data, f, indent=2, ensure_ascii=False)
        print(f"✅ Successfully updated {manifest_path}")
    except Exception as e:
        print(f"Error writing {manifest_path}: {e}")
        sys.exit(1)

    # Report changes
    print(f"Version: {old_version} → {version}")
    if old_requirements != new_requirements:
        print("Requirements updated:")
        for req in old_requirements:
            if req not in new_requirements:
                print(f"  - {req}")
        for req in new_requirements:
            if req not in old_requirements:
                print(f"  + {req}")
    else:
        print("Requirements: no changes")


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Sync manifest.json with pyproject.toml or check if they are in sync"
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Check if manifest.json is in sync with pyproject.toml (exits 1 if not)",
    )

    args = parser.parse_args()

    # Determine project root (parent of scripts directory)
    script_dir = Path(__file__).parent.absolute()
    project_root = script_dir.parent

    # Check if we're in the right directory
    pyproject_path = project_root / "pyproject.toml"
    if not pyproject_path.exists():
        print(f"Error: pyproject.toml not found in {project_root}")
        print("Please run this script from the project root directory.")
        sys.exit(1)

    manifest_path = project_root / "custom_components" / "inworld_tts" / "manifest.json"
    if not manifest_path.exists():
        print(f"Error: manifest.json not found at {manifest_path}")
        sys.exit(1)

    print(f"Project root: {project_root}")

    if args.check:
        print("Checking if manifest.json is in sync with pyproject.toml...")
        is_in_sync = check_manifest_sync_with_pyproject(project_root)
        if not is_in_sync:
            print("\n❌ manifest.json is NOT in sync with pyproject.toml")
            print("Run 'python sync_manifest.py' to update manifest.json")
            sys.exit(1)
        else:
            print("\n✅ All checks passed!")
    else:
        print("Syncing manifest.json with pyproject.toml...")
        sync_manifest_with_pyproject(project_root)


if __name__ == "__main__":
    main()
