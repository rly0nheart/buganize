import enum
import typing as t
from dataclasses import dataclass, field
from datetime import datetime

__all__ = [
    "CUSTOM_FIELD_IDS",
    "Comment",
    "CommentsResult",
    "CustomFieldValue",
    "EXTRA_FIELDS",
    "FieldChange",
    "Issue",
    "IssueType",
    "IssueUpdate",
    "IssueUpdatesResult",
    "Priority",
    "SearchResult",
    "Severity",
    "Status",
]

# Extra fields available via --fields/--all-fields. Each key is both the CLI
# field name and the column header (title-cased with underscores as spaces).
# The value is a getter that extracts a display string from an Issue.
EXTRA_FIELDS: dict[str, t.Callable[["Issue"], t.Any]] = {
    "owner": lambda issue: issue.owner,
    "reporter": lambda issue: issue.reporter,
    "verifier": lambda issue: issue.verifier,
    "type": lambda issue: issue.issue_type.name if issue.issue_type else None,
    "component": lambda issue: str(issue.component_id) if issue.component_id else None,
    "tags": lambda issue: ", ".join(issue.component_tags) or None,
    "ancestor_tags": lambda issue: ", ".join(issue.component_ancestor_tags) or None,
    "labels": lambda issue: ", ".join(issue.labels) or None,
    "os": lambda issue: ", ".join(issue.os) or None,
    "milestone": lambda issue: ", ".join(issue.milestone) or None,
    "ccs": lambda issue: ", ".join(issue.ccs) or None,
    "hotlists": lambda issue: ", ".join(str(h) for h in issue.hotlist_ids) or None,
    "severity": lambda issue: (
        issue.severity.name if issue.severity is not None else None
    ),
    "collaborators": lambda issue: ", ".join(issue.collaborators) or None,
    "found_in": lambda issue: ", ".join(issue.found_in) or None,
    "in_prod": lambda issue: "Yes" if issue.in_prod else None,
    "blocking": lambda issue: ", ".join(str(b) for b in issue.blocking_issue_ids)
    or None,
    "duplicates": lambda issue: ", ".join(str(d) for d in issue.duplicate_issue_ids)
    or None,
    "cve": lambda issue: ", ".join(issue.cve) or None,
    "cwe": lambda issue: str(int(issue.cwe_id)) if issue.cwe_id is not None else None,
    "build": lambda issue: issue.build_number,
    "introduced_in": lambda issue: issue.introduced_in,
    "merge": lambda issue: ", ".join(issue.merge) or None,
    "merge_request": lambda issue: ", ".join(issue.merge_request) or None,
    "release_block": lambda issue: ", ".join(issue.release_block) or None,
    "notice": lambda issue: issue.notice,
    "flaky_test": lambda issue: issue.flaky_test,
    "est_days": lambda issue: (
        str(issue.estimated_days) if issue.estimated_days is not None else None
    ),
    "next_action": lambda issue: issue.next_action,
    "vrp_reward": lambda issue: (
        str(issue.vrp_reward) if issue.vrp_reward is not None else None
    ),
    "irm_link": lambda issue: issue.irm_link,
    "sec_release": lambda issue: ", ".join(issue.security_release) or None,
    "fixed_by": lambda issue: ", ".join(issue.fixed_by_code_changes) or None,
    "created": lambda issue: issue.created_at.isoformat() if issue.created_at else None,
    "modified": lambda issue: (
        issue.modified_at.isoformat() if issue.modified_at else None
    ),
    "verified": lambda issue: (
        issue.verified_at.isoformat() if issue.verified_at else None
    ),
    "comments": lambda issue: str(issue.comment_count),
    "stars": lambda issue: str(issue.star_count),
    "last_modifier": lambda issue: issue.last_modifier,
    "24h_views": lambda issue: str(issue.views_24h) if issue.views_24h else None,
    "7d_views": lambda issue: str(issue.views_7d) if issue.views_7d else None,
    "30d_views": lambda issue: str(issue.views_30d) if issue.views_30d else None,
}


class Status(enum.IntEnum):
    """
    Issue status values used by the Google Issue Tracker.

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
        """
        Whether this status represents an open (unresolved) issue.
        """
        return self in (Status.NEW, Status.ASSIGNED, Status.ACCEPTED)


class Priority(enum.IntEnum):
    """
    Issue priority levels. P0 is the most urgent, P4 is the lowest.

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


class Severity(enum.IntEnum):
    """
    Issue severity levels. S0 is the most severe, S4 is the lowest.

    Severity often matches priority but can diverge, especially on
    security issues. Unknown values from the API get an auto-generated SN name.
    """

    S0 = 0
    S1 = 1
    S2 = 2
    S3 = 3
    S4 = 4

    @classmethod
    def _missing_(cls, value):
        obj = int.__new__(cls, value)
        obj._name_ = f"S{value}"
        obj._value_ = value
        return obj


class IssueType(enum.IntEnum):
    """
    Issue type categories.

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
# Other trackers may use different field IDs; unrecognized fields go to custom_fields.
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
    """
    A single custom field value that didn't map to a known attribute.

    Attributes:
        field_id: Numeric ID of the custom field.
        name: Human-readable name (from CUSTOM_FIELD_IDS or "field_N").
        values: String values for multi-value fields.
        numeric_value: Numeric value for number-type fields.
    """

    field_id: int
    name: str
    values: list[str] = field(default_factory=list)
    numeric_value: float | None = None


@dataclass
class Issue:
    """
    A single issue from the Google Issue Tracker.

    Basic fields (id, title, status, priority, etc.) are always populated.
    Custom fields (os, milestone, cve, etc.) come from the tracker's
    configurable field system and may be empty.

    Attributes:
        id: Unique numeric issue ID.
        title: Issue title/summary.
        status: Current status (open, fixed, etc.).
        priority: Priority level (P0-P4).
        severity: Severity level (S0-S4). Often matches priority but can diverge.
        issue_type: Category (bug, feature request, etc.).
        reporter: Email of the person who filed the issue.
        owner: Email of the currently assigned owner.
        verifier: Email of the person who verified the fix.
        component_id: Numeric ID of the primary component.
        ccs: List of CC'd email addresses.
        collaborators: List of collaborator email addresses.
        found_in: "Found In" version strings (e.g. ["CP21.260116.011.A1"]).
        in_prod: Whether the issue has been observed in production.
        created_at: When the issue was created (UTC).
        modified_at: When the issue was last modified (UTC).
        verified_at: When the fix was verified (UTC).
        comment_count: Total number of comments.
        star_count: Number of stars (watchers/votes).
        body: Issue description text. Only populated in batch/detail responses, not in search results.
        tracker_id: Tracker ID (e.g. 157 for Chromium, 183 for Fuchsia).
        last_modifier: Email of the last person to modify the issue.
        hotlist_ids: IDs of hotlists this issue belongs to.
        blocking_issue_ids: IDs of issues this one blocks.
        duplicate_issue_ids: IDs of issues marked as duplicates of this one.
        views_24h: Number of views in the last 24 hours.
        views_7d: Number of views in the last 7 days.
        views_30d: Number of views in the last 30 days.
        component_tags: Component tags (e.g. ["Blink>JavaScript"]).
        component_ancestor_tags: Full component ancestry.
        labels: Tracker-specific labels.
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
    severity: Severity | None = None
    issue_type: IssueType | None = None
    reporter: str | None = None
    owner: str | None = None
    verifier: str | None = None
    component_id: int | None = None
    ccs: list[str] = field(default_factory=list)
    collaborators: list[str] = field(default_factory=list)
    found_in: list[str] = field(default_factory=list)
    in_prod: bool | None = None
    created_at: datetime | None = None
    modified_at: datetime | None = None
    verified_at: datetime | None = None
    comment_count: int = 0
    star_count: int = 0
    body: str | None = None
    tracker_id: int | None = None
    last_modifier: str | None = None
    hotlist_ids: list[int] = field(default_factory=list)
    blocking_issue_ids: list[int] = field(default_factory=list)
    duplicate_issue_ids: list[int] = field(default_factory=list)
    views_24h: int = 0
    views_7d: int = 0
    views_30d: int = 0
    component_tags: list[str] = field(default_factory=list)
    component_ancestor_tags: list[str] = field(default_factory=list)
    labels: list[str] = field(default_factory=list)
    os: list[str] = field(default_factory=list)
    milestone: list[str] = field(default_factory=list)
    merge: list[str] = field(default_factory=list)
    merge_request: list[str] = field(default_factory=list)
    release_block: list[str] = field(default_factory=list)
    cve: list[str] = field(default_factory=list)
    cwe_id: float | None = None
    vrp_reward: float | None = None
    estimated_days: float | None = None
    build_number: str | None = None
    flaky_test: str | None = None
    next_action: str | None = None
    notice: str | None = None
    introduced_in: str | None = None
    irm_link: str | None = None
    security_release: list[str] = field(default_factory=list)
    fixed_by_code_changes: list[str] = field(default_factory=list)
    custom_fields: dict[str, t.Any] = field(default_factory=dict)

    @property
    def url(self) -> str:
        """
        Direct link to this issue on issuetracker.google.com.
        """
        return f"https://issuetracker.google.com/issues/{self.id}"


@dataclass
class Comment:
    """
    A single comment on an issue.

    Attributes:
        issue_id: The issue this comment belongs to.
        comment_number: 1-indexed comment number.
        author: Email of the comment author.
        timestamp: When the comment was posted (UTC).
        body: The comment text.
    """

    issue_id: int
    comment_number: int
    author: str | None = None
    timestamp: datetime | None = None
    body: str = ""


@dataclass
class CommentsResult:
    """
    Result from fetching comments via the listComments endpoint.

    Attributes:
        comments: The comments for this page.
        total_count: Total number of text comments on this issue.
        next_page_token: Token for fetching the next page, if there are more.
    """

    comments: list[Comment]
    total_count: int
    next_page_token: str | None = None

    @property
    def has_more(self) -> bool:
        """
        Whether there are more comments beyond this page.
        """
        return self.next_page_token is not None


@dataclass
class FieldChange:
    """
    A single field change within an issue update.

    Attributes:
        field: Name of the changed field (e.g. "status", "priority").
        old_value: Previous value (not always available from the API).
        new_value: New value (not always available from the API).
    """

    field: str
    old_value: str | None = None
    new_value: str | None = None


@dataclass
class IssueUpdate:
    """
    An issue update entry. May contain a comment, field changes, or both.

    Attributes:
        issue_id: The issue this update belongs to.
        sequence_number: Ordering number for this update.
        author: Email of the person who made this update.
        timestamp: When the update happened (UTC).
        comment: The comment attached to this update, if any.
        field_changes: List of field changes in this update.
    """

    issue_id: int
    sequence_number: int | None = None
    author: str | None = None
    timestamp: datetime | None = None
    comment: Comment | None = None
    field_changes: list[FieldChange] = field(default_factory=list)


@dataclass
class IssueUpdatesResult:
    """
    Result from fetching issue updates (comments + field changes).

    The API returns updates in reverse chronological order (newest first).
    Use the .comments property to get just the comments in chronological order.

    Attributes:
        updates: All updates, newest first.
        total_count: Total number of updates for this issue.
        next_page_token: Token for fetching the next page, if there are more.
    """

    updates: list[IssueUpdate]
    total_count: int
    next_page_token: str | None = None

    @property
    def comments(self) -> list[Comment]:
        """
        Only the updates that have comments, in chronological order (oldest first).
        """
        return [u.comment for u in reversed(self.updates) if u.comment is not None]

    @property
    def has_more(self) -> bool:
        """
        Whether there are more updates beyond this page.
        """
        return self.next_page_token is not None


@dataclass
class SearchResult:
    """
    Result from searching/listing issues.

    Attributes:
        issues: The matching issues for this page.
        total_count: Total number of matching issues (across all pages).
        next_page_token: Token for fetching the next page, if there are more.
        query: The query string used for this search (stored for pagination).
        page_size: The page size used for this search (stored for pagination).
    """

    issues: list[Issue]
    total_count: int
    next_page_token: str | None = None
    query: str = ""
    page_size: int = 50

    @property
    def has_more(self) -> bool:
        """
        Whether there are more results beyond this page.
        """
        return self.next_page_token is not None
