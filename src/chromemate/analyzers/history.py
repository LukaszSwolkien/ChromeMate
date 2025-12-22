"""History analysis for Chrome profiles."""

import shutil
import sqlite3
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlparse, urlunparse

from chromemate.analyzers.utils import convert_webkit_timestamp

SECONDS_PER_DAY = 86400


@dataclass
class HistoryEntry:
    """Represents a visited URL from history."""

    url: str
    title: str
    visit_count: int
    last_visit_time: int  # Unix timestamp


def _get_base_url(url: str) -> str:
    """Get URL without query parameters and fragments."""
    parsed = urlparse(url)
    # Rebuild URL without query and fragment
    return urlunparse((parsed.scheme, parsed.netloc, parsed.path, "", "", ""))


def _get_domain(url: str) -> str:
    """Get just the domain from a URL."""
    parsed = urlparse(url)
    return parsed.netloc


@dataclass
class HistoryAnalyzer:
    """Analyzes browsing history from a Chrome profile."""

    profile_path: Path
    entries: list[HistoryEntry] = field(default_factory=list)

    def analyze(self, limit: int = 100) -> list[HistoryEntry]:
        """
        Analyze browsing history and return top visited sites.

        Note: Chrome locks the History database while running.
        We copy the file to a temp location to read it safely.
        """
        history_file = self.profile_path / "History"
        if not history_file.exists():
            return []

        # Copy to temp file to avoid lock issues
        with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as tmp:
            tmp_path = Path(tmp.name)

        try:
            shutil.copy2(history_file, tmp_path)
            self.entries = self._query_history(tmp_path, limit)
        except (sqlite3.Error, OSError):
            self.entries = []
        finally:
            tmp_path.unlink(missing_ok=True)

        return self.entries

    def _query_history(self, db_path: Path, limit: int) -> list[HistoryEntry]:
        """Query the history database for top visited URLs."""
        entries: list[HistoryEntry] = []

        conn = sqlite3.connect(db_path)
        try:
            cursor = conn.execute(
                """
                SELECT url, title, visit_count, last_visit_time
                FROM urls
                WHERE visit_count > 0
                ORDER BY visit_count DESC
                LIMIT ?
                """,
                (limit,),
            )

            for row in cursor:
                url, title, visit_count, last_visit_time = row
                entries.append(
                    HistoryEntry(
                        url=url,
                        title=title or "",
                        visit_count=visit_count,
                        last_visit_time=convert_webkit_timestamp(last_visit_time) or 0,
                    )
                )
        finally:
            conn.close()

        return entries

    def get_top_sites(self, n: int = 10) -> list[HistoryEntry]:
        """Get the top N most visited sites."""
        return sorted(self.entries, key=lambda e: e.visit_count, reverse=True)[:n]

    def get_domains(self) -> dict[str, int]:
        """Get aggregated visit counts by domain."""
        domains: dict[str, int] = {}
        for entry in self.entries:
            try:
                domain = urlparse(entry.url).netloc
                if domain:
                    domains[domain] = domains.get(domain, 0) + entry.visit_count
            except Exception:
                continue
        return dict(sorted(domains.items(), key=lambda x: x[1], reverse=True))

    def filter(
        self,
        include: list[str] | None = None,
        exclude: list[str] | None = None,
        bookmarked_urls: set[str] | None = None,
        aggregate: str | None = None,
        aggregate_domains_by_url: list[str] | None = None,
        aggregate_domains_by_domain: list[str] | None = None,
        days: int | None = None,
    ) -> list[HistoryEntry]:
        """
        Filter history entries by domain patterns and/or bookmark membership.

        Args:
            include: Only include URLs containing any of these patterns
            exclude: Exclude URLs containing any of these patterns
            bookmarked_urls: If provided, only include URLs that are in this set
            aggregate: Aggregation mode: "url" (by base URL) or "domain" (by domain)
            aggregate_domains_by_url: List of domain patterns to aggregate by URL
            aggregate_domains_by_domain: List of domain patterns to aggregate by domain
            days: If provided, only include entries from the last N days

        Returns:
            Filtered list of history entries, sorted by visit count
        """
        import time

        filtered = self.entries

        # Filter by time range first (before aggregation)
        if days is not None:
            cutoff_time = int(time.time()) - (days * SECONDS_PER_DAY)
            filtered = [e for e in filtered if e.last_visit_time >= cutoff_time]

        # Filter by bookmarks BEFORE aggregation (use exact URL match)
        if bookmarked_urls is not None:
            filtered = [e for e in filtered if e.url in bookmarked_urls]

        # Selective aggregation by domain patterns
        if aggregate_domains_by_url or aggregate_domains_by_domain:
            filtered = self._aggregate_selective(
                filtered,
                by_url_patterns=aggregate_domains_by_url or [],
                by_domain_patterns=aggregate_domains_by_domain or [],
            )
        # Global aggregation
        elif aggregate == "url":
            filtered = self._aggregate_by_url(filtered)
        elif aggregate == "domain":
            filtered = self._aggregate_by_domain(filtered)

        if include:
            filtered = [
                e for e in filtered
                if any(pattern.lower() in e.url.lower() for pattern in include)
            ]

        if exclude:
            filtered = [
                e for e in filtered
                if not any(pattern.lower() in e.url.lower() for pattern in exclude)
            ]

        return sorted(filtered, key=lambda e: e.visit_count, reverse=True)

    def _aggregate_by_url(self, entries: list[HistoryEntry]) -> list[HistoryEntry]:
        """Combine entries with the same base URL (ignoring query parameters)."""
        aggregated: dict[str, dict] = {}

        for entry in entries:
            base_url = _get_base_url(entry.url)

            if base_url in aggregated:
                data = aggregated[base_url]
                data["total_visits"] += entry.visit_count
                data["last_visit_time"] = max(data["last_visit_time"], entry.last_visit_time)
                # Keep title from entry with most visits (likely the canonical title)
                if entry.visit_count > data["best_title_visits"] and entry.title:
                    data["best_title"] = entry.title
                    data["best_title_visits"] = entry.visit_count
            else:
                aggregated[base_url] = {
                    "total_visits": entry.visit_count,
                    "best_title": entry.title,
                    "best_title_visits": entry.visit_count,
                    "last_visit_time": entry.last_visit_time,
                }

        return [
            HistoryEntry(
                url=base_url,
                title=data["best_title"],
                visit_count=data["total_visits"],
                last_visit_time=data["last_visit_time"],
            )
            for base_url, data in aggregated.items()
        ]

    def _aggregate_by_domain(self, entries: list[HistoryEntry]) -> list[HistoryEntry]:
        """Combine entries by domain, using domain as title."""
        aggregated: dict[str, dict] = {}

        for entry in entries:
            domain = _get_domain(entry.url)
            if not domain:
                continue

            if domain in aggregated:
                data = aggregated[domain]
                data["total_visits"] += entry.visit_count
                data["last_visit_time"] = max(data["last_visit_time"], entry.last_visit_time)
            else:
                aggregated[domain] = {
                    "total_visits": entry.visit_count,
                    "last_visit_time": entry.last_visit_time,
                }

        return [
            HistoryEntry(
                url=f"https://{domain}/",
                title=domain,  # Use domain as title
                visit_count=data["total_visits"],
                last_visit_time=data["last_visit_time"],
            )
            for domain, data in aggregated.items()
        ]

    def _aggregate_selective(
        self,
        entries: list[HistoryEntry],
        by_url_patterns: list[str],
        by_domain_patterns: list[str],
    ) -> list[HistoryEntry]:
        """
        Selectively aggregate entries based on domain patterns.

        - Entries matching by_url_patterns are aggregated by base URL
        - Entries matching by_domain_patterns are aggregated by domain
        - Other entries are left as-is
        """
        to_aggregate_url: list[HistoryEntry] = []
        to_aggregate_domain: list[HistoryEntry] = []
        unchanged: list[HistoryEntry] = []

        for entry in entries:
            url_lower = entry.url.lower()

            if any(p.lower() in url_lower for p in by_domain_patterns):
                to_aggregate_domain.append(entry)
            elif any(p.lower() in url_lower for p in by_url_patterns):
                to_aggregate_url.append(entry)
            else:
                unchanged.append(entry)

        result = unchanged
        if to_aggregate_url:
            result.extend(self._aggregate_by_url(to_aggregate_url))
        if to_aggregate_domain:
            result.extend(self._aggregate_by_domain(to_aggregate_domain))

        return result

