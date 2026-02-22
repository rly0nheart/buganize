from __future__ import annotations

import json
import typing as t
from datetime import datetime, timezone

from buganize.api.models import CUSTOM_FIELD_IDS

if t.TYPE_CHECKING:
    from buganize.api.models import (
        Comment,
        FieldChange,
        Issue,
        IssueType,
        IssueUpdate,
        IssueUpdatesResult,
        Priority,
        SearchResult,
        Status,
    )


def strip_response_prefix(raw_text: str) -> str:
    """Remove the )]}' anti-XSSI prefix that the API prepends to all JSON responses.

    :param raw_text: Raw response body from the API.
    :return: The response body with the prefix stripped, ready for json.loads().
    """

    for prefix in (")]}'\n", ")]}'\\n", ")]}'\r\n"):
        if raw_text.startswith(prefix):
            return raw_text[len(prefix):]
    return raw_text


def parse_json_response(raw_text: str) -> t.Any:
    """Strip the anti-XSSI prefix and parse the JSON body.

    :param raw_text: Raw response body from the API.
    :return: The parsed JSON (usually a nested list).
    """

    return json.loads(strip_response_prefix(raw_text))


def _safe_get(array: t.Any, *indices: int, default=None) -> t.Any:
    """Safely traverse nested arrays/lists by index.

    :param array: The root array to traverse.
    :param indices: One or more integer indices to follow.
    :param default: Value to return if any index is out of bounds.
    :return: The value at the given path, or default if not reachable.
    """

    current = array
    for index in indices:
        try:
            current = current[index]
        except (IndexError, TypeError, KeyError):
            return default
    return current


def _parse_timestamp(raw_timestamp: t.Any) -> t.Optional[datetime]:
    """Parse a [seconds, nanos] timestamp array into a UTC datetime.

    :param raw_timestamp: A list like [1657579144] or [1657579144, 285000000].
    :return: A timezone-aware UTC datetime, or None if unparseable.
    """

    if (
            not raw_timestamp
            or not isinstance(raw_timestamp, list)
            or len(raw_timestamp) < 1
    ):
        return None
    try:
        seconds = raw_timestamp[0]
        nanos = raw_timestamp[1] if len(raw_timestamp) > 1 else 0
        return datetime.fromtimestamp(seconds + nanos / 1e9, tz=timezone.utc)
    except (TypeError, ValueError, OSError):
        return None


def _parse_email(user_array: t.Any) -> t.Optional[str]:
    """Extract an email address from a user field array.

    User fields look like [null, "user@example.com", 1, [...]].
    We find the first string that looks like an email.

    :param user_array: A list representing a user, or None.
    :return: The email address, or None if not found.
    """

    if not user_array or not isinstance(user_array, list):
        return None
    for item in user_array:
        if isinstance(item, str) and ("@" in item or item):
            return item
    return None


def _parse_ccs(raw_ccs: t.Any) -> list[str]:
    """Parse a CC list where each entry is a user array like [null, "email", type].

    :param raw_ccs: List of user arrays.
    :return: List of email addresses.
    """

    if not raw_ccs or not isinstance(raw_ccs, list):
        return []
    emails = []
    for entry in raw_ccs:
        email = _parse_email(entry)
        if email:
            emails.append(email)
    return emails


def _parse_int_list(raw_list: t.Any) -> list[int]:
    """Extract integers from a list, ignoring non-int values.

    :param raw_list: A list that should contain integers (e.g. hotlist IDs).
    :return: Only the integer values from the list.
    """

    if not raw_list or not isinstance(raw_list, list):
        return []
    return [item for item in raw_list if isinstance(item, int)]


def _parse_custom_field_values(raw_field_entries: t.Any) -> dict[str, t.Any]:
    """Parse custom field value entries from the issue details array at [2][14].

    Each entry is an array like::

        [field_id, null, null, null, numeric_val?, label_values?,
         null, enum_values?, null, display_string, ...]

    The field_id is looked up in CUSTOM_FIELD_IDS to get a canonical name.
    Unknown fields get a ``field_{id}`` name.

    :param raw_field_entries: List of custom field arrays from the API.
    :return: Mapping of field names to their parsed values. Values are
        list[str] for multi-value fields, float for numeric fields,
        or str for single-value text fields.
    """

    if not raw_field_entries or not isinstance(raw_field_entries, list):
        return {}

    parsed_fields: dict[str, t.Any] = {}
    for entry in raw_field_entries:
        if not isinstance(entry, list) or len(entry) < 1:
            continue

        field_id = entry[0]
        field_name = CUSTOM_FIELD_IDS.get(field_id, f"field_{field_id}")

        display_string = _safe_get(entry, 9)

        # Numeric value at index 4.
        numeric_value = _safe_get(entry, 4)
        if isinstance(numeric_value, (int, float)):
            parsed_fields[field_name] = numeric_value
            continue

        # Multi-value labels at index 5: [[val1, val2, ...]]
        label_values = _safe_get(entry, 5)
        if label_values and isinstance(label_values, list):
            flat_labels = []
            for group in label_values:
                if isinstance(group, list):
                    flat_labels.extend(s for s in group if isinstance(s, str))
                elif isinstance(group, str):
                    flat_labels.append(group)
            if flat_labels:
                parsed_fields[field_name] = flat_labels
                continue

        # Enum-like values at index 7: [[val1, val2, ...]]
        enum_values = _safe_get(entry, 7)
        if enum_values and isinstance(enum_values, list):
            flat_enums = []
            for group in enum_values:
                if isinstance(group, list):
                    flat_enums.extend(s for s in group if isinstance(s, str))
                elif isinstance(group, str):
                    flat_enums.append(group)
            if flat_enums:
                parsed_fields[field_name] = flat_enums
                continue

        # Fall back to the display string.
        if display_string and isinstance(display_string, str):
            parsed_fields[field_name] = display_string

    return parsed_fields


def parse_issue_from_entry(raw_entry: list) -> Issue:
    """Parse a single issue from the 48-element array format used across all endpoints.

    This is the api parser. Every endpoint (search, get, batch) ultimately
    produces these 48-element arrays, just nested at different paths.

    Array index map::

        Top-level (48 elements):
          [1]  = issue ID (int)
          [2]  = details array (32 elements, see below)
          [4]  = created timestamp [seconds, nanos]
          [5]  = modified timestamp [seconds, nanos]
          [6]  = verified timestamp [seconds, nanos]
          [9]  = star count (int)
          [10] = [unknown constant, always 3]
          [11] = comment count (int)
          [13] = owner user array
          [14] = custom field definitions (schema, not values)
          [41] = tracker ID (int)
          [47] = last modifier user array

        Details array [2] (32 elements):
          [0]  = component ID (int)
          [1]  = issue type (int, maps to IssueType enum)
          [2]  = status (int, maps to Status enum)
          [3]  = priority (int, 1-indexed: P0=1, P1=2, P2=3, P3=4, P4=5)
          [5]  = title (str)
          [6]  = reporter user array
          [7]  = verifier user array
          [9]  = CCs list (list of user arrays)
          [13] = hotlist IDs (list of ints)
          [14] = custom field values (list of field arrays)
          [21] = blocking/related issue IDs (list of ints)

    :param raw_entry: The 48-element array representing one issue.
    :return: A fully populated Issue dataclass.
    """

    issue_id = _safe_get(raw_entry, 1, default=0)
    details = _safe_get(raw_entry, 2, default=[]) or []

    # --- Details array fields ---
    component_id = _safe_get(details, 0)
    issue_type_detail = _safe_get(details, 1)
    status_value = _safe_get(details, 2, default=1)
    priority_raw = _safe_get(details, 3, default=3)  # 1-indexed: P0=1, P1=2, ...
    # Convert 1-indexed API priority to 0-indexed enum (P0=0, P1=1, ...)
    priority_value = (priority_raw - 1) if isinstance(priority_raw, int) else 2
    title = _safe_get(details, 5, default="") or ""
    reporter_array = _safe_get(details, 6)
    verifier_array = _safe_get(details, 7)
    ccs_array = _safe_get(details, 9)
    hotlist_ids_array = _safe_get(details, 13)
    custom_field_entries = _safe_get(details, 14)
    blocking_ids_array = _safe_get(details, 21)

    # --- Top-level fields ---
    created_timestamp = _safe_get(raw_entry, 4)
    modified_timestamp = _safe_get(raw_entry, 5)
    verified_timestamp = _safe_get(raw_entry, 6)
    star_count = _safe_get(raw_entry, 9, default=0)
    if not isinstance(star_count, int):
        star_count = 0
    issue_type_value = issue_type_detail
    comment_count = _safe_get(raw_entry, 11, default=0) or 0
    owner_array = _safe_get(raw_entry, 13)
    tracker_id = _safe_get(raw_entry, 41)
    last_modifier_array = _safe_get(raw_entry, 47)

    # --- Parse custom fields into a mutable dict, then pop known ones ---
    custom_fields = _parse_custom_field_values(custom_field_entries)

    def pop_string_list(key: str) -> list[str]:
        """Pop a key from custom_fields and return it as a list of strings."""

        value = custom_fields.pop(key, None)
        if value is None:
            return []
        if isinstance(value, list):
            return value
        if isinstance(value, str):
            return [part.strip() for part in value.split(",") if part.strip()]
        return []

    def pop_string(key: str) -> t.Optional[str]:
        """Pop a key from custom_fields and return it as a single string."""

        value = custom_fields.pop(key, None)
        if value is None:
            return None
        if isinstance(value, str):
            return value
        if isinstance(value, list):
            return ", ".join(str(v) for v in value)
        return str(value)

    def pop_float(key: str) -> t.Optional[float]:
        """Pop a key from custom_fields and return it as a float."""

        value = custom_fields.pop(key, None)
        if value is None:
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    return Issue(
        id=issue_id,
        title=title,
        status=Status(status_value) if status_value else Status.NEW,
        priority=(
            Priority(priority_value) if priority_value is not None else Priority.P2
        ),
        issue_type=IssueType(issue_type_value) if issue_type_value else None,
        reporter=_parse_email(reporter_array),
        owner=_parse_email(owner_array),
        verifier=_parse_email(verifier_array),
        component_id=component_id,
        ccs=_parse_ccs(ccs_array),
        created_at=_parse_timestamp(created_timestamp),
        modified_at=_parse_timestamp(modified_timestamp),
        verified_at=_parse_timestamp(verified_timestamp),
        comment_count=comment_count,
        star_count=star_count,
        tracker_id=tracker_id,
        last_modifier=_parse_email(last_modifier_array),
        hotlist_ids=_parse_int_list(hotlist_ids_array),
        blocking_issue_ids=_parse_int_list(blocking_ids_array),
        component_tags=pop_string_list("component_tags"),
        component_ancestor_tags=pop_string_list("component_ancestor_tags"),
        chromium_labels=pop_string_list("chromium_labels"),
        os=pop_string_list("os"),
        milestone=pop_string_list("milestone"),
        merge=pop_string_list("merge"),
        merge_request=pop_string_list("merge_request"),
        release_block=pop_string_list("release_block"),
        cve=pop_string_list("cve"),
        cwe_id=pop_float("cwe_id"),
        vrp_reward=pop_float("vrp_reward"),
        estimated_days=pop_float("estimated_days"),
        build_number=pop_string("build_number"),
        flaky_test=pop_string("flaky_test"),
        next_action=pop_string("next_action"),
        notice=pop_string("notice"),
        introduced_in=pop_string("introduced_in"),
        irm_link=pop_string("irm_link"),
        security_release=pop_string_list("security_release"),
        fixed_by_code_changes=pop_string_list("fixed_by_code_changes"),
        custom_fields=custom_fields,
    )


def parse_search_response(
        raw_text: str,
        query: str = "",
        page_size: int = 50,
) -> SearchResult:
    """Parse a search/list response.

    Response shape::

        [["b.IssueSearchResponse", ..., [issues, page_token, total_count]]]

    Issues at ``[0][6][0]``, pagination token at ``[0][6][1]``,
    total count at ``[0][6][2]``.

    :param raw_text: Raw response body from POST /action/issues/list.
    :param query: The query string used (stored on the result for pagination).
    :param page_size: The page size used (stored on the result for pagination).
    :return: Parsed issues with pagination info.
    """

    data = parse_json_response(raw_text)

    response_wrapper = _safe_get(data, 0, default=[])
    result_block = _safe_get(response_wrapper, 6, default=[])

    raw_issues = _safe_get(result_block, 0, default=[]) or []
    page_token = _safe_get(result_block, 1)
    total_count = _safe_get(result_block, 2, default=0) or 0

    issues = [
        parse_issue_from_entry(entry) for entry in raw_issues if isinstance(entry, list)
    ]

    return SearchResult(
        issues=issues,
        total_count=total_count,
        next_page_token=page_token if page_token else None,
        query=query,
        page_size=page_size,
    )


def parse_issue_detail_response(raw_text: str) -> Issue:
    """Parse a getIssue response.

    Response shape::

        [["b.IssueFetchResponse", [<23-element payload>]]]

    The 48-element issue entry is at ``data[0][1][22]``
    (last element of the payload).

    :param raw_text: Raw response body from POST /action/issues/{id}/getIssue.
    :return: The fully parsed issue.
    :raises ValueError: If the issue entry can't be located in the response.
    """

    data = parse_json_response(raw_text)

    response_wrapper = _safe_get(data, 0, default=[])
    payload = _safe_get(response_wrapper, 1, default=[])

    issue_entry = None
    if isinstance(payload, list) and len(payload) > 0:
        for i in range(len(payload) - 1, -1, -1):
            candidate = _safe_get(payload, i)
            if isinstance(candidate, list) and isinstance(_safe_get(candidate, 1), int):
                issue_entry = candidate
                break

    if issue_entry is None:
        raise ValueError("Could not locate issue entry in getIssue response")

    return parse_issue_from_entry(issue_entry)


def parse_batch_response(raw_text: str) -> list[Issue]:
    """Parse a batch get response.

    Response shape::

        [["b.BatchGetIssuesResponse", null, [[issue1, issue2, ...]]]]

    Each issue at ``data[0][2][0][i]`` is a standard 48-element array.

    :param raw_text: Raw response body from POST /action/issues/batch.
    :return: List of parsed issues.
    """

    data = parse_json_response(raw_text)

    response_wrapper = _safe_get(data, 0, default=[])
    entries_wrapper = _safe_get(response_wrapper, 2, default=[])
    raw_issues = _safe_get(entries_wrapper, 0, default=[]) or []

    return [
        parse_issue_from_entry(entry)
        for entry in raw_issues
        if isinstance(entry, list) and isinstance(_safe_get(entry, 1), int)
    ]


def _parse_field_changes(raw_changes: t.Any) -> list[FieldChange]:
    """Parse field change entries from an update's changes array.

    Each change looks like ``["field_name", null, old_value_wrapper, new_value_wrapper]``.
    We currently only extract the field name.

    :param raw_changes: The field changes array from an update entry.
    :return: List of parsed field changes.
    """

    if not raw_changes or not isinstance(raw_changes, list):
        return []
    changes = []
    for entry in raw_changes:
        if not isinstance(entry, list) or len(entry) < 1:
            continue
        field_name = entry[0] if isinstance(entry[0], str) else str(entry[0])
        changes.append(FieldChange(field=field_name))
    return changes


def _parse_comment(raw_comment: t.Any, issue_id: int) -> t.Optional[Comment]:
    """Parse a comment body array (18 elements) into a Comment.

    Comment array index map::

        [0]  = comment text (str)
        [2]  = author user array
        [3]  = timestamp [seconds, nanos]
        [5]  = issue ID (int)
        [6]  = comment sequence number (0-indexed in the API)

    :param raw_comment: The 18-element comment array from an update entry.
    :param issue_id: The issue ID this comment belongs to.
    :return: The parsed comment, or None if raw_comment is invalid.
    """

    if not raw_comment or not isinstance(raw_comment, list):
        return None

    comment_text = _safe_get(raw_comment, 0, default="") or ""
    author_array = _safe_get(raw_comment, 2)
    timestamp_array = _safe_get(raw_comment, 3)
    sequence_number = _safe_get(raw_comment, 6, default=0) or 0

    return Comment(
        issue_id=issue_id,
        comment_number=sequence_number + 1,  # convert from 0-indexed to 1-indexed
        author=_parse_email(author_array),
        timestamp=_parse_timestamp(timestamp_array),
        body=comment_text,
    )


def parse_updates_response(raw_text: str) -> IssueUpdatesResult:
    """Parse a ListIssueUpdatesResponse (comments + field changes).

    Response shape::

        [["b.ListIssueUpdatesResponse", [[update, ...], page_token, total_count]]]

    Each update is a 10-element array::

        [0] = author user array
        [1] = timestamp [seconds, nanos]
        [2] = comment body (18-element array) or None
        [3] = update sequence number
        [5] = field changes array
        [6] = comment number (descending in response order)
        [9] = issue ID

    Updates are returned newest-first. Use ``.comments`` on the result to get
    comments in chronological order.

    :param raw_text: Raw response body from POST /action/issues/{id}/updates.
    :return: Parsed updates with pagination info.
    """

    data = parse_json_response(raw_text)

    response_wrapper = _safe_get(data, 0, default=[])
    result_block = _safe_get(response_wrapper, 1, default=[])

    raw_updates = _safe_get(result_block, 0, default=[]) or []
    page_token = _safe_get(result_block, 1)
    total_count = _safe_get(result_block, 2, default=0) or 0

    updates = []
    for update_entry in raw_updates:
        if not isinstance(update_entry, list):
            continue

        issue_id = _safe_get(update_entry, 9, default=0) or 0
        author_array = _safe_get(update_entry, 0)
        timestamp_array = _safe_get(update_entry, 1)
        comment_array = _safe_get(update_entry, 2)
        sequence_number = _safe_get(update_entry, 3)
        changes_array = _safe_get(update_entry, 5)

        comment = _parse_comment(comment_array, issue_id) if comment_array else None

        updates.append(
            IssueUpdate(
                issue_id=issue_id,
                sequence_number=sequence_number,
                author=_parse_email(author_array),
                timestamp=_parse_timestamp(timestamp_array),
                comment=comment,
                field_changes=_parse_field_changes(changes_array),
            )
        )

    return IssueUpdatesResult(
        updates=updates,
        total_count=total_count,
        next_page_token=page_token if page_token else None,
    )
