"""Shared test fixtures."""

import json
import sqlite3
from pathlib import Path

import pytest


@pytest.fixture
def temp_profile(tmp_path: Path) -> Path:
    """Create a temporary Chrome profile with sample data."""
    profile_path = tmp_path / "TestProfile"
    profile_path.mkdir()
    return profile_path


@pytest.fixture
def sample_bookmarks(temp_profile: Path) -> Path:
    """Create sample Bookmarks file."""
    bookmarks_data = {
        "checksum": "test",
        "roots": {
            "bookmark_bar": {
                "children": [
                    {
                        "name": "GitHub",
                        "type": "url",
                        "url": "https://github.com",
                        "date_added": "13345678901234567",
                    },
                    {
                        "name": "Work",
                        "type": "folder",
                        "children": [
                            {
                                "name": "Jira",
                                "type": "url",
                                "url": "https://jira.example.com",
                            },
                            {
                                "name": "Confluence",
                                "type": "url",
                                "url": "https://confluence.example.com",
                            },
                        ],
                    },
                ],
                "name": "Bookmarks Bar",
                "type": "folder",
            },
            "other": {
                "children": [
                    {
                        "name": "Stack Overflow",
                        "type": "url",
                        "url": "https://stackoverflow.com",
                    }
                ],
                "name": "Other Bookmarks",
                "type": "folder",
            },
        },
        "version": 1,
    }

    bookmarks_file = temp_profile / "Bookmarks"
    bookmarks_file.write_text(json.dumps(bookmarks_data))
    return bookmarks_file


@pytest.fixture
def sample_history(temp_profile: Path) -> Path:
    """Create sample History SQLite database."""
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

    # Chrome timestamps: microseconds since Jan 1, 1601
    # 13345678901234567 is approximately 2023
    sample_urls = [
        (1, "https://github.com", "GitHub", 150, 13345678901234567),
        (2, "https://google.com", "Google", 500, 13345678901234567),
        (3, "https://stackoverflow.com", "Stack Overflow", 75, 13345678901234567),
        (4, "https://docs.python.org", "Python Docs", 30, 13345678901234567),
    ]

    conn.executemany(
        "INSERT INTO urls (id, url, title, visit_count, last_visit_time) VALUES (?, ?, ?, ?, ?)",
        sample_urls,
    )
    conn.commit()
    conn.close()

    return history_file


@pytest.fixture
def sample_preferences(temp_profile: Path) -> Path:
    """Create sample Preferences file with extension data."""
    prefs_data = {
        "profile": {"name": "Test User"},
        "extensions": {
            "settings": {
                "abcdefghijklmnop": {
                    "manifest": {
                        "name": "uBlock Origin",
                        "version": "1.50.0",
                        "description": "An efficient blocker.",
                    },
                    "state": 1,
                    "from_webstore": True,
                },
                "qrstuvwxyz123456": {
                    "manifest": {
                        "name": "Dark Reader",
                        "version": "4.9.60",
                        "description": "Dark mode for every website.",
                    },
                    "state": 1,
                    "from_webstore": True,
                },
                "disabled12345678": {
                    "manifest": {
                        "name": "Old Extension",
                        "version": "1.0.0",
                        "description": "Not used anymore.",
                    },
                    "state": 0,
                    "from_webstore": True,
                },
            }
        },
    }

    prefs_file = temp_profile / "Preferences"
    prefs_file.write_text(json.dumps(prefs_data))
    return prefs_file




