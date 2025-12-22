"""Tests for history analyzer."""

from pathlib import Path

from chromemate.analyzers.history import HistoryAnalyzer


def test_history_reads_entries(temp_profile: Path, sample_history: Path) -> None:
    """Test reading history entries from database."""
    analyzer = HistoryAnalyzer(temp_profile)
    entries = analyzer.analyze()

    assert len(entries) == 4


def test_history_ranks_by_visit_count(temp_profile: Path, sample_history: Path) -> None:
    """Test that top sites are ranked by visit count."""
    analyzer = HistoryAnalyzer(temp_profile)
    analyzer.analyze()
    top_sites = analyzer.get_top_sites(n=2)

    # Google should be first (500 visits), GitHub second (150 visits)
    assert top_sites[0].title == "Google"
    assert top_sites[1].title == "GitHub"


def test_history_handles_missing_file(temp_profile: Path) -> None:
    """Test graceful handling when History file doesn't exist."""
    analyzer = HistoryAnalyzer(temp_profile)
    entries = analyzer.analyze()

    assert entries == []


def test_history_get_domains(temp_profile: Path, sample_history: Path) -> None:
    """Test domain aggregation from history."""
    analyzer = HistoryAnalyzer(temp_profile)
    analyzer.analyze()
    domains = analyzer.get_domains()

    assert "google.com" in domains
    assert "github.com" in domains
    assert domains["google.com"] == 500


def test_history_respects_limit(temp_profile: Path, sample_history: Path) -> None:
    """Test that limit parameter restricts results."""
    analyzer = HistoryAnalyzer(temp_profile)
    entries = analyzer.analyze(limit=2)

    assert len(entries) == 2


def test_history_filter_include(temp_profile: Path, sample_history: Path) -> None:
    """Test filtering history to include only matching URLs."""
    analyzer = HistoryAnalyzer(temp_profile)
    analyzer.analyze()
    filtered = analyzer.filter(include=["github"])

    assert len(filtered) == 1
    assert "github.com" in filtered[0].url


def test_history_filter_exclude(temp_profile: Path, sample_history: Path) -> None:
    """Test filtering history to exclude matching URLs."""
    analyzer = HistoryAnalyzer(temp_profile)
    analyzer.analyze()
    filtered = analyzer.filter(exclude=["google"])

    assert len(filtered) == 3
    assert all("google" not in e.url for e in filtered)


def test_history_filter_include_and_exclude(temp_profile: Path, sample_history: Path) -> None:
    """Test combining include and exclude filters."""
    analyzer = HistoryAnalyzer(temp_profile)
    analyzer.analyze()
    # Include anything with 'o' but exclude google
    filtered = analyzer.filter(include=["stackoverflow", "github"], exclude=["github"])

    assert len(filtered) == 1
    assert "stackoverflow" in filtered[0].url


def test_history_filter_bookmarked_only(temp_profile: Path, sample_history: Path) -> None:
    """Test filtering to only bookmarked URLs."""
    analyzer = HistoryAnalyzer(temp_profile)
    analyzer.analyze()

    # Only github.com is "bookmarked"
    bookmarked_urls = {"https://github.com", "https://example.com"}
    filtered = analyzer.filter(bookmarked_urls=bookmarked_urls)

    assert len(filtered) == 1
    assert filtered[0].url == "https://github.com"


def test_history_aggregate_by_url_combines_urls(temp_profile: Path) -> None:
    """Test aggregating URLs with different query parameters."""
    import sqlite3

    history_file = temp_profile / "History"
    conn = sqlite3.connect(history_file)
    conn.execute(
        """
        CREATE TABLE urls (
            id INTEGER PRIMARY KEY,
            url TEXT,
            title TEXT,
            visit_count INTEGER,
            last_visit_time INTEGER
        )
    """
    )
    sample_urls = [
        (1, "https://docs.google.com/doc/123?tab=1", "My Doc", 50, 13345678901234567),
        (2, "https://docs.google.com/doc/123?tab=2", "My Doc", 30, 13345678901234568),
        (3, "https://docs.google.com/doc/123?tab=3", "My Doc", 20, 13345678901234566),
        (4, "https://other.com/page", "Other", 10, 13345678901234567),
    ]
    conn.executemany(
        "INSERT INTO urls (id, url, title, visit_count, last_visit_time) VALUES (?, ?, ?, ?, ?)",
        sample_urls,
    )
    conn.commit()
    conn.close()

    analyzer = HistoryAnalyzer(temp_profile)
    analyzer.analyze()
    aggregated = analyzer.filter(aggregate="url")

    # Should have 2 entries: the combined doc and other
    assert len(aggregated) == 2

    # Combined doc should have 100 visits (50+30+20)
    doc_entry = next(e for e in aggregated if "docs.google.com" in e.url)
    assert doc_entry.visit_count == 100
    assert "?" not in doc_entry.url  # Query params removed


def test_history_aggregate_by_domain(temp_profile: Path) -> None:
    """Test aggregating by domain with domain as title."""
    import sqlite3

    history_file = temp_profile / "History"
    conn = sqlite3.connect(history_file)
    conn.execute(
        """
        CREATE TABLE urls (
            id INTEGER PRIMARY KEY,
            url TEXT,
            title TEXT,
            visit_count INTEGER,
            last_visit_time INTEGER
        )
    """
    )
    sample_urls = [
        (1, "https://github.com/user/repo1", "Repo 1", 50, 13345678901234567),
        (2, "https://github.com/user/repo2", "Repo 2", 30, 13345678901234568),
        (3, "https://google.com/search?q=test", "Search", 20, 13345678901234566),
    ]
    conn.executemany(
        "INSERT INTO urls (id, url, title, visit_count, last_visit_time) VALUES (?, ?, ?, ?, ?)",
        sample_urls,
    )
    conn.commit()
    conn.close()

    analyzer = HistoryAnalyzer(temp_profile)
    analyzer.analyze()
    aggregated = analyzer.filter(aggregate="domain")

    # Should have 2 entries: github.com and google.com
    assert len(aggregated) == 2

    # GitHub should have 80 visits and domain as title
    github_entry = next(e for e in aggregated if "github" in e.url)
    assert github_entry.visit_count == 80
    assert github_entry.title == "github.com"

