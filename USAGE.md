# Usage

## Table of Contents

1. [Library usage](#library-usage)
    - [Search issues](#search-issues)
    - [Get a single issue](#get-a-single-issue)
    - [Batch get issues](#batch-get-issues)
    - [Get comments](#get-comments)
    - [Get full updates](#get-full-updates)
2. [CLI usage](#cli-usage)
    - [Search](#search)
    - [Tracker selection](#tracker-selection)
    - [Issue](#issue)
    - [Issues (batch)](#issues-batch)
    - [Comments](#comments)
    - [Extra fields](#extra-fields)
    - [Export](#export)
    - [Debug logging](#debug-logging)
    - [Timeout](#timeout)
3. [GUI Usage](#gui-usage)
   - [NixOS Users](#nixos-users)

## Library usage

```python
from buganize import Buganize
```

or

```python
from buganise import Buganise
```

### Search issues

```python
async def search():
    # Search across all public trackers (default)
    async with Buganize() as client:
        result = await client.search("status:open component:Blink", page_size=10)

        print(f"{result.total_count} total matches")
        for issue in result.issues:
            print(f"#{issue.id} [{issue.status.name}] {issue.title}")

        # Pagination
        if result.has_more:
            page2 = await client.next_page(result)
            for issue in page2.issues:
                print(f"#{issue.id} [{issue.status.name}] {issue.title}")
```

```python
async def search_chromium():
    # Search only within the Chromium tracker
    async with Buganize(trackers=["chromium"]) as client:
        result = await client.search("status:open component:Blink")
```

```python
async def search_multiple():
    # Search across Chromium and Fuchsia trackers
    async with Buganize(trackers=["chromium", "fuchsia"]) as client:
        result = await client.search("status:open")
```

### Get a single issue

```python
async def get_issue():
    async with Buganize() as client:
        issue = await client.issue(40060244)

        print(issue.title)
        print(issue.url)  # https://issuetracker.google.com/issues/40060244
        print(issue.body)  # Description
        print(issue.status.name)  # e.g. "FIXED"
        print(issue.priority.name)  # e.g. "P2"
        print(issue.severity.name)  # e.g. "S2" (may differ from priority)
        print(issue.os)  # e.g. ["Linux", "Mac", "Windows"]
        print(issue.cve)  # e.g. ["CVE-2024-1234"]
        print(issue.found_in)  # e.g. ["CP21.260116.011.A1"]
        print(issue.in_prod)  # True or None
        print(issue.collaborators)  # e.g. ["user@example.com"]
        print(issue.duplicate_issue_ids)  # e.g. [12345, 67890]
        print(issue.blocking_issue_ids)  # e.g. [11111]
        print(issue.views_24h, issue.views_7d, issue.views_30d)  # e.g. 5, 20, 100
```

### Batch get issues

```python
async def batch_get():
    async with Buganize() as client:
        issues = await client.issues([40060244, 485912774, 486077869])

        for issue in issues:
            print(f"#{issue.id} - {issue.title}")
```

### Get comments

```python
async def get_comments():
    async with Buganize() as client:
        comments = await client.comments(486077869)

        for comment in comments:
            print(f"#{comment.comment_number} by {comment.author}")
            print(comment.body)
```

### Get full updates

Updates include both comments and field changes (status changes, priority changes, etc.):

```python
async def get_updates():
    async with Buganize() as client:
        result = await client.issue_updates(486077869)

        print(f"{result.total_count} total updates")

        # Just the comments, in chronological order
        for comment in result.comments:
            print(f"#{comment.comment_number}: {comment.body[:80]}")

        # All updates (newest first), including field changes
        for update in result.updates:
            if update.field_changes:
                changed = ", ".join(fc.field for fc in update.field_changes)
                print(f"  Fields changed: {changed}")
            if update.comment:
                print(f"  Comment: {update.comment.body[:80]}")
```

## CLI usage

Run with `python -m buganize <command>` or just `buganize <command>`.

### Search

```bash
# Search across all public trackers (default)
buganize search "status:open"

# Combined filters
buganize search "status:open component:Blink"

# Results per page (choices: 25, 50, 100, 250)
buganize search "type:bug" -n 100

# Fetch a total of 200 results, paginating as needed
buganize search "status:open" -l 200
```

### Tracker selection

By default, buganize searches across all public trackers on issuetracker.google.com. Use `-t/--tracker` to narrow to
one or more specific trackers (repeat `-t` for multiple):

```bash
# Search only Chromium issues
buganize -t chromium search "status:open"

# Search only Fuchsia issues
buganize -t fuchsia search "status:open"

# Search across Chromium and Fuchsia
buganize -t chromium -t fuchsia search "status:open"

# Search ANGLE and Skia issues
buganize -t angle -t skia search "status:open"
```

To list all available trackers and their IDs:

```bash
buganize trackers
```

### Issue

```bash
buganize issue 486077869
```

### Issues (batch)

```bash
buganize issues 40060244 485912774 486077869
```

### Comments

```bash
buganize comments 486077869
```

### Extra fields

By default, the table output only shows ID, Status, Priority, and Title. You can show additional columns with
`-f/--fields` (repeatable) or `-F/--all-fields`. These are global options that work with any subcommand:

```bash
# Show specific extra fields (repeat -f for each)
buganize -f owner -f os -f milestone search "status:open"

# Show all available fields
buganize -F search "status:open"

# Works with issue and issues too
buganize -f cve -f tags -f labels issue 486077869
buganize -F issue 486077869
```

Available extra field names: `owner`, `reporter`, `verifier`, `type`, `component`, `tags`, `ancestor_tags`, `labels`,
`os`, `milestone`, `ccs`, `hotlists`, `severity`, `collaborators`, `found_in`, `in_prod`, `blocking`, `duplicates`,
`cve`, `cwe`, `build`, `introduced_in`, `merge`, `merge_request`, `release_block`, `notice`, `flaky_test`, `est_days`,
`next_action`, `vrp_reward`, `irm_link`, `sec_release`, `fixed_by`, `created`, `modified`, `verified`, `comments`,
`stars`, `last_modifier`, `24h_views`, `7d_views`, `30d_views`.

### Export

All commands support `-e/--export` (repeatable) for exporting to CSV or JSON files. Exported files are named with a
timestamp (e.g. `buganize-20260223_012345.csv`):

```bash
buganize -e csv search "status:open" -n 50
buganize -e json issue 486077869

# Multiple formats in one command
buganize -e csv -e json search "status:open"
```

### Debug logging

Use `--debug` to see HTTP request/response details:

```bash
buganize --debug search "status:open"
```

### Timeout

Use `--timeout` to set the HTTP request timeout in seconds (default: 30):

```bash
buganize --timeout 60 search "status:open"
```

> [!Tip]
> British English spelling `buganise` will also work.

## GUI Usage

If you're feeling a bit elegant and lazy, you can use the GTK4-based GUI, on the condition that you have the following dependencies installed:

1. **Python 3.11+**
2. **GTK 4** (`Gtk-4.0` typelib): `gtk4` on Arch / Fedora, `libgtk-4-1` on Debian / Ubuntu.
3. **libadwaita 1** (`Adw-1` typelib): `libadwaita` on Arch / Fedora, `libadwaita-1-0` on Debian / Ubuntu.
4. **gdk-pixbuf 2** with SVG loader: usually pulled in as a GTK 4 dependency; on some distros the SVG loader is a separate package (`librsvg` / `gdk-pixbuf2-modules`).
5. **gobject-introspection**: needed for PyGObject to resolve the typelibs above.
6. **PyGObject** (the `gi` Python module): `python-gobject` on Arch, `python3-gi` on Debian / Ubuntu, `python3-gobject` on Fedora. Building from PyPI (`pip install PyGObject`) is possible but requires the GTK / GObject development headers.

Once the system bits are in place, launch the GUI with:

```bash
python -m buganize.gui
```

To register the app in your application menu (writes `~/.local/share/applications/dev.rly0nheart.buganize.desktop` and the icon), run once:

```bash
python -m buganize.gui --install-desktop
```

### NixOS Users
NixOS users (kind of) have it easy! If you're one, you know what shell.nix does and you can utilise its power with the [cli.sh](/cli.sh) and [gui.sh](/gui.sh) scripts. Just run whichever you like and enjoy.