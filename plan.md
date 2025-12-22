# ChromeMate Implementation Plan

## Overview

ChromeMate is a Python CLI tool that analyzes Chrome browser profiles and helps users selectively migrate data to a new profile. All processing is done locally for privacy.

---

## Technology Stack

- **Language**: Python 3.11+
- **Dependency Manager**: uv
- **CLI Framework**: typer (lightweight, modern CLI)
- **Data Processing**: sqlite3 (Chrome stores data in SQLite), json
- **Output**: rich (terminal formatting and reports)

---

## Project Structure

```
ChromeMate/
├── src/
│   └── chromemate/
│       ├── __init__.py
│       ├── cli.py              # CLI entry point
│       ├── profile.py          # Chrome profile discovery
│       ├── analyzers/
│       │   ├── __init__.py
│       │   ├── bookmarks.py    # Bookmark analysis
│       │   ├── history.py      # History/top sites analysis
│       │   └── extensions.py   # Extension usage analysis
│       ├── report.py           # Report generation
│       └── exporter.py         # Export selected data
├── tests/
│   └── ...
├── pyproject.toml
├── plan.md
├── docs/
│   └── spec.md
└── README.md
```

---

## Implementation Phases

### Phase 1: Project Setup

- [ ] Initialize project with uv
- [ ] Create `pyproject.toml` with dependencies
- [ ] Set up basic CLI structure with typer
- [ ] Implement Chrome profile discovery (find profile paths on macOS/Windows/Linux)

### Phase 2: Data Readers

- [ ] **Bookmarks Reader**: Parse `Bookmarks` JSON file
- [ ] **History Reader**: Query `History` SQLite database for visit counts and timestamps
- [ ] **Extensions Reader**: Parse `Extensions` folder and `Preferences` for installed extensions

### Phase 3: Usage Analysis

- [ ] **Bookmark Analysis**: Identify bookmarks with visit history (cross-reference with History)
- [ ] **Top Sites Analysis**: Extract most visited URLs from history
- [ ] **Extension Analysis**: Identify active vs. disabled extensions, last used timestamps

### Phase 4: Report Generation

- [ ] Generate terminal-based usage report with rich
- [ ] Show categorized data: frequently used bookmarks, top sites, active extensions
- [ ] Provide recommendations on what to migrate

### Phase 5: Selective Export

- [ ] Export selected bookmarks as HTML (Chrome-importable format)
- [ ] Generate extension list with install URLs
- [ ] Create migration summary document

---

## Chrome Data Locations

| OS | Profile Path |
|----|--------------|
| macOS | `~/Library/Application Support/Google/Chrome/` |
| Windows | `%LOCALAPPDATA%\Google\Chrome\User Data\` |
| Linux | `~/.config/google-chrome/` |

### Key Files

- `Bookmarks` - JSON file with bookmark tree
- `History` - SQLite database with browsing history
- `Preferences` - JSON with settings and extension state
- `Extensions/` - Folder with installed extensions

---

## CLI Commands

```bash
# Discover available Chrome profiles
chromemate profiles

# Analyze a profile
chromemate analyze [--profile NAME]

# Generate migration report
chromemate report [--profile NAME] [--output FILE]

# Export selected data
chromemate export [--profile NAME] [--bookmarks] [--extensions] [--output DIR]
```

---

## Dependencies

```toml
[project]
dependencies = [
    "typer>=0.9.0",
    "rich>=13.0.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0.0",
    "ruff>=0.1.0",
]
```

---

## Milestones

| Milestone | Deliverable | Estimated Effort |
|-----------|-------------|------------------|
| M1 | Project setup + profile discovery | 1 day |
| M2 | Data readers (bookmarks, history, extensions) | 2 days |
| M3 | Usage analysis + scoring | 2 days |
| M4 | Report generation | 1 day |
| M5 | Export functionality | 1 day |
| M6 | Testing + documentation | 1 day |

---

## Testing Strategy

### Test Structure

```
tests/
├── conftest.py              # Shared fixtures
├── fixtures/                # Sample Chrome data files
│   ├── Bookmarks            # Sample bookmarks JSON
│   ├── History              # Sample SQLite database
│   └── Preferences          # Sample preferences JSON
├── test_profile.py          # Profile discovery tests
├── test_bookmarks.py        # Bookmark parsing tests
├── test_history.py          # History analysis tests
├── test_extensions.py       # Extension analysis tests
├── test_report.py           # Report generation tests
└── test_exporter.py         # Export functionality tests
```

### Testing Approach

| Component | Test Type | Method |
|-----------|-----------|--------|
| Profile discovery | Unit | Mock filesystem paths, test OS detection |
| Bookmarks reader | Unit | Use fixture JSON files with known structure |
| History reader | Unit | Use fixture SQLite DB with sample visits |
| Extensions reader | Unit | Use fixture Preferences JSON |
| Usage analysis | Unit | Test scoring logic with controlled inputs |
| Report generation | Integration | Verify output format with sample data |
| CLI commands | Integration | Use typer's test runner (`CliRunner`) |

### Test Fixtures

Create minimal but realistic Chrome data files:

**`fixtures/Bookmarks`** - JSON with nested folders and bookmarks
```json
{
  "roots": {
    "bookmark_bar": {
      "children": [
        {"name": "GitHub", "url": "https://github.com"},
        {"name": "Work", "type": "folder", "children": [...]}
      ]
    }
  }
}
```

**`fixtures/History`** - SQLite with `urls` and `visits` tables
```sql
CREATE TABLE urls (id, url, title, visit_count, last_visit_time);
CREATE TABLE visits (id, url, visit_time);
-- Insert sample rows with realistic timestamps
```

### Key Test Cases

1. **Profile discovery**
   - `test_profile_discovery_finds_default_profile`
   - `test_profile_discovery_handles_missing_chrome`
   - `test_profile_discovery_lists_multiple_profiles`

2. **Bookmarks**
   - `test_bookmarks_parses_nested_folders`
   - `test_bookmarks_handles_empty_file`
   - `test_bookmarks_extracts_urls_correctly`

3. **History**
   - `test_history_ranks_by_visit_count`
   - `test_history_filters_by_date_range`
   - `test_history_handles_locked_database`

4. **Extensions**
   - `test_extensions_identifies_enabled_vs_disabled`
   - `test_extensions_extracts_manifest_info`

5. **Export**
   - `test_export_creates_valid_html_bookmarks`
   - `test_export_generates_extension_list`

### Running Tests

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=chromemate

# Run specific module
uv run pytest tests/test_bookmarks.py -v
```

### CI Considerations

- Tests run without actual Chrome installation
- All Chrome data is mocked via fixtures
- No network access required
- Cross-platform compatible (fixture paths normalized)

---

## Notes

- Chrome must be closed when reading History database (SQLite lock)
- Handle gracefully when data files are missing or corrupted
- All paths should be cross-platform compatible

