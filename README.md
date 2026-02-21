# Buganise

Python client for the Chromium Issue Tracker.

## Table of Contents

- [Installation](#installation)
- [Usage as a library](#usage-as-a-library)
    - [Search issues](#search-issues)
    - [Get a single issue](#get-a-single-issue)
    - [Batch get issues](#batch-get-issues)
    - [Get comments](#get-comments)
    - [Get full updates](#get-full-updates)
- [CLI usage](#cli-usage)
    - [Search](#search)
    - [Issue](#issue)
    - [Issues (batch)](#issues-batch)
    - [Comments](#comments)
    - [Extra fields](#extra-fields)
    - [Export](#export)
    - [Debug logging](#debug-logging)
    - [Timeout](#timeout)
- [How it works](#how-it-works)
- [Limitations](#limitations)

## Installation

```shell
pip install buganise
```

## Usage as a library

### Search issues

```python
from buganise import Buganise

async with Buganise() as client:
    result = await client.search("status:open component:Blink", page_size=10)

print(f"{result.total_count} total matches")
for issue in result.issues:
    print(f"#{issue.id} [{issue.status.name}] {issue.title}")

if result.has_more:
    next_page = await client.next_page(result)
```

### Get a single issue

```python
async with Buganise() as client:
    issue = await client.issue(40060244)

print(issue.title)
print(issue.url)  # https://issues.chromium.org/issues/40060244
print(issue.status.name)  # e.g. "FIXED"
print(issue.priority.name)  # e.g. "P2"
print(issue.os)  # e.g. ["Linux", "Mac", "Windows"]
print(issue.cve)  # e.g. ["CVE-2024-1234"]
```

### Batch get issues

```python
async with Buganise() as client:
    issues = await client.issues([40060244, 485912774, 486077869])

for issue in issues:
    print(f"#{issue.id} - {issue.title}")
```

### Get comments

```python
async with Buganise() as client:
    comments = await client.comments(486077869)

for comment in comments:
    print(f"#{comment.comment_number} by {comment.author}")
    print(comment.body)
```

### Get full updates

Updates include both comments and field changes (status changes, priority changes, etc.):

```python
async with Buganise() as client:
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

Run with `python -m buganise <command>` or just `buganise <command>`.

### Search

```bash
# Search for open issues
buganise search "status:open"

# Combined filters
buganise search "status:open component:Blink"

# Results per page (choices: 25, 50, 100, 250)
buganise search "type:bug" -n 100

# Fetch a total of 200 results, paginating as needed
buganise search "status:open" -l 200
```

### Issue

```bash
buganise issue 486077869
```

### Issues (batch)

```bash
buganise issues 40060244 485912774 486077869
```

### Comments

```bash
buganise comments 486077869
```

### Extra fields

By default, the table output only shows ID, Status, Priority, and Title. You can show additional columns:

```bash
# Show specific extra fields
buganise search "status:open" -f owner os milestone

# Show all available fields
buganise search "status:open" -F

# Works with issue and issues too
buganise issue 486077869 --fields cve tags labels
buganise issue 486077869 --all-fields
```

Available extra field names: `owner`, `reporter`, `verifier`, `type`, `component`, `tags`, `ancestor_tags`, `labels`,
`os`, `milestone`, `ccs`, `hotlists`, `blocking`, `cve`, `cwe`, `build`, `introduced_in`, `merge`, `merge_request`,
`release_block`, `notice`, `flaky_test`, `est_days`, `next_action`, `vrp_reward`, `irm_link`, `sec_release`, `fixed_by`,
`created`, `modified`, `verified`, `comments`, `stars`, `last_modifier`.

### Export

All commands support `-e/--export` for exporting to CSV, JSON, or HTML. You can specify multiple formats at once:

```bash
buganise -e csv search "status:open" -n 50
buganise -e json issue 486077869
buganise -e html comments 486077869

# Multiple formats in one command
buganise -e csv json search "status:open"
```

### Debug logging

Use `-d/--debug` to see HTTP request/response details:

```bash
buganise --debug search "status:open"
```

### Timeout

Use `-t/--timeout` to set the HTTP request timeout in seconds (default: 30):

```bash
buganise -t 60 search "status:open"
```

> [!Tip]
> American English spelling `buganize`, will also work.

## How it works

The Chromium issue tracker at `issues.chromium.org` doesn't have a documented public API. But the web frontend talks to
a set of POST endpoints under `https://issues.chromium.org/action/` using JSON arrays as request/response bodies. This
library speaks that same protocol.

Every response from the API starts with `)]}'\n` (an anti-XSSI prefix) followed by a JSON array. Issue data comes back
as 48-element positional arrays, no keys, just indexes. The parser maps those indexes to fields on the `Issue`
dataclass. Custom fields (things like OS, milestone, CVE, component tags) are embedded inside the issue array at a
specific offset and have their own internal structure.

No cookies or tokens are needed for reading public issues. The only headers required are `Content-Type`, `Origin`,
`Referer`, and a browser-like `User-Agent`.

## Limitations

- This uses an undocumented API. It could break if Google changes the response format.
- Only works with public issues. Private/restricted issues need authentication cookies that this client doesn't handle.
- The parser is entirely index-based. If the API adds or removes fields from the arrays, the parsing will silently
  return wrong data.
- Pagination for updates (comments) is not fully wired up, currently fetches the first page only.
- The batch endpoint may not return issues in the same order as the input IDs.
