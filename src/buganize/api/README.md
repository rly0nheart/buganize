# Google Issue Tracker (Buganizer)  API Reference

Reverse-engineered documentation of the JSON API at
`issuetracker.google.com` (to the best of my knowledge). Everything here was discovered by intercepting
browser traffic with BurpSuite and mitmproxy. There is no official documentation.

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
    - [Get Component](#get-component)
    - [Batch Get Components](#batch-get-components)
    - [Get Tracker](#get-tracker)
    - [Get Hotlist](#get-hotlist)
    - [Batch Get Hotlists](#batch-get-hotlists)
    - [List Issue Relationships](#list-issue-relationships)
6. [Response Shapes](#response-shapes)
    - [Search Response](#search-response)
    - [Issue Detail Response](#issue-detail-response)
    - [Batch Response](#batch-response)
    - [Updates Response](#updates-response)
7. [Issue Array (48 elements)](#issue-array-48-elements)
    - [Top-Level Index Map](#top-level-index-map)
    - [Details Array (32 elements)](#details-array-32-elements)
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
17. [Limitations](#limitations)
18. [Debugging Tips](#debugging-tips)

---

## Overview

The Google Issue Tracker at `issuetracker.google.com` has no documented public API. The web frontend talks to a set of
POST endpoints under `https://issuetracker.google.com/action/` using JSON arrays as request/response bodies. This
library speaks that same protocol. The same backend powers `issues.chromium.org` (hard-coded to tracker 157) and other
Google project trackers.

Every response starts with `)]}'\n` (an anti-XSSI prefix) followed by a JSON array. Issue data comes back as
48-element positional arrays, no keys, just indexes. The parser maps those indexes to fields on the `Issue` dataclass.
Custom fields (OS, milestone, CVE, component tags, etc.) are embedded inside the issue array at a specific offset and
have their own internal structure.

No cookies or tokens are needed for reading public issues. The only required headers are `Content-Type`, `Origin`,
`Referer`, and a browser-like `User-Agent`.

---

## Base URL & Headers

```
Base:  https://issuetracker.google.com/action
```

Issue endpoints use **POST** with JSON bodies. Resource endpoints (components,
trackers, hotlists) use **GET** with query parameters.

| Header       | Value                                     | POST | GET |
|--------------|-------------------------------------------|------|-----|
| Content-Type | `application/json`                        | Yes  | No  |
| Origin       | `https://issuetracker.google.com`         | Yes  | Yes |
| Referer      | `https://issuetracker.google.com/`        | Yes  | Yes |
| User-Agent   | Any Googlebot-like or standard browser UA | Yes  | Yes |

GET endpoints must **not** send `Content-Type: application/json` or they
return 400.

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

There are 14 public trackers with their own tracker IDs. All sit under the root
component `166797` ("Public Trackers"). Using `tracker_id=None` in searches
queries all public trackers, including ones without their own tracker ID
(Android, YouTube, Cloud, etc.).

Tracker IDs are not sequential. These were found by scanning IDs 1-3000.

| Tracker ID | Name         | Root Component | Public URL                               |
|------------|--------------|----------------|------------------------------------------|
| `1`        | Pigweed      | 1194524        | https://issues.pigweed.dev               |
| `27`       | Gerrit       | 1370273        | https://issues.gerritcodereview.com      |
| `53`       | Git          | 1320275        | https://git.issues.gerritcodereview.com  |
| `79`       | Skia         | 1363359        | https://issues.skia.org                  |
| `105`      | WebRTC       | 1363538        | https://issues.webrtc.org                |
| `131`      | libyuv       | 1363539        | https://libyuv.issues.chromium.org       |
| `157`      | Chromium     | 1363614        | https://issues.chromium.org              |
| `183`      | Fuchsia      | 1360843        | https://issues.fuchsia.dev               |
| `235`      | ANGLE        | 853171         | https://issues.angleproject.org          |
| `261`      | AOMedia      | 1597128        | https://aomedia.issues.chromium.org      |
| `287`      | WebM         | 1615215        | https://issues.webmproject.org           |
| `339`      | GN           | 1636803        | https://gn.issues.chromium.org           |
| `365`      | Project Zero | 1638259        | https://project-zero.issues.chromium.org |
| `391`      | OSS Fuzz     | 1638179        | https://issues.oss-fuzz.com              |

There is no "list all trackers" endpoint. You must know the tracker ID in advance.

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
| `[5]`    | tracker_filter | `[str] \| null`  | `["157"]` for Chromium, `["157", "183"]` for multiple, `null` for all  |
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

> **Note:** This endpoint does **not** populate `TOP[43]` (issue
> body/description) — it is always `null`. Use the batch endpoint
> instead if you need the description.

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

### Get Component

```
GET /action/components/{id}
```

No request body. Returns a single `b.Component` response.

The component data is inside a nested array at `data[0][28]` (22 elements):

| Path     | Field               | Type        | Notes                                                 |
|----------|---------------------|-------------|-------------------------------------------------------|
| `[1]`    | component_id        | `int`       | Same as the ID in the URL                             |
| `[2]`    | parent_component_id | `int`       | Parent component in the tree                          |
| `[3]`    | component_name      | `str`       | Human-readable name                                   |
| `[6][0]` | breadcrumb_ids      | `list[int]` | Component IDs from root to this component             |
| `[6][1]` | breadcrumb_names    | `list[str]` | Component names from root to this component           |
| `[6][2]` | custom_field_defs   | `list`      | Custom field definitions for this component's tracker |
| `[19]`   | tracker_id          | `int`       | Tracker this component belongs to                     |

---

### Batch Get Components

```
GET /action/components?id=X&id=Y&id=Z
```

No request body. Pass component IDs as repeated `id` query parameters.

**Response type:** `b.ListComponentsResponse`

Each component in the response has the same inner structure at index `[28]`
as the single component endpoint.

---

### Get Tracker

```
GET /action/trackers/{id}
```

No request body. Returns a single `b.Tracker` response.

The tracker data is inside a nested array at `data[0][9]` (12 elements):

| Path   | Field             | Type        | Notes                                                      |
|--------|-------------------|-------------|------------------------------------------------------------|
| `[0]`  | tracker_id        | `int`       | Same as the ID in the URL                                  |
| `[1]`  | root_component_id | `int`       | Root component for this tracker                            |
| `[2]`  | name              | `str`       | Human-readable tracker name                                |
| `[5]`  | branding          | `list`      | `[logo_url, type_int, code_of_conduct_url]`                |
| `[7]`  | internal_url      | `str`       | Internal vanity URL (e.g. `https://g-issues.chromium.org`) |
| `[8]`  | public_url        | `str`       | Public vanity URL (e.g. `https://issues.chromium.org`)     |
| `[10]` | slug              | `str\|null` | URL slug (e.g. `"fuchsia"`) or `null`                      |

---

### Get Hotlist

```
GET /action/hotlists/{id}
```

No request body. Returns a single `b.Hotlist` response.

The hotlist data is at `data[0][18]` (10 elements):

| Path  | Field       | Type            | Notes                         |
|-------|-------------|-----------------|-------------------------------|
| `[0]` | hotlist_id  | `int`           | Same as the ID in the URL     |
| `[1]` | name        | `str`           | Human-readable hotlist name   |
| `[2]` | description | `str\|null`     | Hotlist description           |
| `[6]` | created_at  | `[secs, nanos]` | When the hotlist was created  |
| `[7]` | modified_at | `[secs, nanos]` | When the hotlist was modified |
| `[8]` | admins      | `list`          | Admin user arrays             |

---

### Batch Get Hotlists

```
GET /action/hotlists?id=X&id=Y
```

No request body. Pass hotlist IDs as repeated `id` query parameters.

**Response type:** `b.ListHotlistsResponse`

---

### List Issue Relationships

```
GET /action/issues/{id}/relationships?relationshipType=1
```

No request body.

**Response type:** `b.ListIssueRelationshipsResponse`

Returns an empty `[["b.ListIssueRelationshipsResponse"]]` when no
relationships exist. The `relationshipType=1` parameter filters for
blocking/blocked-by relationships.

Note that "blocking" issue IDs are available directly on the issue array at
`TOP[36]`, but "blocked by" data is only available through this endpoint.

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

| Index  | Field              | Type                 | Notes                                                                      |
|--------|--------------------|----------------------|----------------------------------------------------------------------------|
| `[0]`  | (unknown)          | —                    | —                                                                          |
| `[1]`  | issue_id           | `int`                | Unique issue ID                                                            |
| `[2]`  | details            | `list` (32 elements) | See [Details Array](#details-array-32-elements)                            |
| `[3]`  | (unknown)          | —                    | —                                                                          |
| `[4]`  | created_at         | `[secs, nanos]`      | Created timestamp                                                          |
| `[5]`  | modified_at        | `[secs, nanos]`      | Last modified timestamp                                                    |
| `[6]`  | verified_at        | `[secs, nanos]`      | Verification timestamp (may be `null`)                                     |
| `[7]`  | (unknown)          | —                    | —                                                                          |
| `[8]`  | (unknown)          | —                    | —                                                                          |
| `[9]`  | star_count         | `int \| null`        | Number of stars/votes. `null` means 0                                      |
| `[10]` | (unknown)          | `int`                | Always `3`                                                                 |
| `[11]` | comment_count      | `int`                | Total comment count                                                        |
| `[12]` | (unknown)          | `str`                | Base64-encoded string on every issue, possibly an etag or cursor           |
| `[13]` | owner              | user array           | Currently assigned owner                                                   |
| `[14]` | custom_field_defs  | `list`               | Custom field definitions (schema, not values; values are in `details[14]`) |
| `[33]` | custom_field_refs  | `list[list[int]]`    | Custom field IDs available for this issue's component                      |
| `[36]` | blocking_issue_ids | `list[int]`          | IDs of issues that this issue blocks                                       |
| `[37]` | relationship_graph | `list`               | Relationship data: `[[this_issue, [[blocked_issue]]]]`                     |
| `[40]` | links              | `list`               | URLs extracted from issue body: `[[[url], null, type_int]]`                |
| `[41]` | tracker_id         | `int \| null`        | Tracker ID (e.g. `157` for Chromium)                                       |
| `[43]` | body               | `list \| null`       | Issue description entry, **only in batch/detail responses** (see below)    |
| `[46]` | views              | `list \| null`       | View counts as `[24h, 7d, 30d]`. Empty `[]` means 0 views                  |
| `[47]` | last_modifier      | user array           | Last person to modify the issue (index may be 46 in some response shapes)  |

> Search response issues have 47 elements (some fields are absent compared
> to detail/batch responses). The `last_modifier` index may shift to `[46]`
> in search results.

#### Body Entry (`TOP[43]`)

The body/description is structured like a comment entry, not a plain string.
It is `null` in search responses and only populated in batch/detail responses.

| Index | Field     | Type            | Notes                                      |
|-------|-----------|-----------------|--------------------------------------------|
| `[0]` | text      | `str`           | Plain text description (may contain markdown) |
| `[1]` | (unknown) | `null`          | Always `null`                              |
| `[2]` | author    | user array      | Who wrote the description                  |
| `[3]` | timestamp | `[secs, nanos]` | When the description was written           |
| `[4]` | (unknown) | `list`          | Always `[]`                                |
| `[5]` | issue_id  | `int`           | Parent issue ID                            |
| `[6]` | sequence  | `int`           | Always `1`                                 |

The entry also contains an HTML-rendered version of the description deeper
in the array, with Google redirect wrappers on all links.

### Details Array (32 elements)

The details array lives at `TOP[2]` and contains most of the issue's
metadata.

| Index  | Field               | Type                | Notes                                                                                               |
|--------|---------------------|---------------------|-----------------------------------------------------------------------------------------------------|
| `[0]`  | component_id        | `int`               | Primary component ID (name requires a separate components call)                                     |
| `[1]`  | issue_type          | `int`               | Maps to `IssueType` enum (1=BUG, 2=FEATURE_REQUEST, etc.)                                           |
| `[2]`  | status              | `int`               | Maps to `Status` enum (1=NEW, 2=ASSIGNED, etc.)                                                     |
| `[3]`  | priority            | `int`               | **1-indexed**: P0=1, P1=2, P2=3, P3=4, P4=5                                                         |
| `[4]`  | severity            | `int \| null`       | **1-indexed**: S0=1, S1=2, S2=3, S3=4, S4=5. Often matches priority but diverges on security issues |
| `[5]`  | title               | `str`               | Issue title/summary                                                                                 |
| `[6]`  | reporter            | user array          | Person who filed the issue                                                                          |
| `[7]`  | verifier            | user array          | Person who verified the fix                                                                         |
| `[8]`  | (unknown)           | —                   | —                                                                                                   |
| `[9]`  | ccs                 | `list[user_array]`  | CC'd users                                                                                          |
| `[10]` | (unknown)           | —                   | —                                                                                                   |
| `[11]` | (unknown)           | —                   | —                                                                                                   |
| `[12]` | (unknown)           | —                   | —                                                                                                   |
| `[13]` | hotlist_ids         | `list[int]`         | Hotlist IDs the issue belongs to                                                                    |
| `[14]` | custom_field_values | `list[field_entry]` | Custom field value entries (see [Custom Fields](#custom-fields))                                    |
| `[16]` | found_in            | `list[str]`         | "Found In" version strings (e.g. `["CP21.260116.011.A1"]`). API name: `found_in_versions`           |
| `[19]` | in_prod             | `bool \| null`      | `True` = observed in production, `null` = no                                                        |
| `[21]` | duplicate_issue_ids | `list[int]`         | IDs of issues marked as duplicates of this one                                                      |
| `[30]` | collaborators       | `list[user_array]`  | Collaborator users, same format as CCs. Only present on some issues                                 |
| `[31]` | issue_access_level  | `list`              | Always `[1]`, possibly default access level                                                         |

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

### Severity

**The API uses 1-indexed severity.** Subtract 1 to get standard S0-S4.
Severity often matches priority but can diverge, especially on security
issues where severity may be S0 while priority is P2.

| API Value | Display |
|-----------|---------|
| 1         | S0      |
| 2         | S1      |
| 3         | S2      |
| 4         | S3      |
| 5         | S4      |

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

| Index | Field           | Type             | Notes                                                                    |
|-------|-----------------|------------------|--------------------------------------------------------------------------|
| `[0]` | author          | user array       | Who made this update                                                     |
| `[1]` | timestamp       | `[secs, nanos]`  | When the update happened                                                 |
| `[2]` | comment         | 18-element array | Comment body (see below), or `null` if field-change-only                 |
| `[3]` | sequence_number | `int`            | Ordering number for this update                                          |
| `[4]` | (unknown)       | —                | —                                                                        |
| `[5]` | field_changes   | `list`           | Array of field change entries                                            |
| `[6]` | comment_number  | `int`            | Comment number (descending in response)                                  |
| `[7]` | attachments     | `list`           | Attachment data: `[attachment_id, mime_type, size_bytes, filename, ...]` |
| `[8]` | (unknown)       | —                | —                                                                        |
| `[9]` | issue_id        | `int`            | The issue this update belongs to                                         |

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
| `[2]` | old_value  | Previous value (protobuf wrapper format)                  |
| `[3]` | new_value  | New value (protobuf wrapper format)                       |

The old/new value wrappers use typed protobuf wrappers like:

```json
[
  "type.googleapis.com/google.protobuf.Int32Value",
  [
    42
  ]
]
```

Known field names that appear in changes: `component_id`, `type`, `status`,
`priority`, `hotlist_ids`, `ccs`, `found_in_versions`. Currently we only
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

Issue responses only contain a numeric `component_id`. To resolve the
human-readable component name, use `GET /action/components/{id}` or the
batch endpoint `GET /action/components?id=X&id=Y`.

See [Get Component](#get-component) for the full response structure.

---

## Limitations

- This is an undocumented API. It could break if Google changes the response format.
- Only works with public issues. Private/restricted issues need authentication cookies that this client doesn't handle.
- The parser is entirely index-based. If the API adds or removes fields from the arrays, the parsing will silently
  return wrong data.
- Custom field mappings (OS, milestone, CVE, etc.) are based on the Chromium tracker. Other trackers may use different
  field IDs, in which case those fields will appear in the `custom_fields` dict instead of named attributes.
- Pagination for updates (comments) is not fully wired up, currently fetches the first page only.
- The batch endpoint may not return issues in the same order as the input IDs.

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

5. **`details[4]` is severity**, not priority. On most issues severity
   matches priority, but on security issues they diverge (e.g. S0 with P2).
   It is 1-indexed like priority: S0=1, S1=2, S2=3, S3=4, S4=5.

6. **`details[19]` is the "In Prod" flag.** `True` means the issue has
   been observed in production, `None` means no.

7. **`details[21]` is duplicate issue IDs**, not blocking. An issue with
   a DUPE COUNT of 10 will have exactly 10 IDs here. Blocking issue IDs
   are at `TOP[36]` instead.

8. **`TOP[43]` (issue body)** is only populated in **batch/detail
   responses**, not in search results. It is a comment-like array, not
   a plain string — the text is at `TOP[43][0]`. If you need the
   description, use batch fetch or the single-issue endpoint.

9. **`TOP[46]` (view counts)** contains `[24h_views, 7d_views, 30d_views]`.
   An empty `[]` means 0 views.

10. **The total count in search results is approximate.** It may fluctuate
    between pages and is prefixed with `~` in the CLI for this reason.

11. **Updates come newest-first.** Reverse the list if you need chronological
    order. The `IssueUpdatesResult.comments` property does this
    automatically.

12. **Component names require a separate request.** Issue responses only
    contain a numeric `component_id`. To resolve the name, use
    `GET /action/components/{id}` or the batch endpoint.

13. **"Blocked by" data is only available from the relationships endpoint.**
    The issue array at `TOP[36]` only contains issues that this issue
    blocks. To find what blocks this issue, use
    `GET /action/issues/{id}/relationships?relationshipType=1`.
