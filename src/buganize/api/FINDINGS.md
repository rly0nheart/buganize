# Authenticated API Findings

> **Last updated:** 16 06 2026, 17:10:55

Discoveries from intercepting browser traffic (mitmproxy/mitmweb) while authenticated
on `issuetracker.google.com`. These supplement the main `README.md` which
documents the unauthenticated API.

## New Endpoints

| # | Endpoint                                    | Method | Tested   | Notes                                                                                          |
|---|---------------------------------------------|--------|----------|------------------------------------------------------------------------------------------------|
| 1 | `/action/issues/{id}/listComments`          | POST   | **true** | Dedicated comments endpoint, separate from `/updates`                                          |
| 2 | `/action/current_user/preferences`          | POST   | false    | Returns user preferences (seen: `[["f.mt"]]`)                                                  |
| 3 | `/action/issues/read_timestamp`             | POST   | false    | Marks issue as read, returns timestamp                                                         |
| 4 | `/action/access_policies/components%2F{id}` | GET    | **true** | `b.AccessPolicy`: user arrays grouped by role (admin/writer/appender/reader)                    |
| 5 | `/action/user_access`                       | GET    | **true** | Returns only relations the principal holds; observed `4` = reader on a public issue            |
| 6 | `/action/retrieve_similar_issues`           | POST   | false    | Returns 401 without Google auth cookies                                                        |
| 7 | `/action/yes`                               | GET    | **true** | Buganizer-wide health check, returns `yes` (text/plain). Implemented as `client.echo()`         |

## Changes to Existing Endpoints

| #  | What Changed                          | Tested | Notes                                                                                                                                                         |
|----|---------------------------------------|--------|---------------------------------------------------------------------------------------------------------------------------------------------------------------|
| 8  | Updates request format                | **true** | `[issue_id, "ASC", 1100, null, 2]` works. Pos 1 = sort order (`"ASC"`/`"DESC"`), pos 2 = page size, pos 4 = unknown flag (always `2`)                         |
| 9  | New field change types in updates     | **true** | `is_archived`, `is_deleted`, `access_limit` appear in the initial (seq 1) update's field changes                                                             |
| 10 | New protobuf types                    | false  | `google.devtools.issuetracker.v1.IssueAccessLimit`, `google.devtools.issuetracker.v1.User`                                                                    |
| 11 | Issue array TOP[34] and TOP[35]       | **true** | `TOP[35]` ≈ `modified_at` (last write); `TOP[34]` = last substantive update. See below                                                                       |
| 12 | Hotlists batch silently drops private | false  | Batch GET returns only accessible hotlists, individual GETs return 403 for private ones                                                                       |

---

## Endpoint Details

### 1. listComments (TESTED)

```
POST /action/issues/{issue_id}/listComments
```

Works without authentication. No cookies or tokens needed.

**Request body:**

```json
[
  ISSUE_ID,
  SORT_ORDER,
  PAGE_SIZE,
  PAGE_TOKEN
]
```

| Position | Field      | Type             | Description                                                                  |
|----------|------------|------------------|------------------------------------------------------------------------------|
| `[0]`    | issue_id   | `int`            | The issue ID                                                                 |
| `[1]`    | sort_order | `str \| null`    | `"DESC"` for newest-first (default), `"ASC"` for oldest-first. `null` = DESC |
| `[2]`    | page_size  | `int`            | Number of comments per page                                                  |
| `[3]`    | page_token | `str \| omitted` | Pagination token from previous response (e.g. `"start_index:2"`)             |

**Response type:** `b.ListIssueCommentsResponse`

```
data[0] = ["b.ListIssueCommentsResponse", [COMMENTS, PAGE_TOKEN, TOTAL_COUNT]]
```

| Path        | Type          | Description                                                             |
|-------------|---------------|-------------------------------------------------------------------------|
| `[0][1][0]` | `list[list]`  | Array of 18-element comment entries                                     |
| `[0][1][1]` | `str \| null` | Next page token (e.g. `"start_index:2"`), `null` on last page           |
| `[0][1][2]` | `int`         | Total comment count (only text comments, not field-change-only updates) |

**Observations from testing:**

- Default sort (null) is **DESC** (newest first).
- `"ASC"` and `"DESC"` both confirmed working.
- `total_count` here counts only text comments, which is lower than `issue.comment_count`
  (which includes field-change-only updates from the `/updates` endpoint).
- Pagination token format is `"start_index:N"`.

**Comment array (18 elements):**

Same format as comments from the `/updates` endpoint. Comment arrays are
18 elements (indices 0 to 17).

| Index  | Field           | Type            | Notes                                                                 |
|--------|-----------------|-----------------|-----------------------------------------------------------------------|
| `[0]`  | body            | `str`           | Comment text                                                          |
| `[2]`  | author          | user array      | Comment author                                                        |
| `[3]`  | modified_at     | `[secs, nanos]` | When the comment was last modified (equals `[18]` if never edited)    |
| `[4]`  | (unknown)       | `list`          | Always `[]`                                                           |
| `[5]`  | issue_id        | `int`           | Parent issue ID                                                       |
| `[6]`  | sequence_number | `int`           | **1-indexed** comment number (unlike `/updates` where it's 0-indexed) |
| `[8]`  | (unknown)       | `int`           | Small enum (`1` or `2`); likely a comment type/format marker          |
| `[9]`  | (unknown)       | `list`          | Constant `[[1]]`; purpose unknown                                     |
| `[14]` | comment_token   | `str`           | Opaque per-comment token: double-base64 of a 128-bit hex value, unique per comment and stable across fetches |
| `[17]` | last_editor     | user array      | Possibly the last person to edit this comment                         |
| `[18]` | created_at      | `[secs, nanos]` | Original post time. Confirmed via 491 live comments: `[18] <= [3]` always; `[18] < [3]` exactly when the comment was edited (including author self-edits, which leave `last_editor` unchanged) |

**Example — fetch first 3 comments (oldest first) for issue 496840714:**

Request:

```json
[
  496840714,
  "ASC",
  3
]
```

Response (trimmed):

```json
[
  [
    "b.ListIssueCommentsResponse",
    [
      [
        [
          "This is an **M147** merge request from crbug/495542144...",
          null,
          [
            null,
            "chromium-merge@google.com",
            1,
            [
              "google_domain"
            ]
          ],
          [
            1774605025,
            724000000
          ],
          [],
          496840714,
          1,
          null,
          2,
          [
            [
              1
            ]
          ],
          null,
          null,
          null,
          null,
          "WVRReVltSTBNVEl5...",
          null,
          null,
          [
            null,
            "chromium-merge@google.com",
            1,
            [
              "google_domain"
            ]
          ]
        ],
        [
          "Fixes a major user reported regression...",
          null,
          [
            null,
            "user@google.com",
            1,
            [
              "googlers_unrestricted",
              "google_domain"
            ]
          ],
          [
            1774605229,
            679000000
          ],
          [],
          496840714,
          2,
          null,
          2,
          [
            [
              1
            ]
          ],
          null,
          null,
          null,
          null,
          "WVRReVltSTBNVEl5...",
          null,
          null,
          [
            null,
            "user@google.com",
            1,
            [
              "googlers_unrestricted",
              "google_domain"
            ]
          ]
        ]
      ],
      "start_index:2",
      7
    ]
  ]
]
```

Key takeaways from this example:

- Comment `[6]` is **1-indexed** (first comment = 1, not 0).
- `[8]` is a small enum (`1` or `2`), independent of the sequence number;
  likely a comment type/format marker.
- `[17]` matches `[2]` (author = last_editor) when the comment hasn't been edited.
- Page token `"start_index:2"` means the next page starts at offset 2.
- Total is `7` (text comments only, not the 22 from `issue.comment_count`).

### 2. current_user/preferences

```
POST /action/current_user/preferences
```

**Request body:** Unknown (not captured).

**Response:** `[["f.mt"]]` — meaning unknown.

### 3. read_timestamp

```
POST /action/issues/read_timestamp
```

**Request body:**

```json
[
  null,
  null,
  null,
  [
    [
      ISSUE_IDS
    ],
    1,
    1
  ]
]
```

**Response type:** `b.UpdateIssueReadTimestampResponse`

```json
[
  [
    "b.UpdateIssueReadTimestampResponse",
    null,
    [
      null,
      null,
      [
        SECS,
        NANOS
      ]
    ]
  ]
]
```

### 4. access_policies

```
GET /action/access_policies/components%2F{component_id}
```

**Response type:** `b.AccessPolicy`

Contains nested arrays of user arrays organized by role (admin, writer,
appender, reader). Includes both individual users and groups
(e.g. `"googlers_unrestricted"`, `"public_non_google"`).

### 5. user_access

```
GET /action/user_access?relations=admin,writer,appender,reader&resourceNames=issues/{id}
```

**Response type:** `b.UserAccessBatchResponse`

```json
[
  [
    "b.UserAccessBatchResponse",
    [
      [
        "b.ResourceRelation",
        "issues/497175171",
        3
      ],
      [
        "b.ResourceRelation",
        "issues/497175171",
        4
      ]
    ]
  ]
]
```

The integer is the relation type, in the order of the `relations=` query
parameter: `1` = admin, `2` = writer, `3` = appender, `4` = reader. The
response contains only the relations the principal actually holds; a
public read-only user on a public issue returns just `4` (reader).

### 6. retrieve_similar_issues

```
POST /action/retrieve_similar_issues
```

**Request body:**

```json
[
  "b.RetrieveSimilarIssuesRequest",
  [
    ISSUE_ID,
    null,
    null,
    7,
    null,
    null,
    2
  ]
]
```

Returns **401** without full Google auth — requires session cookies beyond
what the public API uses.

### 7. /action/yes (TESTED)

```
GET /action/yes
```

Returns the literal string `yes` as `text/plain`. No anti-XSSI prefix, no JSON.
No authentication required.

Works on **all 13 tracker domains** — useful as a connectivity check:

| Domain                             | Status    |
|------------------------------------|-----------|
| `issuetracker.google.com`          | 200 `yes` |
| `issues.chromium.org`              | 200 `yes` |
| `issues.pigweed.dev`               | 200 `yes` |
| `issues.gerritcodereview.com`      | 200 `yes` |
| `issues.skia.org`                  | 200 `yes` |
| `issues.webrtc.org`                | 200 `yes` |
| `issues.fuchsia.dev`               | 200 `yes` |
| `issues.angleproject.org`          | 200 `yes` |
| `issues.webmproject.org`           | 200 `yes` |
| `issues.oss-fuzz.com`              | 200 `yes` |
| `project-zero.issues.chromium.org` | 200 `yes` |
| `gn.issues.chromium.org`           | 200 `yes` |
| `git.issues.gerritcodereview.com`  | 200 `yes` |

---

## Updated Observations

### Updates Request (finding #8)

The browser sends a richer request body than documented:

```json
[
  ISSUE_ID,
  "ASC",
  1100,
  null,
  2
]
```

| Position | Field      | Type          | Description                                              |
|----------|------------|---------------|----------------------------------------------------------|
| `[0]`    | issue_id   | `int`         | The issue ID                                             |
| `[1]`    | sort_order | `str`         | `"ASC"` = chronological (oldest first)                   |
| `[2]`    | page_size  | `int`         | 1100 (much larger than the 25/50/100/250 seen in search) |
| `[3]`    | page_token | `null \| str` | Pagination token                                         |
| `[4]`    | unknown    | `int`         | Always `2` — purpose unknown                             |

### New Field Change Types (finding #9)

These field names appear in `update[5]` but are not in the README:

- `is_archived` — `BoolValue`
- `is_deleted` — `BoolValue`
- `access_limit` — `IssueAccessLimit` (value `[1]`, probably default access)

### Issue Array TOP[34] and TOP[35] (finding #11)

Both are `[secs, nanos]` timestamps present on every issue.

`TOP[35]` tracks the last write to the issue, equal to `modified_at`
(`TOP[5]`) or within a few seconds of it. It moves on every change,
including the automated metadata churn (hotlist and custom-field bot
updates) that also bumps `modified_at`.

`TOP[34]` is the timestamp of the last substantive update: the most
recent comment or meaningful field change (status, assignee, component).
It excludes the trailing automated metadata churn, so on bot-triaged
issues `TOP[34]` ≤ `TOP[35]`. It is populated even on issues with no
comments, anchored to the last meaningful field change in that case.
