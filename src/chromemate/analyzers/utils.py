"""Shared utilities for Chrome data analyzers."""

# Chrome/WebKit epoch offset: microseconds between 1601-01-01 and 1970-01-01
WEBKIT_EPOCH_OFFSET = 11644473600000000


def convert_webkit_timestamp(webkit_time: int | str | None) -> int | None:
    """
    Convert Chrome's WebKit timestamp to Unix timestamp.
    Chrome uses microseconds since Jan 1, 1601.
    Returns Unix timestamp (seconds since Jan 1, 1970) or None.
    """
    if webkit_time is None:
        return None
    try:
        webkit_ts = int(webkit_time)
        unix_ts = (webkit_ts - WEBKIT_EPOCH_OFFSET) // 1000000
        return unix_ts if unix_ts > 0 else None
    except (ValueError, TypeError):
        return None


