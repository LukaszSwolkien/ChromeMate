"""Tests for history merger."""

import sqlite3
from pathlib import Path

import pytest

from chromemate.history_merger import HistoryMerger, MergeStats


def create_history_db(
    path: Path,
    urls: list[tuple[int, str, str, int, int, int, int]],
    visits: list[tuple[int, int, int]] | None = None,
) -> None:
    """Create a History database with given data.

    urls format: (id, url, title, visit_count, typed_count, last_visit_time, hidden)
    visits format: (url_id, visit_time, transition)
    """
    conn = sqlite3.connect(path)
    conn.execute(
        """
        CREATE TABLE urls (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url LONGVARCHAR,
            title LONGVARCHAR,
            visit_count INTEGER DEFAULT 0 NOT NULL,
            typed_count INTEGER DEFAULT 0 NOT NULL,
            last_visit_time INTEGER NOT NULL,
            hidden INTEGER DEFAULT 0 NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE visits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url INTEGER NOT NULL,
            visit_time INTEGER NOT NULL,
            from_visit INTEGER DEFAULT 0,
            transition INTEGER DEFAULT 0 NOT NULL,
            segment_id INTEGER DEFAULT 0,
            visit_duration INTEGER DEFAULT 0 NOT NULL,
            incremented_omnibox_typed_score BOOLEAN DEFAULT FALSE NOT NULL,
            consider_for_ntp_most_visited BOOLEAN DEFAULT FALSE NOT NULL
        )
        """
    )

    for url_data in urls:
        conn.execute(
            """
            INSERT INTO urls (id, url, title, visit_count, typed_count, last_visit_time, hidden)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            url_data,
        )

    if visits:
        for visit_data in visits:
            url_id, visit_time, transition = visit_data
            conn.execute(
                """
                INSERT INTO visits (url, visit_time, transition)
                VALUES (?, ?, ?)
                """,
                (url_id, visit_time, transition),
            )

    conn.commit()
    conn.close()


@pytest.fixture
def source_profile(tmp_path: Path) -> Path:
    """Create source profile with history."""
    profile = tmp_path / "Source"
    profile.mkdir()

    # Chrome timestamps: microseconds since Jan 1, 1601
    create_history_db(
        profile / "History",
        urls=[
            (1, "https://github.com", "GitHub", 100, 10, 13345678901234567, 0),
            (2, "https://stackoverflow.com", "Stack Overflow", 50, 5, 13345678901234568, 0),
            (3, "https://unique-source.com", "Unique Source", 25, 2, 13345678901234569, 0),
        ],
        visits=[
            (1, 13345678901234567, 0),
            (1, 13345678901234568, 0),
            (2, 13345678901234569, 0),
            (3, 13345678901234570, 0),
        ],
    )
    return profile


@pytest.fixture
def target_profile(tmp_path: Path) -> Path:
    """Create target profile with history."""
    profile = tmp_path / "Target"
    profile.mkdir()

    create_history_db(
        profile / "History",
        urls=[
            (1, "https://github.com", "GitHub - Home", 200, 20, 13345678901234600, 0),
            (2, "https://google.com", "Google", 300, 30, 13345678901234601, 0),
        ],
        visits=[
            (1, 13345678901234600, 0),
            (2, 13345678901234601, 0),
        ],
    )
    return profile


def test_merge_adds_new_urls(source_profile: Path, target_profile: Path) -> None:
    """Test that new URLs from source are added to target."""
    merger = HistoryMerger(source_profile, target_profile)
    stats = merger.merge()

    # unique-source.com and stackoverflow.com should be added
    assert stats.urls_added == 2

    # Verify in database
    conn = sqlite3.connect(target_profile / "History")
    urls = {row[0] for row in conn.execute("SELECT url FROM urls")}
    conn.close()

    assert "https://unique-source.com" in urls
    assert "https://stackoverflow.com" in urls


def test_merge_updates_existing_urls(source_profile: Path, target_profile: Path) -> None:
    """Test that existing URLs have visit counts combined."""
    merger = HistoryMerger(source_profile, target_profile)
    stats = merger.merge()

    # github.com exists in both
    assert stats.urls_updated == 1

    # Verify counts are combined
    conn = sqlite3.connect(target_profile / "History")
    row = conn.execute(
        "SELECT visit_count, typed_count FROM urls WHERE url = ?",
        ("https://github.com",),
    ).fetchone()
    conn.close()

    # 200 (target) + 100 (source) = 300
    assert row[0] == 300
    # 20 (target) + 10 (source) = 30
    assert row[1] == 30


def test_merge_adds_visits(source_profile: Path, target_profile: Path) -> None:
    """Test that individual visits are copied."""
    merger = HistoryMerger(source_profile, target_profile)
    stats = merger.merge()

    # 4 visits from source should be added
    assert stats.visits_added == 4

    conn = sqlite3.connect(target_profile / "History")
    visit_count = conn.execute("SELECT COUNT(*) FROM visits").fetchone()[0]
    conn.close()

    # 2 original + 4 from source
    assert visit_count == 6


def test_merge_dry_run_no_changes(source_profile: Path, target_profile: Path) -> None:
    """Test that dry run doesn't modify target."""
    merger = HistoryMerger(source_profile, target_profile, dry_run=True)

    # Get original state
    conn = sqlite3.connect(target_profile / "History")
    original_urls = conn.execute("SELECT COUNT(*) FROM urls").fetchone()[0]
    original_visits = conn.execute("SELECT COUNT(*) FROM visits").fetchone()[0]
    conn.close()

    stats = merger.merge()

    # Stats should still show what would happen
    assert stats.urls_added == 2
    assert stats.urls_updated == 1

    # But database should be unchanged
    conn = sqlite3.connect(target_profile / "History")
    new_urls = conn.execute("SELECT COUNT(*) FROM urls").fetchone()[0]
    new_visits = conn.execute("SELECT COUNT(*) FROM visits").fetchone()[0]
    conn.close()

    assert new_urls == original_urls
    assert new_visits == original_visits


def test_merge_preview(source_profile: Path, target_profile: Path) -> None:
    """Test preview provides accurate statistics."""
    merger = HistoryMerger(source_profile, target_profile)
    preview = merger.preview()

    assert preview["source_urls"] == 3
    assert preview["source_visits"] == 4
    assert preview["target_urls"] == 2
    assert preview["target_visits"] == 2
    assert preview["new_urls_to_add"] == 2  # stackoverflow, unique-source
    assert preview["existing_urls_to_update"] == 1  # github


def test_merge_handles_duplicate_visits(tmp_path: Path) -> None:
    """Test that duplicate visits (same URL+time) are skipped."""
    source = tmp_path / "Source"
    target = tmp_path / "Target"
    source.mkdir()
    target.mkdir()

    # Same visit in both profiles
    create_history_db(
        source / "History",
        urls=[(1, "https://example.com", "Example", 10, 1, 13345678901234567, 0)],
        visits=[(1, 13345678901234567, 0)],
    )
    create_history_db(
        target / "History",
        urls=[(1, "https://example.com", "Example", 5, 0, 13345678901234567, 0)],
        visits=[(1, 13345678901234567, 0)],  # Same visit time
    )

    merger = HistoryMerger(source, target)
    stats = merger.merge()

    # URL should be updated but visit should be skipped (duplicate)
    assert stats.urls_updated == 1
    assert stats.visits_added == 0


def test_merge_preserves_last_visit_time(source_profile: Path, target_profile: Path) -> None:
    """Test that the most recent last_visit_time is preserved."""
    merger = HistoryMerger(source_profile, target_profile)
    merger.merge()

    conn = sqlite3.connect(target_profile / "History")
    row = conn.execute(
        "SELECT last_visit_time FROM urls WHERE url = ?",
        ("https://github.com",),
    ).fetchone()
    conn.close()

    # Target had 13345678901234600 (higher), source had 13345678901234567
    assert row[0] == 13345678901234600


def test_merge_missing_source_raises(tmp_path: Path, target_profile: Path) -> None:
    """Test that missing source history raises error."""
    empty_source = tmp_path / "EmptySource"
    empty_source.mkdir()

    merger = HistoryMerger(empty_source, target_profile)

    with pytest.raises(FileNotFoundError, match="Source history not found"):
        merger.merge()


def test_merge_missing_target_raises(source_profile: Path, tmp_path: Path) -> None:
    """Test that missing target history raises error."""
    empty_target = tmp_path / "EmptyTarget"
    empty_target.mkdir()

    merger = HistoryMerger(source_profile, empty_target)

    with pytest.raises(FileNotFoundError, match="Target history not found"):
        merger.merge()


def test_merge_empty_source(tmp_path: Path, target_profile: Path) -> None:
    """Test merging from profile with no visited URLs."""
    empty_source = tmp_path / "EmptySource"
    empty_source.mkdir()

    # Create empty history DB
    create_history_db(empty_source / "History", urls=[], visits=[])

    merger = HistoryMerger(empty_source, target_profile)
    stats = merger.merge()

    assert stats.urls_added == 0
    assert stats.urls_updated == 0
    assert stats.visits_added == 0

