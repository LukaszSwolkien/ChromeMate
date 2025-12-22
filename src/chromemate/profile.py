"""Chrome profile discovery and management."""

import json
import platform
from dataclasses import dataclass
from pathlib import Path


@dataclass
class ChromeProfile:
    """Represents a Chrome profile."""

    name: str
    path: Path
    display_name: str | None = None

    def __post_init__(self) -> None:
        if self.display_name is None:
            self.display_name = self.name


def get_chrome_base_path() -> Path | None:
    """Get the base Chrome user data directory for the current OS."""
    system = platform.system()

    if system == "Darwin":  # macOS
        return Path.home() / "Library/Application Support/Google/Chrome"
    elif system == "Windows":
        local_app_data = Path.home() / "AppData/Local"
        return local_app_data / "Google/Chrome/User Data"
    elif system == "Linux":
        return Path.home() / ".config/google-chrome"

    return None


def discover_profiles() -> list[ChromeProfile]:
    """Discover all Chrome profiles on the system."""
    base_path = get_chrome_base_path()
    if base_path is None or not base_path.exists():
        return []

    profiles: list[ChromeProfile] = []

    # Check for Default profile
    default_path = base_path / "Default"
    if default_path.exists():
        display_name = _get_profile_display_name(default_path)
        profiles.append(ChromeProfile("Default", default_path, display_name))

    # Check for numbered profiles (Profile 1, Profile 2, etc.)
    for item in base_path.iterdir():
        if item.is_dir() and item.name.startswith("Profile "):
            display_name = _get_profile_display_name(item)
            profiles.append(ChromeProfile(item.name, item, display_name))

    return profiles


def _get_profile_display_name(profile_path: Path) -> str | None:
    """Extract the user-friendly profile name from Preferences."""
    prefs_path = profile_path / "Preferences"
    if not prefs_path.exists():
        return None

    try:
        with open(prefs_path, encoding="utf-8") as f:
            prefs = json.load(f)
        return prefs.get("profile", {}).get("name")
    except (json.JSONDecodeError, OSError):
        return None


def get_profile_by_name(name: str) -> ChromeProfile | None:
    """Get a specific profile by name."""
    profiles = discover_profiles()
    for profile in profiles:
        if profile.name == name or profile.display_name == name:
            return profile
    return None


