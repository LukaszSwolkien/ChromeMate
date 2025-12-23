"""History merger for Chrome profiles.

Merges browsing history from a source profile into a target profile,
allowing Chrome to suggest previously visited sites from the old profile.
"""

import shutil
import sqlite3
import tempfile
from dataclasses import dataclass
from pathlib import Path


@dataclass
class MergeStats:
    """Statistics from a history merge operation."""

    urls_added: int = 0
    urls_updated: int = 0
    visits_added: int = 0
    urls_skipped: int = 0


@dataclass
class HistoryMerger:
    """Merges browsing history between Chrome profiles."""

    source_profile: Path
    target_profile: Path
    dry_run: bool = False

    def merge(self) -> MergeStats:
        """
        Merge history from source profile into target profile.

        Chrome must be closed for this operation to succeed.

        Returns:
            MergeStats with counts of merged entries
        """
        source_history = self.source_profile / "History"
        target_history = self.target_profile / "History"

        if not source_history.exists():
            raise FileNotFoundError(f"Source history not found: {source_history}")
        if not target_history.exists():
            raise FileNotFoundError(f"Target history not found: {target_history}")

        # Work on copies to avoid corruption
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            source_copy = tmp_path / "source_history.db"
            target_copy = tmp_path / "target_history.db"

            shutil.copy2(source_history, source_copy)
            shutil.copy2(target_history, target_copy)

            stats = self._merge_databases(source_copy, target_copy)

            # Copy back to target if not dry run
            if not self.dry_run and (stats.urls_added > 0 or stats.urls_updated > 0):
                try:
                    shutil.copy2(target_copy, target_history)
                except PermissionError as e:
                    raise PermissionError(
                        "Cannot write to Chrome history. Is Chrome running? "
                        "Please close Chrome and try again."
                    ) from e

        return stats

    def _merge_databases(self, source_db: Path, target_db: Path) -> MergeStats:
        """Merge source history database into target database."""
        stats = MergeStats()

        source_conn = sqlite3.connect(source_db)
        target_conn = sqlite3.connect(target_db)

        try:
            # Build mapping of existing URLs in target
            target_urls = self._get_url_mapping(target_conn)

            # Get all URLs from source
            source_cursor = source_conn.execute(
                """
                SELECT id, url, title, visit_count, typed_count, last_visit_time, hidden
                FROM urls
                WHERE visit_count > 0
                """
            )

            # Map old source URL IDs to new target URL IDs
            url_id_mapping: dict[int, int] = {}

            for row in source_cursor:
                src_id, url, title, visit_count, typed_count, last_visit_time, hidden = row

                if url in target_urls:
                    # URL exists in target - update counts
                    target_id, target_visits, target_typed, target_last_visit = target_urls[url]
                    url_id_mapping[src_id] = target_id

                    new_visit_count = target_visits + visit_count
                    new_typed_count = target_typed + typed_count
                    new_last_visit = max(target_last_visit, last_visit_time)

                    target_conn.execute(
                        """
                        UPDATE urls
                        SET visit_count = ?, typed_count = ?, last_visit_time = ?
                        WHERE id = ?
                        """,
                        (new_visit_count, new_typed_count, new_last_visit, target_id),
                    )
                    stats.urls_updated += 1
                else:
                    # New URL - insert
                    cursor = target_conn.execute(
                        """
                        INSERT INTO urls
                        (url, title, visit_count, typed_count, last_visit_time, hidden)
                        VALUES (?, ?, ?, ?, ?, ?)
                        """,
                        (url, title, visit_count, typed_count, last_visit_time, hidden),
                    )
                    new_id = cursor.lastrowid
                    url_id_mapping[src_id] = new_id
                    target_urls[url] = (new_id, visit_count, typed_count, last_visit_time)
                    stats.urls_added += 1

            # Merge visits table
            # Get existing visit times in target to avoid duplicates
            existing_visits = self._get_existing_visits(target_conn)

            source_visits = source_conn.execute(
                """
                SELECT url, visit_time, from_visit, transition, segment_id,
                       visit_duration, incremented_omnibox_typed_score,
                       consider_for_ntp_most_visited
                FROM visits
                """
            )

            for visit in source_visits:
                url_id, visit_time, from_visit, transition, segment_id, \
                    visit_duration, incr_omnibox, consider_ntp = visit

                # Skip if source URL wasn't mapped (no visits)
                if url_id not in url_id_mapping:
                    continue

                new_url_id = url_id_mapping[url_id]

                # Check for duplicate visit (same URL + same time)
                visit_key = (new_url_id, visit_time)
                if visit_key in existing_visits:
                    continue

                # Insert visit with mapped URL ID
                # Note: from_visit references aren't preserved (would need complex remapping)
                target_conn.execute(
                    """
                    INSERT INTO visits (
                        url, visit_time, from_visit, transition, segment_id,
                        visit_duration, incremented_omnibox_typed_score,
                        consider_for_ntp_most_visited
                    )
                    VALUES (?, ?, 0, ?, ?, ?, ?, ?)
                    """,
                    (new_url_id, visit_time, transition, segment_id or 0,
                     visit_duration, incr_omnibox, consider_ntp),
                )
                existing_visits.add(visit_key)
                stats.visits_added += 1

            target_conn.commit()

        finally:
            source_conn.close()
            target_conn.close()

        return stats

    def _get_url_mapping(self, conn: sqlite3.Connection) -> dict[str, tuple[int, int, int, int]]:
        """Get mapping of URL -> (id, visit_count, typed_count, last_visit_time)."""
        cursor = conn.execute(
            "SELECT id, url, visit_count, typed_count, last_visit_time FROM urls"
        )
        return {
            row[1]: (row[0], row[2], row[3], row[4])
            for row in cursor
        }

    def _get_existing_visits(self, conn: sqlite3.Connection) -> set[tuple[int, int]]:
        """Get set of (url_id, visit_time) for existing visits."""
        cursor = conn.execute("SELECT url, visit_time FROM visits")
        return {(row[0], row[1]) for row in cursor}

    def preview(self) -> dict[str, int]:
        """
        Preview what would be merged without modifying anything.

        Returns:
            Dictionary with counts of URLs and visits that would be merged
        """
        source_history = self.source_profile / "History"
        target_history = self.target_profile / "History"

        if not source_history.exists():
            raise FileNotFoundError(f"Source history not found: {source_history}")
        if not target_history.exists():
            raise FileNotFoundError(f"Target history not found: {target_history}")

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            source_copy = tmp_path / "source_history.db"
            target_copy = tmp_path / "target_history.db"

            shutil.copy2(source_history, source_copy)
            shutil.copy2(target_history, target_copy)

            source_conn = sqlite3.connect(source_copy)
            target_conn = sqlite3.connect(target_copy)

            try:
                # Count source entries
                source_urls = source_conn.execute(
                    "SELECT COUNT(*) FROM urls WHERE visit_count > 0"
                ).fetchone()[0]
                source_visits = source_conn.execute(
                    "SELECT COUNT(*) FROM visits"
                ).fetchone()[0]

                # Count target entries
                target_urls = target_conn.execute(
                    "SELECT COUNT(*) FROM urls WHERE visit_count > 0"
                ).fetchone()[0]
                target_visits = target_conn.execute(
                    "SELECT COUNT(*) FROM visits"
                ).fetchone()[0]

                target_url_set = {
                    row[0] for row in target_conn.execute("SELECT url FROM urls")
                }
                source_url_list = [
                    row[0] for row in source_conn.execute(
                        "SELECT url FROM urls WHERE visit_count > 0"
                    )
                ]
                new_urls = sum(1 for url in source_url_list if url not in target_url_set)
                existing_urls = len(source_url_list) - new_urls

            finally:
                source_conn.close()
                target_conn.close()

        return {
            "source_urls": source_urls,
            "source_visits": source_visits,
            "target_urls": target_urls,
            "target_visits": target_visits,
            "new_urls_to_add": new_urls,
            "existing_urls_to_update": existing_urls,
        }

