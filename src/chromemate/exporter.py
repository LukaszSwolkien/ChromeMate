"""Export functionality for Chrome profile data."""

import csv
import html
import json
from datetime import datetime
from pathlib import Path

from chromemate.analyzers.bookmarks import Bookmark
from chromemate.analyzers.extensions import Extension
from chromemate.analyzers.history import HistoryEntry


def export_bookmarks_html(bookmarks: list[Bookmark], output_path: Path) -> None:
    """
    Export bookmarks to HTML format (Netscape Bookmark File Format).

    This format can be imported by Chrome and other browsers.
    Preserves folder structure from bookmark paths.
    """
    lines = [
        "<!DOCTYPE NETSCAPE-Bookmark-file-1>",
        "<!-- This is an automatically generated file. -->",
        "<!-- It will be read and overwritten. DO NOT EDIT! -->",
        '<META HTTP-EQUIV="Content-Type" CONTENT="text/html; charset=UTF-8">',
        "<TITLE>Bookmarks</TITLE>",
        "<H1>Bookmarks</H1>",
        "<DL><p>",
    ]

    # Group bookmarks by folder
    folders: dict[str, list[Bookmark]] = {}
    for bm in bookmarks:
        if bm.path not in folders:
            folders[bm.path] = []
        folders[bm.path].append(bm)

    # Build folder tree to ensure proper nesting
    open_folders: list[str] = []

    for folder_path in sorted(folders.keys()):
        parts = [p for p in folder_path.split("/") if p]

        # Find common prefix with current open folders
        common_depth = 0
        for i, (open_part, new_part) in enumerate(zip(open_folders, parts)):
            if open_part == new_part:
                common_depth = i + 1
            else:
                break

        # Close folders that are no longer in path
        while len(open_folders) > common_depth:
            open_folders.pop()
            indent = "    " * (len(open_folders) + 1)
            lines.append(f"{indent}</DL><p>")

        # Open new folders
        for i in range(common_depth, len(parts)):
            indent = "    " * (len(open_folders) + 1)
            folder_name = html.escape(parts[i])
            lines.append(f"{indent}<DT><H3>{folder_name}</H3>")
            lines.append(f"{indent}<DL><p>")
            open_folders.append(parts[i])

        # Add bookmarks in this folder
        for bm in folders[folder_path]:
            indent = "    " * (len(open_folders) + 1)
            name = html.escape(bm.name)
            url = html.escape(bm.url)
            lines.append(f'{indent}<DT><A HREF="{url}">{name}</A>')

    # Close remaining folders
    while open_folders:
        open_folders.pop()
        indent = "    " * (len(open_folders) + 1)
        lines.append(f"{indent}</DL><p>")

    lines.append("</DL><p>")

    output_path.write_text("\n".join(lines), encoding="utf-8")


def export_extensions_json(extensions: list[Extension], output_path: Path) -> None:
    """Export extensions list to JSON format."""
    data = {
        "exported_at": datetime.now().isoformat(),
        "extensions": [
            {
                "id": ext.id,
                "name": ext.name,
                "version": ext.version,
                "enabled": ext.enabled,
                "description": ext.description,
                "webstore_url": ext.webstore_url,
            }
            for ext in extensions
        ],
    }
    output_path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def export_extensions_markdown(extensions: list[Extension], output_path: Path) -> None:
    """Export extensions list as Markdown for easy reference."""
    lines = [
        "# Chrome Extensions",
        "",
        f"Exported on {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "",
        "## Enabled Extensions",
        "",
    ]

    enabled = [e for e in extensions if e.enabled]
    disabled = [e for e in extensions if not e.enabled]

    for ext in sorted(enabled, key=lambda e: e.name.lower()):
        lines.append(f"- **{ext.name}** (v{ext.version})")
        if ext.description:
            lines.append(f"  - {ext.description[:100]}")
        lines.append(f"  - [Install]({ext.webstore_url})")
        lines.append("")

    if disabled:
        lines.append("## Disabled Extensions")
        lines.append("")
        for ext in sorted(disabled, key=lambda e: e.name.lower()):
            lines.append(f"- {ext.name} (v{ext.version})")

    output_path.write_text("\n".join(lines), encoding="utf-8")


def export_history_csv(history: list[HistoryEntry], output_path: Path) -> None:
    """Export browsing history to CSV format, ranked by visit count."""
    sorted_history = sorted(history, key=lambda e: e.visit_count, reverse=True)

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Rank", "Title", "URL", "Visit Count", "Last Visit"])

        for rank, entry in enumerate(sorted_history, 1):
            last_visit = datetime.fromtimestamp(entry.last_visit_time).strftime("%Y-%m-%d %H:%M")
            writer.writerow([rank, entry.title, entry.url, entry.visit_count, last_visit])


def export_history_json(history: list[HistoryEntry], output_path: Path) -> None:
    """Export browsing history to JSON format, ranked by visit count."""
    sorted_history = sorted(history, key=lambda e: e.visit_count, reverse=True)

    data = {
        "exported_at": datetime.now().isoformat(),
        "total_entries": len(sorted_history),
        "history": [
            {
                "rank": rank,
                "title": entry.title,
                "url": entry.url,
                "visit_count": entry.visit_count,
                "last_visit": datetime.fromtimestamp(entry.last_visit_time).isoformat(),
            }
            for rank, entry in enumerate(sorted_history, 1)
        ],
    }
    output_path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def export_history_markdown(history: list[HistoryEntry], output_path: Path) -> None:
    """Export browsing history as Markdown, ranked by visit count."""
    sorted_history = sorted(history, key=lambda e: e.visit_count, reverse=True)

    lines = [
        "# Top Sites by Usage",
        "",
        f"Exported on {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "",
        "| Rank | Title | Visits | URL |",
        "|------|-------|--------|-----|",
    ]

    for rank, entry in enumerate(sorted_history, 1):
        title = entry.title[:40] + "..." if len(entry.title) > 40 else entry.title
        lines.append(f"| {rank} | {title} | {entry.visit_count} | {entry.url} |")

    output_path.write_text("\n".join(lines), encoding="utf-8")

