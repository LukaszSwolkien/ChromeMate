"""Tests for bookmarks analyzer."""

from pathlib import Path

from chromemate.analyzers.bookmarks import BookmarksAnalyzer


def test_bookmarks_parses_flat_bookmarks(temp_profile: Path, sample_bookmarks: Path) -> None:
    """Test parsing bookmarks at the root level."""
    analyzer = BookmarksAnalyzer(temp_profile)
    bookmarks = analyzer.analyze()

    # Should find GitHub at bookmark bar root
    github = next((b for b in bookmarks if b.name == "GitHub"), None)
    assert github is not None
    assert github.url == "https://github.com"


def test_bookmarks_parses_nested_folders(temp_profile: Path, sample_bookmarks: Path) -> None:
    """Test parsing bookmarks inside folders."""
    analyzer = BookmarksAnalyzer(temp_profile)
    bookmarks = analyzer.analyze()

    # Should find Jira inside Work folder
    jira = next((b for b in bookmarks if b.name == "Jira"), None)
    assert jira is not None
    assert "Work" in jira.path
    assert jira.url == "https://jira.example.com"


def test_bookmarks_counts_total_correctly(temp_profile: Path, sample_bookmarks: Path) -> None:
    """Test that all bookmarks are counted."""
    analyzer = BookmarksAnalyzer(temp_profile)
    bookmarks = analyzer.analyze()

    # GitHub, Jira, Confluence, Stack Overflow = 4
    assert len(bookmarks) == 4


def test_bookmarks_handles_missing_file(temp_profile: Path) -> None:
    """Test graceful handling when Bookmarks file doesn't exist."""
    analyzer = BookmarksAnalyzer(temp_profile)
    bookmarks = analyzer.analyze()

    assert bookmarks == []


def test_bookmarks_get_folders(temp_profile: Path, sample_bookmarks: Path) -> None:
    """Test extracting unique folder paths."""
    analyzer = BookmarksAnalyzer(temp_profile)
    analyzer.analyze()
    folders = analyzer.get_folders()

    assert len(folders) > 0
    assert any("Work" in f for f in folders)




