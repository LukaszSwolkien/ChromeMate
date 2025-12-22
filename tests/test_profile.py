"""Tests for profile discovery."""

import json
from pathlib import Path
from unittest.mock import patch

from chromemate.profile import ChromeProfile, _get_profile_display_name


def test_profile_display_name_from_preferences(temp_profile: Path) -> None:
    """Test extracting display name from Preferences."""
    prefs = {"profile": {"name": "Work Profile"}}
    prefs_file = temp_profile / "Preferences"
    prefs_file.write_text(json.dumps(prefs))

    display_name = _get_profile_display_name(temp_profile)

    assert display_name == "Work Profile"


def test_profile_display_name_handles_missing_file(temp_profile: Path) -> None:
    """Test handling when Preferences file is missing."""
    display_name = _get_profile_display_name(temp_profile)

    assert display_name is None


def test_profile_display_name_handles_invalid_json(temp_profile: Path) -> None:
    """Test handling when Preferences file is invalid."""
    prefs_file = temp_profile / "Preferences"
    prefs_file.write_text("not valid json")

    display_name = _get_profile_display_name(temp_profile)

    assert display_name is None


def test_chrome_profile_dataclass() -> None:
    """Test ChromeProfile dataclass initialization."""
    profile = ChromeProfile(name="Default", path=Path("/test"))

    assert profile.name == "Default"
    assert profile.display_name == "Default"  # Should default to name


def test_chrome_profile_with_display_name() -> None:
    """Test ChromeProfile with explicit display name."""
    profile = ChromeProfile(name="Profile 1", path=Path("/test"), display_name="Work")

    assert profile.name == "Profile 1"
    assert profile.display_name == "Work"


