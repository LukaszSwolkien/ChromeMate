"""Extension analysis for Chrome profiles."""

import json
from dataclasses import dataclass, field
from pathlib import Path

# Chrome extension state values
EXTENSION_STATE_ENABLED = 1
EXTENSION_STATE_DISABLED = 0


@dataclass
class Extension:
    """Represents a Chrome extension."""

    id: str
    name: str
    version: str
    enabled: bool
    description: str = ""
    webstore_url: str = ""

    def __post_init__(self) -> None:
        if not self.webstore_url and self.id:
            self.webstore_url = f"https://chromewebstore.google.com/detail/{self.id}"


@dataclass
class ExtensionsAnalyzer:
    """Analyzes installed extensions from a Chrome profile."""

    profile_path: Path
    extensions: list[Extension] = field(default_factory=list)

    def analyze(self) -> list[Extension]:
        """Analyze installed extensions from the profile."""
        self.extensions = []

        # Get extension settings from Preferences
        prefs_path = self.profile_path / "Preferences"
        if not prefs_path.exists():
            return []

        try:
            with open(prefs_path, encoding="utf-8") as f:
                prefs = json.load(f)
        except (json.JSONDecodeError, OSError):
            return []

        extensions_settings = prefs.get("extensions", {}).get("settings", {})

        for ext_id, settings in extensions_settings.items():
            # Skip component extensions and themes
            if settings.get("from_webstore") is False:
                continue

            manifest = settings.get("manifest", {})
            state = settings.get("state", EXTENSION_STATE_DISABLED)
            enabled = state == EXTENSION_STATE_ENABLED

            self.extensions.append(
                Extension(
                    id=ext_id,
                    name=manifest.get("name", ext_id),
                    version=manifest.get("version", ""),
                    enabled=enabled,
                    description=manifest.get("description", ""),
                )
            )

        return self.extensions

    def get_enabled(self) -> list[Extension]:
        """Get only enabled extensions."""
        return [ext for ext in self.extensions if ext.enabled]

    def get_disabled(self) -> list[Extension]:
        """Get only disabled extensions."""
        return [ext for ext in self.extensions if not ext.enabled]


