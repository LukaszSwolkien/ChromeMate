"""Report generation for Chrome profile analysis."""

from dataclasses import dataclass

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from chromemate.analyzers.bookmarks import Bookmark
from chromemate.analyzers.extensions import Extension
from chromemate.analyzers.history import HistoryEntry
from chromemate.profile import ChromeProfile


@dataclass
class AnalysisReport:
    """Contains all analysis results for a profile."""

    profile: ChromeProfile
    bookmarks: list[Bookmark]
    history: list[HistoryEntry]
    extensions: list[Extension]


def print_report(report: AnalysisReport, console: Console | None = None) -> None:
    """Print a formatted analysis report to the console."""
    if console is None:
        console = Console()

    # Header
    console.print()
    console.print(
        Panel(
            f"[bold]Profile:[/bold] {report.profile.display_name or report.profile.name}\n"
            f"[bold]Path:[/bold] {report.profile.path}",
            title="[bold blue]ChromeMate Analysis Report[/bold blue]",
            border_style="blue",
        )
    )
    console.print()

    # Summary
    _print_summary(report, console)

    # Top Sites
    _print_top_sites(report.history, console)

    # Bookmarks by folder
    _print_bookmarks_summary(report.bookmarks, console)

    # Extensions
    _print_extensions(report.extensions, console)

    # Migration recommendations
    _print_recommendations(report, console)


def _print_summary(report: AnalysisReport, console: Console) -> None:
    """Print summary statistics."""
    table = Table(title="Summary", show_header=False, border_style="dim")
    table.add_column("Metric", style="bold")
    table.add_column("Value", justify="right")

    enabled_ext = len([e for e in report.extensions if e.enabled])
    disabled_ext = len([e for e in report.extensions if not e.enabled])
    table.add_row("Total Bookmarks", str(len(report.bookmarks)))
    table.add_row("History Entries", str(len(report.history)))
    table.add_row("Extensions (enabled)", str(enabled_ext))
    table.add_row("Extensions (disabled)", str(disabled_ext))

    console.print(table)
    console.print()


def _print_top_sites(history: list[HistoryEntry], console: Console) -> None:
    """Print top visited sites."""
    if not history:
        return

    from datetime import datetime

    title = f"Top {len(history)} Most Visited Sites"
    table = Table(title=title, border_style="green")
    table.add_column("#", style="dim", width=4)
    table.add_column("Title", max_width=35, overflow="ellipsis")
    table.add_column("Visits", justify="right", style="green")
    table.add_column("Last Visit", style="cyan")
    table.add_column("URL", max_width=40, overflow="ellipsis", style="dim")

    # History is already sorted and filtered
    for i, entry in enumerate(history, 1):
        last_visit = datetime.fromtimestamp(entry.last_visit_time).strftime("%Y-%m-%d")
        table.add_row(
            str(i),
            entry.title or "(no title)",
            str(entry.visit_count),
            last_visit,
            entry.url,
        )

    console.print(table)
    console.print()


def _print_bookmarks_summary(bookmarks: list[Bookmark], console: Console) -> None:
    """Print bookmarks organized by folder."""
    if not bookmarks:
        return

    # Count by top-level folder
    folder_counts: dict[str, int] = {}
    for bm in bookmarks:
        parts = bm.path.split("/")
        top_folder = parts[1] if len(parts) > 1 else parts[0]
        folder_counts[top_folder] = folder_counts.get(top_folder, 0) + 1

    table = Table(title="Bookmarks by Folder", border_style="yellow")
    table.add_column("Folder", style="bold")
    table.add_column("Count", justify="right", style="yellow")

    for folder, count in sorted(folder_counts.items(), key=lambda x: x[1], reverse=True):
        table.add_row(folder, str(count))

    console.print(table)
    console.print()


def _print_extensions(extensions: list[Extension], console: Console) -> None:
    """Print extension information."""
    enabled = [e for e in extensions if e.enabled]
    if not enabled:
        return

    table = Table(title="Enabled Extensions", border_style="cyan")
    table.add_column("Name", max_width=30, overflow="ellipsis")
    table.add_column("Version", style="dim")
    table.add_column("Description", max_width=50, overflow="ellipsis", style="dim")

    for ext in sorted(enabled, key=lambda e: e.name.lower()):
        table.add_row(ext.name, ext.version, ext.description[:50] if ext.description else "")

    console.print(table)
    console.print()


def _print_recommendations(report: AnalysisReport, console: Console) -> None:
    """Print migration recommendations."""
    recommendations = []

    # Recommend enabled extensions
    enabled_ext = len([e for e in report.extensions if e.enabled])
    if enabled_ext > 0:
        recommendations.append(f"✓ {enabled_ext} enabled extensions to migrate")

    # Recommend bookmarks
    if len(report.bookmarks) > 0:
        recommendations.append(f"✓ {len(report.bookmarks)} bookmarks to export")

    # Top sites insight
    if len(report.history) > 0:
        recommendations.append("✓ Top sites identified for quick access setup")

    if recommendations:
        console.print(
            Panel(
                "\n".join(recommendations),
                title="[bold green]Migration Recommendations[/bold green]",
                border_style="green",
            )
        )
        console.print()

