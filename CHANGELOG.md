# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.1.2] - 2026-02-24

### Changed

- CI workflow now uses `gh` CLI for GitHub releases instead of `softprops/action-gh-release`
- CI checks PyPI for existing versions instead of git tags
- CI consolidated from 3 jobs to a single job

## [1.1.1] - 2026-02-24

### Fixed

- Fix USAGE.md link in README pointing to itself instead of USAGE.md
- Update API docs and project README

## [1.1.0] - 2026-02-24

### Added

- **Severity field** — issues now expose `severity` (S0–S4), parsed independently from priority
- **Duplicate tracking** — `duplicate_issue_ids` shows which issues have been marked as duplicates
- **Blocking issues** — `blocking_issue_ids` sourced from the correct API field
- **Collaborators** — list of collaborator emails on an issue
- **Found-in versions** — `found_in` shows which builds/versions a bug was discovered in
- **In-production flag** — `in_prod` indicates whether a bug has been seen in production
- **View counts** — `views_24h`, `views_7d`, `views_30d` for gauging issue activity
- 14 extra field columns available in CLI output (`severity`, `collaborators`, `found_in`, `in_prod`, `duplicates`,
  `24h_views`, `7d_views`, `30d_views`, and more)
- `buganize trackers` CLI command to list all available trackers and their IDs
- `USAGE.md` — dedicated usage documentation for both the library and CLI
- API reference now documents 14 public trackers and 6 additional endpoints (components, trackers, hotlists,
  relationships)

### Changed

- Severity is shown by default in single-issue detail view
- CLI `--tracker` argument now shows available tracker names in help output
- `Buganize(tracker_id=...)` renamed to `Buganize(tracker=...)` — accepts both names (`"chromium"`) and numeric IDs (`"157"`)

### Fixed

- `details[21]` was incorrectly mapped to blocking issues — it is actually duplicate issue IDs
- Blocking issue IDs are now correctly sourced from the top-level array (`TOP[36]`)
- View counts corrected from `[1d, 7d, total]` to `[24h, 7d, 30d]`

## [1.0.1] - 2026-02-23

### Changed

- Update API docs, and README.md at root

## [1.0.0] - 2026-02-23

### Changed

- Rebrand from "Chromium Issue Tracker" to "Google Issue Tracker" — the client now queries all public trackers by
  default
- Drop `pandas` dependency, all output uses Rich tables and stdlib `csv`/`json` for export
- Drop HTML export format, `--export` now accepts `csv` and `json` only

### Added

- `-t`/`--tracker` flag to scope queries to a specific tracker by name (`chromium`, `fuchsia`) or numeric ID.
  Without it, queries search across all public trackers on the Google Issue Tracker
- `API.md` — reverse-engineered documentation of the issuetracker.google.com API

## [0.2.3] - 2026-02-22

### Changed

- Update package details

### Added

- `buganise` command to the CLI

## [0.2.2] - 2026-02-22

### Changed

- Moved from `buganise` to `buganize`, running pip install on either one will install `buganize` as a library and both
  `buganise` and `buganize` as cli commands.

### Added

- Randomised user agent on each request

## [0.2.1] - 2026-02-21

### Changed

- Remove img/ dir

## [0.2.0] - 2026-02-21

### Added

- Update checker. Runs once a day

## [0.1.0] - 2026-02-21

### Added

- Async Python client (`Buganize`) for the Chromium Issue Tracker
- `search()` for querying issues with pagination support via `next_page()`
- `issue()` for fetching a single issue by ID
- `issues()` for fetching multiple issues in a single request
- `issue_updates()` for fetching comments and field changes on an issue
- `comments()` convenience method for fetching comments in chronological order
- CLI with `buganize` command (search, issue, issues, comments)
- Export to CSV, JSON, and HTML via `-e`/`--export`
- Extra fields display with `-f`/`--fields` and `-F`/`--all-fields`
- Jupyter notebook examples for search, issues, comments, and export
