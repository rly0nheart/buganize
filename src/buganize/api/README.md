# Google Issue Tracker (Buganizer)  API Reference

Reverse-engineered documentation of the JSON API at
`issuetracker.google.com` (to the best of my knowledge). Everything here was discovered by intercepting
browser traffic with mitmproxy. There is no official documentation.

---

## Table of Contents

1. [Overview](#overview)
2. [Base URL & Headers](#base-url--headers)
3. [Anti-XSSI Prefix](#anti-xssi-prefix)
4. [Known Trackers](#known-trackers)
5. [Endpoints](#endpoints)
    - [Search Issues](#search-issues)
    - [Get Single Issue](#get-single-issue)
    - [Batch Get Issues](#batch-get-issues)
    - [List Issue Updates](#list-issue-updates)
6. [Response Shapes](#response-shapes)
    - [Search Response](#search-response)
    - [Issue Detail Response](#issue-detail-response)
    - [Batch Response](#batch-response)
    - [Updates Response](#updates-response)
7. [Issue Array (48 elements)](#issue-array-48-elements)
    - [Top-Level Index Map](#top-level-index-map)
    - [Details Array (32 elements)](#details-array-32-elements)
    - [Unmapped / Unknown Fields](#unmapped--unknown-fields)
8. [Custom Fields](#custom-fields)
    - [Custom Field Entry Format](#custom-field-entry-format)
    - [Known Chromium Field IDs](#known-chromium-field-ids)
9. [User Arrays](#user-arrays)
10. [Timestamps](#timestamps)
11. [Enums](#enums)
12. [Update Entry (10 elements)](#update-entry-10-elements)
13. [Comment Array (18 elements)](#comment-array-18-elements)
14. [Field Changes](#field-changes)
15. [Pagination](#pagination)
16. [Component Hierarchy](#component-hierarchy)
17. [Debugging Tips](#debugging-tips)

---

## Overview

`issuetracker.google.com` and `issues.chromium.org` share the **exact same
Buganizer backend** — identical endpoints, response format, and `b.`-prefixed
type strings. The only difference: `issues.chromium.org` hard-codes
tracker 157 (Chromium), while `issuetracker.google.com` can query
**all public trackers** when no tracker ID is specified.

The API uses **positional JSON arrays** rather than keyed objects. Every
response is a deeply nested list of lists. Fields are identified by their
**index position**, not by name.

---

## Base URL & Headers

```
Base:  https://issuetracker.google.com/action
```

All requests are **POST** with the following headers:

| Header       | Value                                     |
|--------------|-------------------------------------------|
| Content-Type | `application/json`                        |
| Origin       | `https://issuetracker.google.com`         |
| Referer      | `https://issuetracker.google.com/`        |
| User-Agent   | Any Googlebot-like or standard browser UA |

No authentication is required for public issues.

---

## Anti-XSSI Prefix

**Every** response body is prefixed with:

```
)]}'
```

followed by a newline (`\n`). This must be stripped before parsing JSON.
The prefix is a standard Google anti-XSSI (cross-site script inclusion)
protection.

```python
# Strip before json.loads()
clean = raw_text.removeprefix(")]}'\\n")
data = json.loads(clean)
```

---

## Known Trackers

| Tracker ID | Name                                         | Root Component ID |
|------------|----------------------------------------------|-------------------|
| `157`      | Chromium                                     | 1362134           |
| `183`      | Fuchsia                                      | 1360843           |
| `None`     | All public trackers (Android, YouTube, etc.) | —                 |

All public trackers sit under the root component `166797` ("Public Trackers").

---

## Endpoints

### Search Issues

```
POST /action/issues/list
```

**Request body:**

```json
[
  null,
  null,
  null,
  null,
  null,
  TRACKER_FILTER,
  QUERY_PAYLOAD
]
```

| Position | Field          | Type             | Description                             |
|----------|----------------|------------------|-----------------------------------------|
| `[5]`    | tracker_filter | `[str] \| null`  | `["157"]` for Chromium, `null` for all  |
| `[6][0]` | query          | `str`            | Search query (e.g. `"status:open"`)     |
| `[6][1]` | unknown        | `null`           | Always `null`                           |
| `[6][2]` | page_size      | `int`            | Results per page: 25, 50, 100, or 250   |
| `[6][3]` | page_token     | `str \| omitted` | Pagination token from previous response |

**Example — search all trackers:**

```json
[
  null,
  null,
  null,
  null,
  null,
  null,
  [
    "status:open",
    null,
    50
  ]
]
```

**Example — search Chromium only, page 2:**

```json
[
  null,
  null,
  null,
  null,
  null,
  [
    "157"
  ],
  [
    "status:open",
    null,
    50,
    "SOME_PAGE_TOKEN"
  ]
]
```

---

### Get Single Issue

```
POST /action/issues/{issue_id}/getIssue
POST /action/issues/{issue_id}/getIssue?currentTrackerId={tracker_id}
```

**Request body:**

```json
[
  ISSUE_ID,
  1,
  1
]
```

The two `1` values appear to be flags (possibly "include details" and
"include custom fields"). Their exact meaning is unknown.

---

### Batch Get Issues

```
POST /action/issues/batch
```

**Request body:**

```json
[
  "b.BatchGetIssuesRequest",
  null,
  null,
  [
    ISSUE_IDS,
    2,
    2
  ]
]
```

| Position | Field     | Type        | Description                  |
|----------|-----------|-------------|------------------------------|
| `[3][0]` | issue_ids | `list[int]` | List of issue IDs to fetch   |
| `[3][1]` | flag_1    | `int`       | Always `2` (purpose unknown) |
| `[3][2]` | flag_2    | `int`       | Always `2` (purpose unknown) |

---

### List Issue Updates

```
POST /action/issues/{issue_id}/updates
POST /action/issues/{issue_id}/updates?currentTrackerId={tracker_id}
```

**Request body:**

```json
[
  ISSUE_ID
]
```

Returns all updates (comments + field changes) in **reverse chronological
order** (newest first).

---

## Response Shapes

### Search Response

**Type string:** `b.IssueSearchResponse`

```
data[0]    = ["b.IssueSearchResponse", ...]
data[0][6] = [ISSUES_ARRAY, PAGE_TOKEN, TOTAL_COUNT]
```

| Path        | Type          | Description                              |
|-------------|---------------|------------------------------------------|
| `[0][6][0]` | `list[list]`  | Array of 48-element issue entries        |
| `[0][6][1]` | `str \| null` | Next page token (`null` if last page)    |
| `[0][6][2]` | `int`         | Total matching issue count (approximate) |

### Issue Detail Response

**Type string:** `b.IssueFetchResponse`

```
data[0]    = ["b.IssueFetchResponse", PAYLOAD]
data[0][1] = 23-element payload array
```

The 48-element issue entry is at the **last element** of the payload that
contains an integer at index `[1]` (the issue ID). Typically this is
`data[0][1][22]`, but the parser scans backwards to be safe.

### Batch Response

**Type string:** `b.BatchGetIssuesResponse`

```
data[0]    = ["b.BatchGetIssuesResponse", null, [[issue1, issue2, ...]]]
data[0][2][0] = array of 48-element issue entries
```

**Note:** Batch responses may include `TOP[43]` (issue body/description),
which is **not** populated in search responses.

### Updates Response

**Type string:** `b.ListIssueUpdatesResponse`

```
data[0]    = ["b.ListIssueUpdatesResponse", [UPDATES, PAGE_TOKEN, TOTAL_COUNT]]
data[0][1][0] = array of 10-element update entries
data[0][1][1] = next page token
data[0][1][2] = total update count
```

---

## Issue Array (48 elements)

Every endpoint produces issues as 48-element positional arrays. The same
format is used across search, get, and batch responses.

### Top-Level Index Map

| Index  | Field             | Type                 | Notes                                                                                              |
|--------|-------------------|----------------------|----------------------------------------------------------------------------------------------------|
| `[0]`  | (unknown)         | —                    | —                                                                                                  |
| `[1]`  | issue_id          | `int`                | Unique issue ID                                                                                    |
| `[2]`  | details           | `list` (32 elements) | See [Details Array](#details-array-32-elements)                                                    |
| `[3]`  | (unknown)         | —                    | —                                                                                                  |
| `[4]`  | created_at        | `[secs, nanos]`      | Created timestamp                                                                                  |
| `[5]`  | modified_at       | `[secs, nanos]`      | Last modified timestamp                                                                            |
| `[6]`  | verified_at       | `[secs, nanos]`      | Verification timestamp (may be `null`)                                                             |
| `[7]`  | (unknown)         | —                    | —                                                                                                  |
| `[8]`  | (unknown)         | —                    | —                                                                                                  |
| `[9]`  | star_count        | `int`                | Number of stars/watchers                                                                           |
| `[10]` | (unknown)         | `int`                | Always `3` — purpose unknown                                                                       |
| `[11]` | comment_count     | `int`                | Total comment count                                                                                |
| `[12]` | (unknown)         | —                    | —                                                                                                  |
| `[13]` | owner             | user array           | Currently assigned owner                                                                           |
| `[14]` | custom_field_defs | `list`               | Custom field definitions (schema, not values — values are in `details[14]`)                        |
| `[41]` | tracker_id        | `int \| null`        | Tracker ID (e.g. `157` for Chromium)                                                               |
| `[43]` | body              | `str \| null`        | Issue description body — **only in batch responses**                                               |
| `[46]` | views             | `list \| null`       | View counts as `[1d, 7d, total]` (all three values are often identical). Empty `[]` means 0 views. |
| `[47]` | last_modifier     | user array           | Last person to modify the issue                                                                    |

> Indices `[15]`–`[40]`, `[42]`, `[44]`–`[45]` are either `null` or
> contain data whose meaning has not been identified.

### Details Array (32 elements)

The details array lives at `TOP[2]` and contains most of the issue's
metadata.

| Index  | Field               | Type                | Notes                                                                                           |
|--------|---------------------|---------------------|-------------------------------------------------------------------------------------------------|
| `[0]`  | component_id        | `int`               | Primary component ID                                                                            |
| `[1]`  | issue_type          | `int`               | Maps to `IssueType` enum (1=BUG, 2=FEATURE_REQUEST, etc.)                                       |
| `[2]`  | status              | `int`               | Maps to `Status` enum (1=NEW, 2=ASSIGNED, etc.)                                                 |
| `[3]`  | priority            | `int`               | **1-indexed**: P0=1, P1=2, P2=3, P3=4, P4=5                                                     |
| `[4]`  | (unknown)           | `int \| null`       | Sometimes matches priority, sometimes differs (e.g. on security issues). Possibly **severity**. |
| `[5]`  | title               | `str`               | Issue title/summary                                                                             |
| `[6]`  | reporter            | user array          | Person who filed the issue                                                                      |
| `[7]`  | verifier            | user array          | Person who verified the fix                                                                     |
| `[8]`  | (unknown)           | —                   | —                                                                                               |
| `[9]`  | ccs                 | `list[user_array]`  | CC'd users                                                                                      |
| `[10]` | (unknown)           | —                   | —                                                                                               |
| `[11]` | (unknown)           | —                   | —                                                                                               |
| `[12]` | (unknown)           | —                   | —                                                                                               |
| `[13]` | hotlist_ids         | `list[int]`         | Hotlist IDs the issue belongs to                                                                |
| `[14]` | custom_field_values | `list[field_entry]` | Custom field value entries (see [Custom Fields](#custom-fields))                                |
| `[19]` | (unknown)           | `bool \| null`      | Boolean flag — `True` or `None`. Possibly `is_public`.                                          |
| `[21]` | blocking_issue_ids  | `list[int]`         | IDs of blocking/related issues                                                                  |

---

## Custom Fields

Custom fields are Chromium-tracker-specific configurable fields stored at
`details[14]`. Each tracker can define its own set of custom fields with
different IDs.

### Custom Field Entry Format

Each entry in `details[14]` is an array:

```
[field_id, null, null, null, numeric_val, label_values, null, enum_values, null, display_string, ...]
```

| Index | Field          | Type                   | Description                                 |
|-------|----------------|------------------------|---------------------------------------------|
| `[0]` | field_id       | `int`                  | Numeric custom field ID                     |
| `[4]` | numeric_value  | `int \| float \| null` | Value for number-type fields (e.g. CWE ID)  |
| `[5]` | label_values   | `[[str, ...]]`         | Multi-value labels (nested list of strings) |
| `[7]` | enum_values    | `[[str, ...]]`         | Enum-like values (nested list of strings)   |
| `[9]` | display_string | `str \| null`          | Human-readable display string (fallback)    |

**Parsing priority:** Check `[4]` (numeric) first, then `[5]` (labels),
then `[7]` (enums), then fall back to `[9]` (display string).

### Known Chromium Field IDs

These are the 24 well-known custom fields for tracker 157 (Chromium).
Other trackers will have different field IDs.

| Field ID | Name                    | Type        |
|----------|-------------------------|-------------|
| 1222907  | component_tags          | `list[str]` |
| 1223031  | chromium_labels         | `list[str]` |
| 1223032  | design_doc              | `str`       |
| 1223033  | build_number            | `str`       |
| 1223034  | respin                  | `str`       |
| 1223081  | flaky_test              | `str`       |
| 1223083  | notice                  | `str`       |
| 1223084  | os                      | `list[str]` |
| 1223085  | milestone               | `list[str]` |
| 1223086  | release_block           | `list[str]` |
| 1223087  | merge                   | `list[str]` |
| 1223088  | security_release        | `list[str]` |
| 1223131  | design_summary          | `str`       |
| 1223134  | merge_request           | `list[str]` |
| 1223135  | vrp_reward              | `float`     |
| 1223136  | cve                     | `list[str]` |
| 1225154  | next_action             | `str`       |
| 1225337  | estimated_days          | `float`     |
| 1225362  | backlog_rank            | `float`     |
| 1253656  | component_ancestor_tags | `list[str]` |
| 1300460  | irm_link                | `str`       |
| 1358989  | fixed_by_code_changes   | `list[str]` |
| 1410892  | cwe_id                  | `float`     |
| 1544844  | introduced_in           | `str`       |

Unrecognized field IDs are stored as `field_{id}` in the catch-all
`custom_fields` dict.

---

## User Arrays

User/person fields (reporter, owner, verifier, CCs, etc.) are arrays like:

```json
[
  null,
  "user@example.com",
  1,
  [
    ...
  ]
]
```

The email address is the **first string element** in the array. The numeric
value after it may indicate user type or role. The trailing list may contain
additional profile data.

---

## Timestamps

Timestamps are `[seconds, nanoseconds]` arrays:

```json
[
  1657579144,
  285000000
]
```

- `[0]` = Unix epoch seconds
- `[1]` = Nanosecond component (optional, may be absent)

Convert to `datetime`:

```python
datetime.fromtimestamp(seconds + nanos / 1e9, tz=timezone.utc)
```

---

## Enums

### Status

| Value | Name              | Open? |
|-------|-------------------|-------|
| 1     | NEW               | Yes   |
| 2     | ASSIGNED          | Yes   |
| 3     | ACCEPTED          | Yes   |
| 4     | FIXED             | No    |
| 5     | VERIFIED          | No    |
| 6     | NOT_REPRODUCIBLE  | No    |
| 7     | INTENDED_BEHAVIOR | No    |
| 8     | OBSOLETE          | No    |
| 9     | INFEASIBLE        | No    |
| 10    | DUPLICATE         | No    |

### Priority

**The API uses 1-indexed priority.** Subtract 1 to get standard P0-P4.

| API Value | Display |
|-----------|---------|
| 1         | P0      |
| 2         | P1      |
| 3         | P2      |
| 4         | P3      |
| 5         | P4      |

### Issue Type

| Value | Name             |
|-------|------------------|
| 1     | BUG              |
| 2     | FEATURE_REQUEST  |
| 3     | CUSTOMER_ISSUE   |
| 4     | INTERNAL_CLEANUP |
| 5     | PROCESS          |
| 6     | VULNERABILITY    |

---

## Update Entry (10 elements)

Updates are returned from the `/updates` endpoint in **reverse chronological
order** (newest first). Each update is a 10-element array:

| Index | Field           | Type             | Notes                                                    |
|-------|-----------------|------------------|----------------------------------------------------------|
| `[0]` | author          | user array       | Who made this update                                     |
| `[1]` | timestamp       | `[secs, nanos]`  | When the update happened                                 |
| `[2]` | comment         | 18-element array | Comment body (see below), or `null` if field-change-only |
| `[3]` | sequence_number | `int`            | Ordering number for this update                          |
| `[4]` | (unknown)       | —                | —                                                        |
| `[5]` | field_changes   | `list`           | Array of field change entries                            |
| `[6]` | comment_number  | `int`            | Comment number (descending in response)                  |
| `[7]` | (unknown)       | —                | —                                                        |
| `[8]` | (unknown)       | —                | —                                                        |
| `[9]` | issue_id        | `int`            | The issue this update belongs to                         |

---

## Comment Array (18 elements)

When an update includes a comment, `update[2]` is an 18-element array:

| Index | Field           | Type            | Notes                                            |
|-------|-----------------|-----------------|--------------------------------------------------|
| `[0]` | body            | `str`           | Comment text                                     |
| `[1]` | (unknown)       | —               | —                                                |
| `[2]` | author          | user array      | Comment author                                   |
| `[3]` | timestamp       | `[secs, nanos]` | When the comment was posted                      |
| `[4]` | (unknown)       | —               | —                                                |
| `[5]` | issue_id        | `int`           | Parent issue ID                                  |
| `[6]` | sequence_number | `int`           | **0-indexed** comment number (add 1 for display) |

---

## Field Changes

Field change entries appear in `update[5]` and look like:

```json
[
  "field_name",
  null,
  OLD_VALUE_WRAPPER,
  NEW_VALUE_WRAPPER
]
```

| Index | Field      | Description                                               |
|-------|------------|-----------------------------------------------------------|
| `[0]` | field_name | Name of the changed field (e.g. `"status"`, `"priority"`) |
| `[2]` | old_value  | Previous value (wrapper format varies by field)           |
| `[3]` | new_value  | New value (wrapper format varies by field)                |

The old/new value wrappers have inconsistent formats depending on the field
type — they may be nested arrays, strings, or integers. Currently we only
extract the field name.

---

## Pagination

Search and update responses include pagination:

| Field         | Description                                        |
|---------------|----------------------------------------------------|
| `page_token`  | Opaque string for fetching the next page           |
| `total_count` | Approximate total count (may change between pages) |

To paginate, pass the `page_token` as `query_payload[3]` in the next search
request. When `page_token` is `null`, you're on the last page.

---

## Component Hierarchy

Components form a tree. The root for all public trackers is component
`166797`.

```
Public Trackers (166797)
  ├── Chromium (1362134)
  │     └── Chromium root (1363614)
  │           └── Internals (1456292)
  │                 └── Crypto (1768937)
  └── Fuchsia (1360843)
        └── Hardware Platform (1620976)
              └── Zircon Kernel (1478131)
                    └── VM (1477815)
```

Component details are available via `GET /action/components/{id}`:

- `data[0][28][1]` = component ID
- `data[0][28][2]` = parent component ID
- `data[0][28][3]` = component name
- `data[0][28][6][0]` = breadcrumb IDs
- `data[0][28][6][1]` = breadcrumb names
- `data[0][28][19]` = tracker ID

---

## Debugging Tips

1. **Always strip the `)]}'` prefix** before parsing. If you get a JSON
   parse error, check that stripping is working correctly.

2. **Priority is 1-indexed in the API** but our `Priority` enum is
   0-indexed. The parser subtracts 1 when converting. If priorities look
   off by one, check this conversion.

3. **Search vs batch vs detail responses wrap the 48-element issue array
   differently.** The issue array itself is always the same format, but
   the path to reach it varies:
    - Search: `data[0][6][0][i]`
    - Detail: `data[0][1][22]` (scan backwards for the first list with an int at `[1]`)
    - Batch: `data[0][2][0][i]`

4. **Custom field IDs are tracker-specific.** The 24 known IDs in
   `CUSTOM_FIELD_IDS` are for Chromium (tracker 157). Other trackers
   will have different IDs for different fields. Unknown fields end up
   in `issue.custom_fields` as `field_{id}`.

5. **`details[4]` is NOT the same as priority (`details[3]`).** On most
   issues they match, but on security issues they diverge. This field is
   suspected to be **severity** but this is unconfirmed.

6. **`details[19]` is a boolean flag** (`True` or `None`). Its exact
   meaning is unknown — possibly `is_public`.

7. **`TOP[43]` (issue body)** is only populated in **batch responses**,
   not in search results. If you need the description, use batch fetch.

8. **`TOP[46]` (view counts)** contains a list like `[1, 1, 1]` representing
   `[1d_views, 7d_views, total_views]`. All three values are often
   identical. An empty `[]` means 0 views. Not currently parsed.

9. **The total count in search results is approximate.** It may fluctuate
   between pages and is prefixed with `~` in the CLI for this reason.

10. **Updates come newest-first.** Reverse the list if you need chronological
    order. The `IssueUpdatesResult.comments` property does this
    automatically.
