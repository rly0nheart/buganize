from __future__ import annotations

import csv
import json
import typing as t
from datetime import datetime

from rich import box
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table as RichTable

from ..api.models import Comment, Issue
from ..cli import console

# Extra fields available via --fields/--all-fields. Each key is both the CLI
# field name and the column header (title-cased with underscores as spaces).
# The value is a getter that extracts a display string from an Issue.
EXTRA_FIELDS: dict[str, t.Callable[[Issue], t.Any]] = {
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


def _column_header(key: str) -> str:
    """
    Derive a column header from a field key.

    :param key: The field key (e.g. ``"merge_request"``).
    :return: Title-cased header (e.g. ``"Merge Request"``).
    """

    return key.replace("_", " ").title()


class Save:
    """
    Handles exporting row data to CSV and JSON files.

    :param rows: List of dicts representing table rows.
    """

    def __init__(self, rows: list[dict[str, t.Any]]):
        self.rows = rows

    def save(self, formats: list[str]):
        """
        Write rows to timestamped files in the specified formats.

        :param formats: List of format strings, each one of ``"csv"`` or ``"json"``.
        """

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        for fmt in formats:
            path = f"buganize-{timestamp}.{fmt}"
            if fmt == "csv":
                self.to_csv(self.rows, path)
            elif fmt == "json":
                self.to_json(self.rows, path)

    @staticmethod
    def to_csv(rows: list[dict[str, t.Any]], path: str):
        """
        Write rows as CSV to a file.

        :param rows: List of dicts to export.
        :param path: Output file path.
        """

        if not rows:
            return
        with open(path, "w", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows(rows)
        console.print(f"[bold green]✔[/bold green] CSV exported to {path}")

    @staticmethod
    def to_json(rows: list[dict[str, t.Any]], path: str):
        """
        Write rows as JSON to a file.

        :param rows: List of dicts to export.
        :param path: Output file path.
        """

        with open(path, "w") as file:
            json.dump(rows, file, indent=4, default=str)
        console.print(f"[bold green]✔[/bold green] JSON exported to {path}")


class Format:
    """
    Converts issues or comments into serialisable row dicts for export.

    Delegates to :class:`Convert` for the actual conversion logic.

    :param items: List of :class:`Issue` or :class:`Comment` objects.
    """

    def __init__(self, items: t.Union[list[Issue], list[Comment]]):
        self.items = items

    def to_rows(
        self,
        fields: t.Optional[list[str]] = None,
    ) -> list[dict[str, t.Any]]:
        """
        Convert the items into a list of row dicts.

        :param fields: Extra field names to include (issues only).
        :return: List of dicts with one entry per item.
        """

        if not self.items:
            return []

        return Convert(items=self.items, fields=fields).to_dict()


class Print:
    """
    Renders issues, comments, or tracker info as Rich tables to the console.

    Dispatches to the appropriate rendering method based on the data type:

    - ``list[Issue]`` → :meth:`issues` (multi-issue table)
    - ``Issue`` → :meth:`issue` (single-issue detail view)
    - ``list[Comment]`` → :meth:`comments` (comment table)
    - ``dict[str, tuple[str, str]]`` → :meth:`trackers` (tracker listing)

    :param data: The data to render. Accepted types are a list of issues,
        a single issue, a list of comments, or the ``TRACKER_NAMES`` dict.
    """

    def __init__(
        self, data: t.Union[list[Issue], list[Comment], Issue, dict[str, tuple]]
    ):
        self.data = data

    @staticmethod
    def _make_table(
        columns: list[tuple[str, dict[str, t.Any]]], expand: bool = False
    ) -> RichTable:
        """
        Create a Rich table with the given columns.

        :param columns: List of ``(header, column_kwargs)`` tuples.
        :param expand: Whether the table should expand to fill the terminal width.
        :return: A configured Rich table ready for rows.
        """

        table = RichTable(box=box.ASCII, highlight=True, expand=expand)

        for header, col_kwargs in columns:
            table.add_column(header, **col_kwargs)

        return table

    def print(self, fields: t.Optional[list[str]] = None):
        """
        Print data as a Rich table, dispatching based on data type.

        Routes to :meth:`issue` for a single Issue, :meth:`issues` for a list
        of issues, or :meth:`comments` for a list of comments. For tracker
        data, use :meth:`trackers` directly instead.

        :param fields: Extra field names to include as columns (issues only).
        """

        if not self.data:
            return

        if isinstance(self.data, Issue):
            self.issue(fields=fields)
        elif all(isinstance(item, Issue) for item in self.data):
            self.issues(fields=fields)
        elif all(isinstance(item, Comment) for item in self.data):
            self.comments()

    def issue(self, fields: t.Optional[list[str]] = None):
        """
        Print a single issue with full detail.

        Always shows the basic fields. Extra fields are shown only when
        requested via --fields or --all-fields.

        :param fields: Extra field names to include.
        """

        enabled_fields = set(fields or [])
        all_fields = bool(enabled_fields)

        def is_shown(field_name: str) -> bool:
            return all_fields or field_name in enabled_fields

        # Basic fields (always shown).
        console.print(f"\nIssue #{self.data.id}")
        console.print(f"  URL:           {self.data.url}")
        console.print(f"  Title:         {self.data.title}")
        console.print(f"  Status:        {self.data.status.name}")
        console.print(f"  Priority:      {self.data.priority.name}")
        if self.data.severity is not None:
            console.print(f"  Severity:      {self.data.severity.name}")
        if self.data.issue_type:
            console.print(f"  Type:          {self.data.issue_type.name}")
        if self.data.reporter:
            console.print(f"  Reporter:      {self.data.reporter}")
        if self.data.owner:
            console.print(f"  Owner:         {self.data.owner}")
        if self.data.component_id:
            console.print(f"  Component:     {self.data.component_id}")
        if self.data.created_at:
            console.print(f"  Created:       {self.data.created_at.isoformat()}")
        if self.data.modified_at:
            console.print(f"  Modified:      {self.data.modified_at.isoformat()}")
        console.print(f"  Comments:      {self.data.comment_count}")
        if self.data.body:
            console.print()
            console.print(
                Panel(Markdown(self.data.body), title="Description", border_style="dim")
            )

        # Extra fields (only when requested).
        if is_shown("verifier") and self.data.verifier:
            console.print(f"  Verifier:      {self.data.verifier}")
        if is_shown("tags") and self.data.component_tags:
            console.print(f"  Comp. Tags:    {', '.join(self.data.component_tags)}")
        if is_shown("ancestor_tags") and self.data.component_ancestor_tags:
            console.print(
                f"  Ancestor Tags: {', '.join(self.data.component_ancestor_tags)}"
            )
        if is_shown("labels") and self.data.labels:
            console.print(f"  Labels:        {', '.join(self.data.labels)}")
        if is_shown("os") and self.data.os:
            console.print(f"  OS:            {', '.join(self.data.os)}")
        if is_shown("milestone") and self.data.milestone:
            console.print(f"  Milestone:     {', '.join(self.data.milestone)}")
        if is_shown("ccs") and self.data.ccs:
            console.print(f"  CCs:           {', '.join(self.data.ccs)}")
        if is_shown("hotlists") and self.data.hotlist_ids:
            console.print(
                f"  Hotlists:      {', '.join(str(h) for h in self.data.hotlist_ids)}"
            )
        if is_shown("collaborators") and self.data.collaborators:
            console.print(f"  Collaborators: {', '.join(self.data.collaborators)}")
        if is_shown("found_in") and self.data.found_in:
            console.print(f"  Found In:      {', '.join(self.data.found_in)}")
        if is_shown("in_prod") and self.data.in_prod:
            console.print(f"  In Prod:       Yes")
        if is_shown("blocking") and self.data.blocking_issue_ids:
            console.print(
                f"  Blocking:      {', '.join(str(b) for b in self.data.blocking_issue_ids)}"
            )
        if is_shown("duplicates") and self.data.duplicate_issue_ids:
            console.print(
                f"  Duplicates:    {', '.join(str(d) for d in self.data.duplicate_issue_ids)}"
            )
        if is_shown("cve") and self.data.cve:
            console.print(f"  CVE:           {', '.join(self.data.cve)}")
        if is_shown("cwe") and self.data.cwe_id is not None:
            console.print(f"  CWE ID:        {int(self.data.cwe_id)}")
        if is_shown("build") and self.data.build_number:
            console.print(f"  Build:         {self.data.build_number}")
        if is_shown("introduced_in") and self.data.introduced_in:
            console.print(f"  Introduced In: {self.data.introduced_in}")
        if is_shown("merge") and self.data.merge:
            console.print(f"  Merge:         {', '.join(self.data.merge)}")
        if is_shown("merge_request") and self.data.merge_request:
            console.print(f"  Merge Req.:    {', '.join(self.data.merge_request)}")
        if is_shown("release_block") and self.data.release_block:
            console.print(f"  Release Block: {', '.join(self.data.release_block)}")
        if is_shown("notice") and self.data.notice:
            console.print(f"  Notice:        {self.data.notice}")
        if is_shown("flaky_test") and self.data.flaky_test:
            console.print(f"  Flaky Test:    {self.data.flaky_test}")
        if is_shown("est_days") and self.data.estimated_days is not None:
            console.print(f"  Est. Days:     {self.data.estimated_days}")
        if is_shown("next_action") and self.data.next_action:
            console.print(f"  Next Action:   {self.data.next_action}")
        if is_shown("vrp_reward") and self.data.vrp_reward is not None:
            console.print(f"  VRP Reward:    {self.data.vrp_reward}")
        if is_shown("irm_link") and self.data.irm_link:
            console.print(f"  IRM Link:      {self.data.irm_link}")
        if is_shown("sec_release") and self.data.security_release:
            console.print(f"  Sec. Release:  {', '.join(self.data.security_release)}")
        if is_shown("fixed_by") and self.data.fixed_by_code_changes:
            console.print(
                f"  Fixed By:      {', '.join(self.data.fixed_by_code_changes)}"
            )
        if is_shown("verified") and self.data.verified_at:
            console.print(f"  Verified:      {self.data.verified_at.isoformat()}")
        if is_shown("stars"):
            console.print(f"  Stars:         {self.data.star_count}")
        if is_shown("last_modifier") and self.data.last_modifier:
            console.print(f"  Last Modifier: {self.data.last_modifier}")
        if is_shown("24h_views") and self.data.views_24h:
            console.print(f"  24h Views:     {self.data.views_24h}")
        if is_shown("7d_views") and self.data.views_7d:
            console.print(f"  7d Views:      {self.data.views_7d}")
        if is_shown("30d_views") and self.data.views_30d:
            console.print(f"  30d Views:     {self.data.views_30d}")
        if all_fields and self.data.custom_fields:
            console.print(f"  Other Fields:")
            for key, value in self.data.custom_fields.items():
                console.print(f"    {key}: {value}")

    def trackers(self):
        """
        Print available trackers as a Rich table with ID, name, and URL columns.

        Expects ``self.data`` to be the ``TRACKER_NAMES`` dict
        (``dict[str, tuple[str, str]]``) mapping tracker names to ``(id, url)`` tuples.
        """

        table = self._make_table(
            columns=[
                ("ID", {"style": "cyan", "justify": "right"}),
                ("Name", {"style": "bold"}),
                ("URL", {}),
            ],
        )
        for name, (tid, url) in self.data.items():
            table.add_row(tid, name, url)
        console.print(table)

    def issues(self, fields: t.Optional[list[str]] = None):
        """
        Print issues as a Rich table.

        :param fields: Extra field names to include as columns.
        """

        extra = fields or []
        extra_columns = [(_column_header(f), {}) for f in extra if f in EXTRA_FIELDS]
        table = self._make_table(
            columns=[
                ("#", {"justify": "right"}),
                ("Priority", {}),
                ("ID", {"justify": "right"}),
                ("Type", {}),
                ("Title", {"overflow": "fold"}),
                ("Status", {}),
                ("Modified", {"justify": "right"}),
                *extra_columns,
            ],
            expand=True,
        )

        for index, issue in enumerate(self.data, start=1):
            row = [
                str(index),
                issue.priority.name,
                str(issue.id),
                issue.issue_type.name,  # if issue.issue_type else "",
                issue.title,
                issue.status.name.lower(),
                issue.modified_at.strftime("%x %X"),  # if issue.modified_at else "",
            ]
            for field_name in extra:
                if field_name in EXTRA_FIELDS:
                    getter = EXTRA_FIELDS[field_name]
                    row.append(str(getter(issue) or ""))
            table.add_row(*row)

        console.print(table)

    def comments(self):
        """
        Print comments as a Rich table.
        """

        table = self._make_table(
            columns=[
                ("#", {"style": "cyan", "no_wrap": True}),
                ("Author", {"style": "bold"}),
                ("Date", {"no_wrap": True}),
                ("Body", {}),
            ],
            expand=True,
        )

        for comment in self.data:
            table.add_row(
                str(comment.comment_number),
                comment.author or "unknown",
                (
                    comment.timestamp.strftime("%Y-%m-%d %H:%M UTC")
                    if comment.timestamp
                    else ""
                ),
                comment.body,
            )

        console.print(table)


class Convert:
    """
    Converts issues or comments into plain dicts.

    :param items: List of :class:`Issue` or :class:`Comment` objects.
    :param fields: Extra field names to include (issues only).
    """

    def __init__(
        self,
        items: t.Union[list[Issue], list[Comment]],
        fields: t.Optional[list[str]] = None,
    ):
        self.items = items
        self.fields = fields

    def to_dict(self) -> list[dict[str, t.Any]]:
        """
        Convert items to a list of dicts, dispatching to :meth:`issues` or
        :meth:`comments` based on item type.

        :return: List of dicts with one entry per item, or empty list if
            the item type is unrecognised.
        """

        if not self.items:
            return []

        if all(isinstance(item, Issue) for item in self.items):
            return self.issues(fields=self.fields)
        elif all(isinstance(item, Comment) for item in self.items):
            return self.comments()

        return []

    def issues(self, fields: t.Optional[list[str]] = None) -> list[dict[str, t.Any]]:
        """
        Build a list of row dicts from issues.

        :param fields: Extra field names to include.
        :return: List of dicts with one entry per issue.
        """

        rows = []
        for issue in self.items:
            row: dict[str, t.Any] = {
                "P": issue.priority.name,
                "ID": issue.id,
                "Type": issue.issue_type.name if issue.issue_type else "",
                "Title": issue.title,
                "Status": issue.status.name.lower(),
                "Last Modified": (
                    issue.modified_at.isoformat() if issue.modified_at else ""
                ),
            }
            for field_name in fields or []:
                if field_name in EXTRA_FIELDS:
                    getter = EXTRA_FIELDS[field_name]
                    row[_column_header(field_name)] = getter(issue) or ""
            rows.append(row)
        return rows

    def comments(self) -> list[dict[str, t.Any]]:
        """
        Build a list of row dicts from comments.

        :return: List of dicts with one entry per comment.
        """

        rows = []
        for comment in self.items:
            rows.append(
                {
                    "#": comment.comment_number,
                    "Author": comment.author or "unknown",
                    "Date": (
                        comment.timestamp.strftime("%x %X") if comment.timestamp else ""
                    ),
                    "Body": comment.body,
                }
            )
        return rows
