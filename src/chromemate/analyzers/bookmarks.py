"""Bookmark analysis for Chrome profiles."""

import json
from dataclasses import dataclass, field
from pathlib import Path

from chromemate.analyzers.utils import convert_webkit_timestamp


@dataclass
class Bookmark:
    """Represents a single bookmark."""

    name: str
    url: str
    path: str  # Folder path like "Bookmarks Bar/Work/Projects"
    date_added: int | None = None


@dataclass
class BookmarksAnalyzer:
    """Analyzes bookmarks from a Chrome profile."""

    profile_path: Path
    bookmarks: list[Bookmark] = field(default_factory=list)

    def analyze(self) -> list[Bookmark]:
        """Parse and analyze bookmarks from the profile."""
        bookmarks_file = self.profile_path / "Bookmarks"
        if not bookmarks_file.exists():
            return []

        try:
            with open(bookmarks_file, encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            return []

        self.bookmarks = []
        roots = data.get("roots", {})

        for root_name, root_node in roots.items():
            if isinstance(root_node, dict):
                self._parse_node(root_node, root_name)

        return self.bookmarks

    def _parse_node(self, node: dict, current_path: str) -> None:
        """Recursively parse bookmark nodes."""
        node_type = node.get("type", "")

        if node_type == "url":
            self.bookmarks.append(
                Bookmark(
                    name=node.get("name", ""),
                    url=node.get("url", ""),
                    path=current_path,
                    date_added=convert_webkit_timestamp(node.get("date_added")),
                )
            )
        elif node_type == "folder":
            folder_name = node.get("name", "")
            new_path = f"{current_path}/{folder_name}" if folder_name else current_path
            for child in node.get("children", []):
                self._parse_node(child, new_path)
        elif "children" in node:
            # Root nodes don't have type but have children
            for child in node.get("children", []):
                self._parse_node(child, current_path)

    def get_by_folder(self, folder_path: str) -> list[Bookmark]:
        """Get bookmarks in a specific folder."""
        return [b for b in self.bookmarks if b.path.startswith(folder_path)]

    def get_folders(self) -> list[str]:
        """Get list of unique folder paths."""
        return sorted(set(b.path for b in self.bookmarks))

    def filter_by_urls(self, urls: set[str]) -> list[Bookmark]:
        """Filter bookmarks to only those whose URLs are in the given set."""
        return [b for b in self.bookmarks if b.url in urls]

