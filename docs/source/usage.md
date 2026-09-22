# Usage

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
        result = await client.comments(486077869)

        for comment in result.comments:
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

### Export results

Every issue and comment writes itself out, and so does the list a read hands back:

```python
async def export():
    async with Buganize() as client:
        issues = await client.issues([40060244, 485912774, 486077869])

        issues.to_csv("issues.csv")  # one row per issue
        issues.to_json("issues.json")  # one array
        issues[0].to_json("issue.json")  # one object
        issues[0].to_dict()  # the fields as a plain dict

        result = await client.search("status:open", page_size=25)
        result.issues.to_csv("open.csv")
```

Missing parent directories are made, and each call returns the path it wrote.
Enums are written as their names (e.g. `FIXED`, `P1`) and timestamps in ISO form.

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

### Export

All commands support `-e/--export` (repeatable) for exporting to CSV or JSON files. Every field the tracker sent is
written, not a chosen few. Exported files are named with a timestamp (e.g. `buganize-20260223_012345.csv`):

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
