"""Tests for export functionality."""

import json
from pathlib import Path

from chromemate.analyzers.bookmarks import Bookmark
from chromemate.analyzers.extensions import Extension
from chromemate.exporter import (
    export_bookmarks_html,
    export_extensions_json,
    export_extensions_markdown,
)


def test_export_bookmarks_creates_html(tmp_path: Path) -> None:
    """Test exporting bookmarks to HTML format."""
    bookmarks = [
        Bookmark(name="GitHub", url="https://github.com", path="bookmark_bar"),
        Bookmark(name="Google", url="https://google.com", path="bookmark_bar"),
    ]

    output_file = tmp_path / "bookmarks.html"
    export_bookmarks_html(bookmarks, output_file)

    content = output_file.read_text()
    assert "<!DOCTYPE NETSCAPE-Bookmark-file-1>" in content
    assert "GitHub" in content
    assert "https://github.com" in content


def test_export_bookmarks_escapes_html(tmp_path: Path) -> None:
    """Test that special characters are escaped in HTML."""
    bookmarks = [
        Bookmark(
            name="Test <script>alert(1)</script>",
            url="https://example.com?a=1&b=2",
            path="bookmark_bar",
        )
    ]

    output_file = tmp_path / "bookmarks.html"
    export_bookmarks_html(bookmarks, output_file)

    content = output_file.read_text()
    assert "&lt;script&gt;" in content
    assert "&amp;b=2" in content


def test_export_extensions_json(tmp_path: Path) -> None:
    """Test exporting extensions to JSON format."""
    extensions = [
        Extension(
            id="abc123",
            name="Test Extension",
            version="1.0.0",
            enabled=True,
            description="A test extension",
        )
    ]

    output_file = tmp_path / "extensions.json"
    export_extensions_json(extensions, output_file)

    data = json.loads(output_file.read_text())
    assert "extensions" in data
    assert len(data["extensions"]) == 1
    assert data["extensions"][0]["name"] == "Test Extension"


def test_export_extensions_markdown(tmp_path: Path) -> None:
    """Test exporting extensions to Markdown format."""
    extensions = [
        Extension(
            id="abc123",
            name="Test Extension",
            version="1.0.0",
            enabled=True,
            description="A test extension",
        ),
        Extension(
            id="disabled",
            name="Disabled Ext",
            version="2.0.0",
            enabled=False,
        ),
    ]

    output_file = tmp_path / "extensions.md"
    export_extensions_markdown(extensions, output_file)

    content = output_file.read_text()
    assert "# Chrome Extensions" in content
    assert "**Test Extension**" in content
    assert "Disabled Ext" in content
    assert "## Disabled Extensions" in content



