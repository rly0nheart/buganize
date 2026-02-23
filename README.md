# Buganize

Python client for the Google Issue Tracker.

## Table of Contents

1. [Installation](#installation)
2. [Usage as a library](#usage-as-a-library)
    - [Search issues](#search-issues)
    - [Get a single issue](#get-a-single-issue)
    - [Batch get issues](#batch-get-issues)
    - [Get comments](#get-comments)
    - [Get full updates](#get-full-updates)
3. [CLI usage](#cli-usage)
    - [Search](#search)
    - [Tracker selection](#tracker-selection)
    - [Issue](#issue)
    - [Issues (batch)](#issues-batch)
    - [Comments](#comments)
    - [Extra fields](#extra-fields)
    - [Export](#export)
    - [Debug logging](#debug-logging)
    - [Timeout](#timeout)

## Installation

```shell
pip install buganize
```

or

```shell
pip install buganise
```

## Usage as a library

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
    async with Buganize(tracker_id="157") as client:
        result = await client.search("status:open component:Blink")
```

### Get a single issue

```python
async def get_issue():
    async with Buganize() as client:
        issue = await client.issue(40060244)

        print(issue.title)
        print(issue.url)  # https://issuetracker.google.com/issues/40060244
        print(issue.status.name)  # e.g. "FIXED"
        print(issue.priority.name)  # e.g. "P2"
        print(issue.os)  # e.g. ["Linux", "Mac", "Windows"]
        print(issue.cve)  # e.g. ["CVE-2024-1234"]
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

By default, buganize searches across all public trackers on issuetracker.google.com. Use `-t/--tracker` to narrow to a
specific tracker:

```bash
# Search only Chromium issues
buganize -t chromium search "status:open"

# Search only Fuchsia issues
buganize -t fuchsia search "status:open"

# Use a numeric tracker ID directly
buganize -t 157 search "status:open"
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

By default, the table output only shows ID, Status, Priority, and Title. You can show additional columns:

```bash
# Show specific extra fields
buganize search "status:open" -f owner os milestone

# Show all available fields
buganize search "status:open" -F

# Works with issue and issues too
buganize issue 486077869 --fields cve tags labels
buganize issue 486077869 --all-fields
```

Available extra field names: `owner`, `reporter`, `verifier`, `type`, `component`, `tags`, `ancestor_tags`, `labels`,
`os`, `milestone`, `ccs`, `hotlists`, `blocking`, `cve`, `cwe`, `build`, `introduced_in`, `merge`, `merge_request`,
`release_block`, `notice`, `flaky_test`, `est_days`, `next_action`, `vrp_reward`, `irm_link`, `sec_release`, `fixed_by`,
`created`, `modified`, `verified`, `comments`, `stars`, `last_modifier`.

### Export

All commands support `-e/--export` for exporting to CSV or JSON files. Exported files are named with a timestamp (e.g.
`buganize-20260223_012345.csv`):

```bash
buganize -e csv search "status:open" -n 50
buganize -e json issue 486077869

# Multiple formats in one command
buganize -e csv json search "status:open"
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


See [API Reference](https://github.com/rly0nheart/buganize/tree/master/src/buganize/api#readme) for details about
limitations, and how the API works
