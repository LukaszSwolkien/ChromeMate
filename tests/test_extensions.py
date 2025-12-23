"""Tests for extensions analyzer."""

from pathlib import Path

from chromemate.analyzers.extensions import ExtensionsAnalyzer


def test_extensions_reads_from_preferences(
    temp_profile: Path, sample_preferences: Path
) -> None:
    """Test reading extensions from Preferences file."""
    analyzer = ExtensionsAnalyzer(temp_profile)
    extensions = analyzer.analyze()

    assert len(extensions) == 3


def test_extensions_identifies_enabled(
    temp_profile: Path, sample_preferences: Path
) -> None:
    """Test identifying enabled extensions."""
    analyzer = ExtensionsAnalyzer(temp_profile)
    analyzer.analyze()
    enabled = analyzer.get_enabled()

    assert len(enabled) == 2
    names = [e.name for e in enabled]
    assert "uBlock Origin" in names
    assert "Dark Reader" in names


def test_extensions_identifies_disabled(
    temp_profile: Path, sample_preferences: Path
) -> None:
    """Test identifying disabled extensions."""
    analyzer = ExtensionsAnalyzer(temp_profile)
    analyzer.analyze()
    disabled = analyzer.get_disabled()

    assert len(disabled) == 1
    assert disabled[0].name == "Old Extension"


def test_extensions_generates_webstore_url(
    temp_profile: Path, sample_preferences: Path
) -> None:
    """Test that webstore URLs are generated."""
    analyzer = ExtensionsAnalyzer(temp_profile)
    extensions = analyzer.analyze()

    for ext in extensions:
        assert ext.webstore_url.startswith("https://chromewebstore.google.com/detail/")
        assert ext.id in ext.webstore_url


def test_extensions_handles_missing_preferences(temp_profile: Path) -> None:
    """Test graceful handling when Preferences file doesn't exist."""
    analyzer = ExtensionsAnalyzer(temp_profile)
    extensions = analyzer.analyze()

    assert extensions == []




