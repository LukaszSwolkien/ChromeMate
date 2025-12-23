# ChromeMate

Chrome profile migration tool. Analyzes bookmarks, history, and extensions to selectively export only what you use.

## Features

| Feature | Description |
|---------|-------------|
| Usage Analysis | Ranks bookmarks and sites by visit frequency |
| Selective Export | Exports only used items with preserved folder structure |
| Unused Detection | Finds bookmarks never visited for cleanup |
| Local Processing | All data stays on your machine |

## Installation

### Pre-built Binary (macOS ARM64)

Download the latest release from [GitHub Releases](https://github.com/LukaszSwolkien/ChromeMate/releases).

```bash
# Make executable
chmod +x chromemate

# First run: Right-click → Open (or allow in System Settings → Privacy & Security)
./chromemate --help
```

### From Source

Requires Python 3.11+ and [uv](https://github.com/astral-sh/uv).

```bash
# Install uv (if not installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clone and setup
git clone git@github.com:LukaszSwolkien/ChromeMate.git
cd ChromeMate
uv sync
```

### Shell Completion

```bash
# zsh - add to ~/.zshrc
source /path/to/completions/chromemate.zsh

# bash - add to ~/.bashrc
source /path/to/completions/chromemate.bash
```

Requires `chromemate` in PATH (e.g., `cp chromemate /usr/local/bin/`).

## Usage

With binary, replace `uv run chromemate` with `./chromemate`.

```bash
# List available profiles
uv run chromemate profiles

# Analyze specific profile
uv run chromemate analyze --profile "Profile 1"

# Analyze bookmarked sites by usage (Default profile if not specified)
uv run chromemate analyze --bookmarked-only --days 365

# Find unused bookmarks
uv run chromemate analyze --unused

# Export used bookmarks (preview first, then export)
uv run chromemate export --bookmarked-only --days 300 --count
uv run chromemate export --bookmarked-only --days 300 --output ./migration
```

### Export

```bash
# Export used bookmarks + all cisco bookmarks regardless of usage (workaround for redirect mechanism)
uv run chromemate export --bookmarked-only --days 400 --include-unvisited cisco --output ./combined

# Preview export count by folder without exporting
uv run chromemate export --bookmarked-only --days 400 --include-unvisited cisco --count
```

### Merge History

```bash
# Merge history from old profile into new one (Chrome must be closed)
uv run chromemate merge-history "OldProfile" "NewProfile" --dry-run
uv run chromemate merge-history "OldProfile" "NewProfile" -y
```

### CLI Options

| Option | Short | Commands | Description |
|--------|-------|----------|-------------|
| `--profile` | `-p` | analyze, export | Chrome profile name (default: `Default`) |
| `--top` | `-t` | analyze, export | Limit results (default: 10/100) |
| `--days` | `-d` | analyze, export | History from last N days |
| `--include` | `-i` | analyze, export | Include URLs matching pattern |
| `--exclude` | `-x` | analyze, export | Exclude URLs matching pattern |
| `--bookmarked-only` | `-B` | analyze, export | Only bookmarked sites |
| `--unused` | `-U` | analyze, export | Bookmarks never visited |
| `--include-unvisited` | | export | Add unvisited bookmarks matching pattern |
| `--count` | `-c` | export | Preview count without exporting |
| `--aggregate` | `-a` | analyze, export | Aggregate by `url` or `domain` |
| `--aggregate-url` | | analyze, export | Aggregate by URL for matching domains |
| `--aggregate-domain` | | analyze, export | Aggregate by domain for matching domains |
| `--output` | `-o` | export | Output directory |

### Output Files

| File | Format | Use |
|------|--------|-----|
| `bookmarks.html` | HTML | Import via chrome://bookmarks |
| `unused_bookmarks.html` | HTML | Review for cleanup |
| `top_sites.csv` | CSV | Spreadsheet analysis |
| `top_sites.json` | JSON | Programmatic access |
| `extensions.json` | JSON | Extension list with install URLs |
| `extensions.md` | Markdown | Human-readable with Web Store links |

## Development

```bash
uv sync --extra dev
uv run pytest
uv run pytest --cov=chromemate
uv run ruff check src/
```

### Building Release

```bash
uv run pyinstaller --onefile --name chromemate src/chromemate/cli.py
# Binary output: dist/chromemate
```

## Data Sources

| Data | File |
|------|------|
| Bookmarks | `Bookmarks` (JSON) |
| History | `History` (SQLite) |
| Extensions | `Preferences` (JSON) |

History database is copied to a temp file, so Chrome can remain open during analysis.

## License

MIT
