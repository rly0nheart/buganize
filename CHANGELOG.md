# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
