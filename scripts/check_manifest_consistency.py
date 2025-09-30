#!/usr/bin/env python3
"""
Check manifest.json consistency with pyproject.toml.

This script verifies that the version and dependencies in manifest.json
are in sync with the corresponding values in pyproject.toml.
"""

import json
import sys
import tomllib
from pathlib import Path


def load_pyproject_toml(pyproject_path: Path) -> dict:
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


def load_manifest_json(manifest_path: Path) -> dict:
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


def main() -> int:
    """Main function to check manifest consistency."""
    workspace_root = Path(__file__).parent.parent
    pyproject_path = workspace_root / "pyproject.toml"
    manifest_path = (
        workspace_root / "custom_components" / "inworld_tts" / "manifest.json"
    )

    print("Checking manifest.json consistency with pyproject.toml...")
    print(f"Project config: {pyproject_path}")
    print(f"Manifest file: {manifest_path}")
    print()

    # Load files
    pyproject_data = load_pyproject_toml(pyproject_path)
    manifest_data = load_manifest_json(manifest_path)

    # Extract data from pyproject.toml
    project_config = pyproject_data.get("project", {})
    expected_version = project_config.get("version", "")
    dependencies = project_config.get("dependencies", [])

    if not expected_version:
        print("❌ No version found in pyproject.toml")
        return 1

    # Get current values from manifest.json
    current_version = manifest_data.get("version", "")
    current_requirements = manifest_data.get("requirements", [])

    expected_requirements = extract_requirements_from_dependencies(dependencies)

    print(f"Expected version: {expected_version}")
    print(f"Manifest version: {current_version}")
    print(f"Expected requirements: {expected_requirements}")
    print(f"Manifest requirements: {current_requirements}")
    print()

    # Compare values
    version_in_sync = current_version == expected_version
    requirements_in_sync = current_requirements == expected_requirements

    issues = []

    if not version_in_sync:
        issues.append(
            f"Version mismatch: manifest.json has '{current_version}', "
            f"pyproject.toml has '{expected_version}'"
        )

    if not requirements_in_sync:
        issues.append("Requirements mismatch:")
        for req in current_requirements:
            if req not in expected_requirements:
                issues.append(f"  - {req} (in manifest.json but not expected)")
        for req in expected_requirements:
            if req not in current_requirements:
                issues.append(f"  + {req} (expected but not in manifest.json)")

    if issues:
        print("❌ manifest.json is inconsistent with pyproject.toml!")
        for issue in issues:
            print(issue)
        print()
        print("Recommendation:")
        print(
            "Update manifest.json to match the version and requirements in pyproject.toml"
        )
        return 1
    else:
        print("✅ manifest.json is consistent with pyproject.toml!")
        return 0


if __name__ == "__main__":
    sys.exit(main())
