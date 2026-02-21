from __future__ import annotations

import enum
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional


class Status(enum.IntEnum):
    """Issue status values used by the Chromium tracker.

    The first three (NEW, ASSIGNED, ACCEPTED) are considered open.
    Everything else is a closed/resolved state. Unknown values from
    the API get an auto-generated UNKNOWN_N name instead of crashing.
    """

    NEW = 1
    ASSIGNED = 2
    ACCEPTED = 3
    FIXED = 4
    VERIFIED = 5
    NOT_REPRODUCIBLE = 6
    INTENDED_BEHAVIOR = 7
    OBSOLETE = 8
    INFEASIBLE = 9
    DUPLICATE = 10

    @classmethod
    def _missing_(cls, value):
        obj = int.__new__(cls, value)
        obj._name_ = f"UNKNOWN_{value}"
        obj._value_ = value
        return obj

    @property
    def is_open(self) -> bool:
        """Whether this status represents an open (unresolved) issue."""
        return self in (Status.NEW, Status.ASSIGNED, Status.ACCEPTED)


class Priority(enum.IntEnum):
    """Issue priority levels. P0 is the most urgent, P4 is the lowest.

    Unknown values from the API get an auto-generated PN name.
    """

    P0 = 0
    P1 = 1
    P2 = 2
    P3 = 3
    P4 = 4

    @classmethod
    def _missing_(cls, value):
        obj = int.__new__(cls, value)
        obj._name_ = f"P{value}"
        obj._value_ = value
        return obj


class IssueType(enum.IntEnum):
    """Issue type categories.

    Unknown values from the API get an auto-generated TYPE_N name.
    """

    BUG = 1
    FEATURE_REQUEST = 2
    CUSTOMER_ISSUE = 3
    INTERNAL_CLEANUP = 4
    PROCESS = 5
    VULNERABILITY = 6

    @classmethod
    def _missing_(cls, value):
        obj = int.__new__(cls, value)
        obj._name_ = f"TYPE_{value}"
        obj._value_ = value
        return obj


# Maps numeric custom field IDs to human-readable names.
# These are the 24 well-known fields in the Chromium tracker (tracker 157).
# The parser uses this to turn raw field IDs into named attributes.
CUSTOM_FIELD_IDS: dict[int, str] = {
    1225362: "backlog_rank",
    1223033: "build_number",
    1223031: "chromium_labels",
    1222907: "component_tags",
    1223136: "cve",
    1410892: "cwe_id",
    1223032: "design_doc",
    1223131: "design_summary",
    1225337: "estimated_days",
    1223081: "flaky_test",
    1223087: "merge",
    1223134: "merge_request",
    1223085: "milestone",
    1225154: "next_action",
    1223083: "notice",
    1223084: "os",
    1223086: "release_block",
    1223034: "respin",
    1300460: "irm_link",
    1223088: "security_release",
    1223135: "vrp_reward",
    1358989: "fixed_by_code_changes",
    1253656: "component_ancestor_tags",
    1544844: "introduced_in",
}


@dataclass
class CustomFieldValue:
    """A single custom field value that didn't map to a known attribute.

    Attributes:
        field_id: Numeric ID of the custom field.
        name: Human-readable name (from CUSTOM_FIELD_IDS or "field_N").
        values: String values for multi-value fields.
        numeric_value: Numeric value for number-type fields.
    """

    field_id: int
    name: str
    values: list[str] = field(default_factory=list)
    numeric_value: Optional[float] = None


@dataclass
class Issue:
    """A single Chromium issue with all available fields.

    Basic fields (id, title, status, priority, etc.) are always populated.
    Custom fields (os, milestone, cve, etc.) come from the tracker's
    configurable field system and may be empty.

    Attributes:
        id: Unique numeric issue ID.
        title: Issue title/summary.
        status: Current status (open, fixed, etc.).
        priority: Priority level (P0-P4).
        issue_type: Category (bug, feature request, etc.).
        reporter: Email of the person who filed the issue.
        owner: Email of the currently assigned owner.
        verifier: Email of the person who verified the fix.
        component_id: Numeric ID of the primary component.
        ccs: List of CC'd email addresses.
        created_at: When the issue was created (UTC).
        modified_at: When the issue was last modified (UTC).
        verified_at: When the fix was verified (UTC).
        comment_count: Total number of comments.
        star_count: Number of stars (watchers/votes).
        tracker_id: Tracker ID (157 for Chromium).
        last_modifier: Email of the last person to modify the issue.
        hotlist_ids: IDs of hotlists this issue belongs to.
        blocking_issue_ids: IDs of issues this one blocks or is related to.
        component_tags: Component tags (e.g. ["Blink>JavaScript"]).
        component_ancestor_tags: Full component ancestry.
        chromium_labels: Chromium-specific labels.
        os: Affected operating systems (e.g. ["Linux", "Mac", "Windows"]).
        milestone: Affected milestones.
        merge: Merge status labels.
        merge_request: Merge request labels.
        release_block: Release-blocking labels.
        cve: CVE identifiers.
        cwe_id: CWE weakness ID.
        vrp_reward: Bug bounty (VRP) reward amount.
        estimated_days: Estimated engineer-days to complete.
        build_number: Affected build number string.
        flaky_test: Flaky test identifier.
        next_action: Next expected action or deadline.
        notice: Notice text.
        introduced_in: Milestone the vulnerability was first introduced.
        irm_link: Link to related IRM incident.
        security_release: Security release labels.
        fixed_by_code_changes: Gerrit URLs of fixing code changes.
        custom_fields: Catch-all dict for any fields not mapped to attributes above.
    """

    id: int
    title: str
    status: Status = Status.NEW
    priority: Priority = Priority.P2
    issue_type: Optional[IssueType] = None
    reporter: Optional[str] = None
    owner: Optional[str] = None
    verifier: Optional[str] = None
    component_id: Optional[int] = None
    ccs: list[str] = field(default_factory=list)
    created_at: Optional[datetime] = None
    modified_at: Optional[datetime] = None
    verified_at: Optional[datetime] = None
    comment_count: int = 0
    star_count: int = 0
    tracker_id: Optional[int] = None
    last_modifier: Optional[str] = None
    hotlist_ids: list[int] = field(default_factory=list)
    blocking_issue_ids: list[int] = field(default_factory=list)
    component_tags: list[str] = field(default_factory=list)
    component_ancestor_tags: list[str] = field(default_factory=list)
    chromium_labels: list[str] = field(default_factory=list)
    os: list[str] = field(default_factory=list)
    milestone: list[str] = field(default_factory=list)
    merge: list[str] = field(default_factory=list)
    merge_request: list[str] = field(default_factory=list)
    release_block: list[str] = field(default_factory=list)
    cve: list[str] = field(default_factory=list)
    cwe_id: Optional[float] = None
    vrp_reward: Optional[float] = None
    estimated_days: Optional[float] = None
    build_number: Optional[str] = None
    flaky_test: Optional[str] = None
    next_action: Optional[str] = None
    notice: Optional[str] = None
    introduced_in: Optional[str] = None
    irm_link: Optional[str] = None
    security_release: list[str] = field(default_factory=list)
    fixed_by_code_changes: list[str] = field(default_factory=list)
    custom_fields: dict[str, Any] = field(default_factory=dict)

    @property
    def url(self) -> str:
        """Direct link to this issue on issues.chromium.org."""
        return f"https://issues.chromium.org/issues/{self.id}"


@dataclass
class Comment:
    """A single comment on an issue.

    Attributes:
        issue_id: The issue this comment belongs to.
        comment_number: 1-indexed comment number.
        author: Email of the comment author.
        timestamp: When the comment was posted (UTC).
        body: The comment text.
    """

    issue_id: int
    comment_number: int
    author: Optional[str] = None
    timestamp: Optional[datetime] = None
    body: str = ""


@dataclass
class FieldChange:
    """A single field change within an issue update.

    Attributes:
        field: Name of the changed field (e.g. "status", "priority").
        old_value: Previous value (not always available from the API).
        new_value: New value (not always available from the API).
    """

    field: str
    old_value: Optional[str] = None
    new_value: Optional[str] = None


@dataclass
class IssueUpdate:
    """An issue update entry. May contain a comment, field changes, or both.

    Attributes:
        issue_id: The issue this update belongs to.
        sequence_number: Ordering number for this update.
        author: Email of the person who made this update.
        timestamp: When the update happened (UTC).
        comment: The comment attached to this update, if any.
        field_changes: List of field changes in this update.
    """

    issue_id: int
    sequence_number: Optional[int] = None
    author: Optional[str] = None
    timestamp: Optional[datetime] = None
    comment: Optional[Comment] = None
    field_changes: list[FieldChange] = field(default_factory=list)


@dataclass
class IssueUpdatesResult:
    """Result from fetching issue updates (comments + field changes).

    The API returns updates in reverse chronological order (newest first).
    Use the .comments property to get just the comments in chronological order.

    Attributes:
        updates: All updates, newest first.
        total_count: Total number of updates for this issue.
        next_page_token: Token for fetching the next page, if there are more.
    """

    updates: list[IssueUpdate]
    total_count: int
    next_page_token: Optional[str] = None

    @property
    def comments(self) -> list[Comment]:
        """Only the updates that have comments, in chronological order (oldest first)."""
        return [u.comment for u in reversed(self.updates) if u.comment is not None]

    @property
    def has_more(self) -> bool:
        """Whether there are more updates beyond this page."""
        return self.next_page_token is not None


@dataclass
class SearchResult:
    """Result from searching/listing issues.

    Attributes:
        issues: The matching issues for this page.
        total_count: Total number of matching issues (across all pages).
        next_page_token: Token for fetching the next page, if there are more.
        query: The query string used for this search (stored for pagination).
        page_size: The page size used for this search (stored for pagination).
    """

    issues: list[Issue]
    total_count: int
    next_page_token: Optional[str] = None
    query: str = ""
    page_size: int = 50

    @property
    def has_more(self) -> bool:
        """Whether there are more results beyond this page."""
        return self.next_page_token is not None
