"""ChromeMate CLI application."""

from pathlib import Path
from typing import Annotated, Optional
from urllib.parse import urlparse

import typer
from rich.console import Console

from chromemate.analyzers import BookmarksAnalyzer, ExtensionsAnalyzer, HistoryAnalyzer
from chromemate.exporter import (
    export_bookmarks_html,
    export_extensions_json,
    export_extensions_markdown,
    export_history_csv,
    export_history_json,
    export_history_markdown,
)
from chromemate.history_merger import HistoryMerger
from chromemate.profile import ChromeProfile, discover_profiles, get_profile_by_name
from chromemate.report import AnalysisReport, print_report

# Constants
HISTORY_QUERY_LIMIT = 10000  # Max entries to fetch for filtering/aggregation


def _normalize_url(url: str) -> str:
    """Normalize URL for matching (lowercase, remove query/fragment)."""
    try:
        parsed = urlparse(url)
        return f"{parsed.netloc}{parsed.path}".lower().rstrip("/")
    except Exception:
        return url.lower()


def _find_unused_bookmarks(
    bookmarks: list,
    history: list,
) -> list:
    """Find bookmarks that have never been visited."""
    visited_keys = {_normalize_url(e.url) for e in history}
    return [b for b in bookmarks if _normalize_url(b.url) not in visited_keys]


app = typer.Typer(
    name="chromemate",
    help="Smart assistant for Chrome profile migration",
    no_args_is_help=True,
    add_completion=False,  # Disabled for PyInstaller compatibility
)
console = Console()


@app.command()
def profiles() -> None:
    """List all available Chrome profiles."""
    found_profiles = discover_profiles()

    if not found_profiles:
        console.print("[yellow]No Chrome profiles found on this system.[/yellow]")
        raise typer.Exit(1)

    console.print("\n[bold]Available Chrome Profiles:[/bold]\n")
    for profile in found_profiles:
        display = profile.display_name or profile.name
        console.print(f"  • [bold]{display}[/bold] ({profile.name})")
        console.print(f"    [dim]{profile.path}[/dim]")
    console.print()


@app.command()
def analyze(
    profile: Annotated[
        Optional[str],
        typer.Option("--profile", "-p", help="Profile name (default: Default)"),
    ] = None,
    top: Annotated[
        Optional[int],
        typer.Option("--top", "-t", help="Limit results (default: 10)"),
    ] = None,
    include: Annotated[
        Optional[list[str]],
        typer.Option("--include", "-i", help="Only include URLs containing pattern (can repeat)"),
    ] = None,
    exclude: Annotated[
        Optional[list[str]],
        typer.Option("--exclude", "-x", help="Exclude URLs containing pattern (can repeat)"),
    ] = None,
    bookmarked_only: Annotated[
        bool,
        typer.Option("--bookmarked-only", "-B", help="Only show sites that are bookmarked"),
    ] = False,
    unused_bookmarks: Annotated[
        bool,
        typer.Option("--unused", "-U", help="Show bookmarks that have never been visited"),
    ] = False,
    aggregate: Annotated[
        Optional[str],
        typer.Option("--aggregate", "-a", help="Aggregate all by: 'url' (base URL) or 'domain'"),
    ] = None,
    aggregate_url: Annotated[
        Optional[list[str]],
        typer.Option("--aggregate-url", help="Aggregate by URL for domains matching pattern"),
    ] = None,
    aggregate_domain: Annotated[
        Optional[list[str]],
        typer.Option("--aggregate-domain", help="Aggregate by domain for domains matching pattern"),
    ] = None,
    days: Annotated[
        Optional[int],
        typer.Option("--days", "-d", help="Only include history from the last N days"),
    ] = None,
) -> None:
    """Analyze a Chrome profile and show usage report."""
    chrome_profile = _get_profile(profile)

    # Validate aggregate option
    if aggregate and aggregate not in ("url", "domain"):
        console.print("[red]Error: --aggregate must be 'url' or 'domain'[/red]")
        raise typer.Exit(1)

    # Determine effective top limit
    # If --days is set but --top is not, don't limit results
    effective_top = top if top is not None else (None if days or unused_bookmarks else 10)

    with console.status("[bold blue]Analyzing profile..."):
        # Run all analyzers
        bookmarks_analyzer = BookmarksAnalyzer(chrome_profile.path)
        bookmarks = bookmarks_analyzer.analyze()

        # Get bookmarked URLs for filtering
        bookmarked_urls = {b.url for b in bookmarks} if bookmarked_only else None

        history_analyzer = HistoryAnalyzer(chrome_profile.path)
        history_analyzer.analyze(limit=HISTORY_QUERY_LIMIT)

        # Handle unused bookmarks mode
        if unused_bookmarks:
            # Get all visited URLs
            all_history = history_analyzer.filter(days=days)

            # Find bookmarks that were never visited
            unused = _find_unused_bookmarks(bookmarks, all_history)

            # Apply include/exclude filters
            if include:
                unused = [b for b in unused if any(p.lower() in b.url.lower() for p in include)]
            if exclude:
                unused = [b for b in unused if not any(p.lower() in b.url.lower() for p in exclude)]

            if effective_top:
                unused = unused[:effective_top]

            # Print unused bookmarks report
            console.print()
            console.print(f"[bold]Found {len(unused)} unused bookmarks[/bold]")
            if days:
                console.print(f"[dim](not visited in the last {days} days)[/dim]")
            console.print()

            from rich.table import Table
            table = Table(title=f"Unused Bookmarks ({len(unused)})", border_style="yellow")
            table.add_column("#", style="dim", width=4)
            table.add_column("Name", max_width=40, overflow="ellipsis")
            table.add_column("Folder", max_width=30, overflow="ellipsis", style="dim")
            table.add_column("URL", max_width=50, overflow="ellipsis", style="dim")

            for i, bm in enumerate(unused, 1):
                table.add_row(str(i), bm.name, bm.path, bm.url)

            console.print(table)
            return

        history = history_analyzer.filter(
            include=include,
            exclude=exclude,
            bookmarked_urls=bookmarked_urls,
            aggregate=aggregate,
            aggregate_domains_by_url=aggregate_url,
            aggregate_domains_by_domain=aggregate_domain,
            days=days,
        )
        if effective_top:
            history = history[:effective_top]

        extensions_analyzer = ExtensionsAnalyzer(chrome_profile.path)
        extensions = extensions_analyzer.analyze()

    # Generate and print report
    report = AnalysisReport(
        profile=chrome_profile,
        bookmarks=bookmarks,
        history=history,
        extensions=extensions,
    )
    print_report(report, console)


@app.command()
def export(
    profile: Annotated[
        Optional[str],
        typer.Option("--profile", "-p", help="Profile name (default: Default)"),
    ] = None,
    output: Annotated[
        Path,
        typer.Option("--output", "-o", help="Output directory"),
    ] = Path("./chromemate-export"),
    bookmarks: Annotated[
        bool,
        typer.Option("--bookmarks", "-b", help="Export bookmarks"),
    ] = True,
    extensions: Annotated[
        bool,
        typer.Option("--extensions", "-e", help="Export extensions list"),
    ] = True,
    history: Annotated[
        bool,
        typer.Option("--history", help="Export browsing history ranked by usage"),
    ] = True,
    top: Annotated[
        Optional[int],
        typer.Option("--top", "-t", help="Limit results (default: 100)"),
    ] = None,
    include: Annotated[
        Optional[list[str]],
        typer.Option("--include", "-i", help="Only include URLs containing pattern (can repeat)"),
    ] = None,
    exclude: Annotated[
        Optional[list[str]],
        typer.Option("--exclude", "-x", help="Exclude URLs containing pattern (can repeat)"),
    ] = None,
    bookmarked_only: Annotated[
        bool,
        typer.Option("--bookmarked-only", "-B", help="Only export sites that are bookmarked"),
    ] = False,
    unused_bookmarks: Annotated[
        bool,
        typer.Option("--unused", "-U", help="Export bookmarks that have never been visited"),
    ] = False,
    aggregate: Annotated[
        Optional[str],
        typer.Option("--aggregate", "-a", help="Aggregate all by: 'url' (base URL) or 'domain'"),
    ] = None,
    aggregate_url: Annotated[
        Optional[list[str]],
        typer.Option("--aggregate-url", help="Aggregate by URL for domains matching pattern"),
    ] = None,
    aggregate_domain: Annotated[
        Optional[list[str]],
        typer.Option("--aggregate-domain", help="Aggregate by domain for domains matching pattern"),
    ] = None,
    days: Annotated[
        Optional[int],
        typer.Option("--days", "-d", help="Only include history from the last N days"),
    ] = None,
    include_unvisited: Annotated[
        Optional[list[str]],
        typer.Option("--include-unvisited", help="Include unvisited bookmarks matching pattern"),
    ] = None,
    count_only: Annotated[
        bool,
        typer.Option("--count", "-c", help="Only show count by folder, don't export"),
    ] = False,
) -> None:
    """Export profile data for migration."""
    chrome_profile = _get_profile(profile)

    # Validate aggregate option
    if aggregate and aggregate not in ("url", "domain"):
        console.print("[red]Error: --aggregate must be 'url' or 'domain'[/red]")
        raise typer.Exit(1)

    # Determine effective top limit
    # If --days is set but --top is not, don't limit results
    effective_top = top if top is not None else (None if days or unused_bookmarks else 100)

    # Always need bookmarks if bookmarked_only filter is used
    bookmarks_analyzer = BookmarksAnalyzer(chrome_profile.path)
    bm_list = bookmarks_analyzer.analyze()
    bookmarked_urls = {b.url for b in bm_list} if bookmarked_only else None

    # If filtering bookmarks by usage, we need to run history analysis first
    filtered_bookmark_urls: set[str] | None = None

    # Handle unused bookmarks mode
    if unused_bookmarks and bookmarks:
        history_analyzer = HistoryAnalyzer(chrome_profile.path)
        history_analyzer.analyze(limit=HISTORY_QUERY_LIMIT)
        all_history = history_analyzer.filter(days=days)

        # Find bookmarks that were never visited
        unused = _find_unused_bookmarks(bm_list, all_history)

        # Apply include/exclude filters
        if include:
            unused = [b for b in unused if any(p.lower() in b.url.lower() for p in include)]
        if exclude:
            unused = [b for b in unused if not any(p.lower() in b.url.lower() for p in exclude)]

        if effective_top:
            unused = unused[:effective_top]

        # Export unused bookmarks
        export_bookmarks_html(unused, output / "unused_bookmarks.html")
        console.print(
            f"[green]✓[/green] Exported {len(unused)} unused bookmarks to unused_bookmarks.html"
        )
        if days:
            console.print(f"[dim](bookmarks not visited in the last {days} days)[/dim]")
        return

    if bookmarked_only and bookmarks:
        # Run history analysis to find which bookmarked URLs are actually used
        history_analyzer = HistoryAnalyzer(chrome_profile.path)
        history_analyzer.analyze(limit=HISTORY_QUERY_LIMIT)
        used_entries = history_analyzer.filter(
            include=include,
            exclude=exclude,
            bookmarked_urls={b.url for b in bm_list},
            days=days,
        )
        # Apply top limit if specified
        if effective_top:
            used_entries = used_entries[:effective_top]
        filtered_bookmark_urls = {e.url for e in used_entries}

        # Also include unvisited bookmarks matching --include-unvisited patterns
        if include_unvisited:
            unvisited_bookmarks = [
                b for b in bm_list
                if b.url not in filtered_bookmark_urls
                and any(p.lower() in b.url.lower() for p in include_unvisited)
            ]
            # Apply exclude filter to unvisited as well
            if exclude:
                unvisited_bookmarks = [
                    b for b in unvisited_bookmarks
                    if not any(p.lower() in b.url.lower() for p in exclude)
                ]
            filtered_bookmark_urls.update(b.url for b in unvisited_bookmarks)

    # Handle --count mode: show breakdown by folder without exporting
    if count_only and bookmarks and bm_list:
        from collections import defaultdict

        from rich.table import Table

        # Determine which bookmarks would be exported
        if filtered_bookmark_urls:
            to_export = [b for b in bm_list if b.url in filtered_bookmark_urls]
            to_discard = [b for b in bm_list if b.url not in filtered_bookmark_urls]
        else:
            to_export = bm_list
            to_discard = []

        # Count exported bookmarks by folder
        export_folder_counts: dict[str, int] = defaultdict(int)
        for b in to_export:
            folder = b.path.rsplit("/", 1)[0] if "/" in b.path else b.path
            export_folder_counts[folder] += 1

        # Count discarded bookmarks by folder
        discard_folder_counts: dict[str, int] = defaultdict(int)
        for b in to_discard:
            folder = b.path.rsplit("/", 1)[0] if "/" in b.path else b.path
            discard_folder_counts[folder] += 1

        # Build tree structure
        console.print()
        console.print("[bold]Bookmark Export Preview[/bold]")
        console.print()

        # Show table with folder counts - exported
        table = Table(title="✓ Bookmarks to Export", border_style="green")
        table.add_column("Folder", style="cyan")
        table.add_column("Count", justify="right", style="green")

        for folder in sorted(export_folder_counts.keys()):
            display_folder = folder.replace("bookmark_bar/", "📁 ").replace("/", " / ")
            table.add_row(display_folder, str(export_folder_counts[folder]))

        console.print(table)

        # Show folders that will be discarded with counts
        if discard_folder_counts:
            console.print()
            discard_table = Table(title="✗ Bookmarks to Discard", border_style="yellow")
            discard_table.add_column("Folder", style="dim")
            discard_table.add_column("Count", justify="right", style="yellow")

            for folder in sorted(discard_folder_counts.keys()):
                display_folder = folder.replace("bookmark_bar/", "📁 ").replace("/", " / ")
                discard_table.add_row(display_folder, str(discard_folder_counts[folder]))

            console.print(discard_table)

        # Summary
        console.print()
        console.print("[bold]Summary:[/bold]")
        console.print(f"  [green]✓ Export:[/green]  {len(to_export)} bookmarks")
        console.print(f"  [yellow]✗ Discard:[/yellow] {len(to_discard)} bookmarks")
        console.print(f"  [dim]  Total:[/dim]   {len(bm_list)} bookmarks")
        console.print()
        console.print("[dim]Run without --count to export.[/dim]")
        return

    # Skip directory creation if count_only
    if not count_only:
        output.mkdir(parents=True, exist_ok=True)

    with console.status("[bold blue]Exporting profile data..."):
        if bookmarks and bm_list:
            if filtered_bookmark_urls:
                # Export only bookmarks that match the filtered URLs
                filtered_bookmarks = [b for b in bm_list if b.url in filtered_bookmark_urls]
                export_bookmarks_html(filtered_bookmarks, output / "bookmarks.html")

                # Build descriptive message
                count = len(filtered_bookmarks)
                console.print(f"[green]✓[/green] Exported {count} bookmarks to bookmarks.html")
            else:
                export_bookmarks_html(bm_list, output / "bookmarks.html")
                console.print(f"[green]✓[/green] Exported {len(bm_list)} bookmarks")

        if history:
            history_analyzer = HistoryAnalyzer(chrome_profile.path)
            history_analyzer.analyze(limit=HISTORY_QUERY_LIMIT)
            hist_list = history_analyzer.filter(
                include=include,
                exclude=exclude,
                bookmarked_urls=bookmarked_urls,
                aggregate=aggregate,
                aggregate_domains_by_url=aggregate_url,
                aggregate_domains_by_domain=aggregate_domain,
                days=days,
            )
            if effective_top:
                hist_list = hist_list[:effective_top]
            if hist_list:
                export_history_csv(hist_list, output / "top_sites.csv")
                export_history_json(hist_list, output / "top_sites.json")
                export_history_markdown(hist_list, output / "top_sites.md")
                label = "bookmarked sites" if bookmarked_only else "top sites"
                if aggregate:
                    label = f"aggregated ({aggregate}) {label}"
                console.print(f"[green]✓[/green] Exported {len(hist_list)} {label}")

        if extensions:
            extensions_analyzer = ExtensionsAnalyzer(chrome_profile.path)
            ext_list = extensions_analyzer.analyze()
            enabled = [e for e in ext_list if e.enabled]
            if enabled:
                export_extensions_json(enabled, output / "extensions.json")
                export_extensions_markdown(enabled, output / "extensions.md")
                console.print(f"[green]✓[/green] Exported {len(enabled)} extensions")

    console.print(f"\n[bold green]Export complete![/bold green] Output: {output}")


def _get_profile(name: str | None) -> ChromeProfile:
    """Get a Chrome profile by name, or default."""
    if name is None:
        name = "Default"

    profile = get_profile_by_name(name)
    if profile is None:
        console.print(f"[red]Profile '{name}' not found.[/red]")
        console.print("Run 'chromemate profiles' to see available profiles.")
        raise typer.Exit(1)

    return profile


@app.command("merge-history")
def merge_history(
    source: Annotated[
        str,
        typer.Argument(help="Source profile name (to copy history FROM)"),
    ],
    target: Annotated[
        str,
        typer.Argument(help="Target profile name (to merge history INTO)"),
    ],
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run", "-n", help="Preview changes without modifying anything"),
    ] = False,
    yes: Annotated[
        bool,
        typer.Option("--yes", "-y", help="Skip confirmation prompt"),
    ] = False,
) -> None:
    """
    Merge browsing history from one profile into another.

    This combines history from both profiles so Chrome will suggest
    previously visited sites from the old profile in the new one.

    IMPORTANT: Chrome must be completely closed before running this command.

    Examples:

        chromemate merge-history "Profile 1" Default --dry-run

        chromemate merge-history "Old Work" "New Work" -y
    """
    source_profile = _get_profile(source)
    target_profile = _get_profile(target)

    if source_profile.path == target_profile.path:
        console.print("[red]Error: Source and target profiles must be different.[/red]")
        raise typer.Exit(1)

    merger = HistoryMerger(
        source_profile=source_profile.path,
        target_profile=target_profile.path,
        dry_run=dry_run,
    )

    # Show preview
    console.print()
    console.print("[bold]History Merge Preview[/bold]")
    console.print()
    console.print(f"  Source: [cyan]{source_profile.display_name}[/cyan] ({source_profile.name})")
    console.print(f"  Target: [cyan]{target_profile.display_name}[/cyan] ({target_profile.name})")
    console.print()

    try:
        with console.status("[bold blue]Analyzing profiles..."):
            preview = merger.preview()
    except FileNotFoundError as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)

    from rich.table import Table

    table = Table(title="Profile Statistics", border_style="blue")
    table.add_column("Profile", style="cyan")
    table.add_column("URLs", justify="right")
    table.add_column("Visits", justify="right")

    table.add_row(
        f"Source ({source_profile.name})",
        str(preview["source_urls"]),
        str(preview["source_visits"]),
    )
    table.add_row(
        f"Target ({target_profile.name})",
        str(preview["target_urls"]),
        str(preview["target_visits"]),
    )

    console.print(table)
    console.print()

    console.print("[bold]Merge Plan:[/bold]")
    new_urls = preview['new_urls_to_add']
    update_urls = preview['existing_urls_to_update']
    console.print(f"  [green]+[/green] New URLs: [green]{new_urls}[/green]")
    console.print(f"  [yellow]~[/yellow] URLs to update: [yellow]{update_urls}[/yellow]")
    console.print()

    if dry_run:
        console.print("[dim]Dry run mode - no changes will be made.[/dim]")
        return

    if preview["new_urls_to_add"] == 0 and preview["existing_urls_to_update"] == 0:
        console.print("[yellow]Nothing to merge - target has all source history.[/yellow]")
        return

    # Confirm
    if not yes:
        console.print("[bold yellow]WARNING:[/bold yellow] Make sure Chrome is completely closed!")
        console.print()
        confirm = typer.confirm("Proceed with merge?")
        if not confirm:
            console.print("[dim]Merge cancelled.[/dim]")
            raise typer.Exit(0)

    # Perform merge
    try:
        with console.status("[bold blue]Merging history..."):
            stats = merger.merge()
    except PermissionError as e:
        console.print(f"[red]Error: {e}[/red]")
        console.print("\n[yellow]Tip: Close Chrome completely and try again.[/yellow]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Error during merge: {e}[/red]")
        raise typer.Exit(1)

    console.print()
    console.print("[bold green]Merge complete![/bold green]")
    console.print()
    console.print(f"  [green]+[/green] URLs added: [green]{stats.urls_added}[/green]")
    console.print(f"  [yellow]~[/yellow] URLs updated: [yellow]{stats.urls_updated}[/yellow]")
    console.print(f"  [blue]>[/blue] Visits added: [blue]{stats.visits_added}[/blue]")
    console.print()
    console.print("[dim]Start Chrome to see the merged history in action.[/dim]")


if __name__ == "__main__":
    app()

