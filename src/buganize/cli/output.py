import csv
import html
import json
import typing as t
from contextlib import nullcontext
from datetime import datetime

from rich import box
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table

from .console import console
from .symbols import OK, WARN
from ..api.models import Comment, EXTRA_FIELDS, Issue

__all__ = ["print_trackers", "print_and_export"]


def _comment_date(comment: Comment) -> str:
    """
    Format a comment's date in the local timezone and locale.

    Prefers the creation time, falling back to the last-modified timestamp.
    ``astimezone()`` (no arg) converts the UTC value to the system's local
    zone; ``%x %X`` renders it using the locale's date/time format.

    :param comment: The comment to format.
    :return: Locale-formatted local date/time, or "" if no timestamp.
    """

    when = comment.created_at or comment.timestamp
    return when.astimezone().strftime("%x %X") if when else ""


def _column_header(key: str) -> str:
    """
    Derive a column header from a field key.

    :param key: The field key (e.g. ``"merge_request"``).
    :return: Title-cased header (e.g. ``"Merge Request"``).
    """

    return key.replace("_", " ").title()


def _make_table(
        columns: list[tuple[str, dict[str, t.Any]]], expand: bool = False
) -> Table:
    """
    Create a Rich table with the given columns.

    :param columns: List of ``(header, column_kwargs)`` tuples.
    :param expand: Whether the table should expand to fill the terminal width.
    :return: A configured Rich table ready for rows.
    """

    table = Table(box=box.SIMPLE, highlight=True, expand=expand)

    for header, col_kwargs in columns:
        table.add_column(header, **col_kwargs)

    return table


def print_trackers(trackers: list[dict[str, str | int]]):
    """
    Print available trackers as a Rich table.

    :param trackers: The ``TRACKERS`` list from :mod:`buganize.api.client`.
    """

    table = _make_table(
        columns=[
            ("#", {"style": "dim", "justify": "right"}),
            ("ID", {"style": "cyan", "justify": "right"}),
            ("Name", {"style": "bold"}),
            ("URL", {}),
        ],
    )

    for index, tracker in enumerate(trackers, start=1):
        table.add_row(
            str(index),
            str(tracker["id"]),
            str(tracker["name"]),
            str(tracker["url"]),
        )

    console.print(table)
    console.print(f"\n{len(trackers)} trackers available")


def print_and_export(
        output: list[Issue] | list[Comment] | Issue,
        formats: list[str] | None = None,
        fields: list[str] | None = None,
):
    """
    Print data to the console and optionally export to file.

    :param output: Issues, comments, or a single issue to display.
    :param formats: Export format strings (e.g. ``["csv", "json"]``), or ``None`` to skip.
    :param fields: Extra field names to include (issues only).
    """

    PrintOutput(output=output).print(fields=fields)

    if formats:
        items = [output] if not isinstance(output, list) else output
        rows = FormatOutput(items=items).to_rows(fields=fields)
        SaveOutput(rows=rows).save(formats=formats)


class SaveOutput:
    """
    Handles exporting row data to CSV, JSON, and HTML files.

    :param rows: List of dicts representing table rows.
    """

    def __init__(self, rows: list[dict[str, t.Any]]):
        self.rows = rows

    def save(self, formats: list[str]):
        """
        Write rows to timestamped files in the specified formats.

        :param formats: List of format strings, each one of ``"csv"``, ``"json"``, or ``"html"``.
        """

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        for fmt in formats:
            path = f"buganize-{timestamp}.{fmt}"
            if fmt == "csv":
                self.to_csv(self.rows, path)
            elif fmt == "json":
                self.to_json(self.rows, path)
            elif fmt == "html":
                self.to_html(self.rows, path)

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
        console.print(f"\n{OK} CSV exported to {path}")

    @staticmethod
    def to_json(rows: list[dict[str, t.Any]], path: str):
        """
        Write rows as JSON to a file.

        :param rows: List of dicts to export.
        :param path: Output file path.
        """

        with open(path, "w") as file:
            json.dump(rows, file, indent=4, default=str)
        console.print(f"\n{OK} JSON exported to {path}")

    @staticmethod
    def to_html(rows: list[dict[str, t.Any]], path: str):
        """
        Write rows as an HTML table to a file.

        :param rows: List of dicts to export.
        :param path: Output file path.
        """

        if not rows:
            return

        headers = list(rows[0].keys())
        lines = [
            "<!DOCTYPE html>",
            "<html><head>",
            '<meta charset="utf-8">',
            "<title>buganize export</title>",
            "<style>",
            "  table { border-collapse: collapse; width: 100%; }",
            "  th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }",
            "  th { background-color: #f2f2f2; }",
            "  tr:nth-child(even) { background-color: #fafafa; }",
            "</style>",
            "</head><body>",
            "<table>",
            "<thead><tr>",
            "  <th>#</th>",
        ]
        for header in headers:
            lines.append(f"  <th>{html.escape(str(header))}</th>")
        lines.append("</tr></thead>")
        lines.append("<tbody>")
        for index, row in enumerate(rows, start=1):
            lines.append("<tr>")
            lines.append(f"  <td>{index}</td>")
            for header in headers:
                value = row.get(header, "")
                lines.append(f"  <td>{html.escape(str(value))}</td>")
            lines.append("</tr>")
        lines.append("</tbody>")
        lines.append("</table>")
        lines.append("</body></html>")

        with open(path, "w") as file:
            file.write("\n".join(lines))
        console.print(f"\n{OK} HTML exported to {path}")


class FormatOutput:
    """
    Converts issues or comments into serialisable row dicts for export.

    Delegates to :class:`Convert` for the actual conversion logic.

    :param items: List of :class:`Issue` or :class:`Comment` objects.
    """

    def __init__(self, items: list[Issue] | list[Comment]):
        self.items = items

    def to_rows(
            self,
            fields: list[str] | None = None,
    ) -> list[dict[str, t.Any]]:
        """
        Convert the items into a list of row dicts.

        :param fields: Extra field names to include (issues only).
        :return: List of dicts with one entry per item.
        """

        if not self.items:
            return []

        return ConvertOutput(items=self.items, fields=fields).to_dict()


class PrintOutput:
    """
    Renders issues or comments as Rich tables to the console.

    Dispatches to the appropriate rendering method based on the data type:

    - ``list[Issue]`` → :meth:`issues` (multi-issue table)
    - ``Issue`` → :meth:`issue` (single-issue detail view)
    - ``list[Comment]`` → :meth:`comments` (comment table)

    :param output: The output to render. Accepted types are a list of issues,
        a single issue, or a list of comments.
    """

    def __init__(self, output: list[Issue] | list[Comment] | Issue):
        self.output = output

    def print(self, fields: list[str] | None = None):
        """
        Print data as a Rich table, dispatching based on data type.

        Routes to :meth:`issue` for a single Issue, :meth:`issues` for a list
        of issues, or :meth:`comments` for a list of comments. For tracker
        data, use :meth:`trackers` directly instead.

        :param fields: Extra field names to include as columns (issues only).
        """

        if not self.output:
            return

        context = nullcontext()
        if console.is_terminal:
            context = console.pager(styles=True)
        else:
            console.print(f"{WARN} Not a TTY — output won't be paged.")

        with context:
            if isinstance(self.output, Issue):
                self.issue(fields=fields)
            elif all(isinstance(item, Issue) for item in self.output):
                self.issues(fields=fields)
            elif all(isinstance(item, Comment) for item in self.output):
                self.comments()

    def issue(self, fields: list[str] | None = None):
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

        if isinstance(self.output, Issue):
            # Basic fields (always shown).
            console.print(f"\nIssue #{self.output.id}")
            console.print(f"  URL:           {self.output.url}")
            console.print(f"  Title:         {self.output.title}")
            console.print(f"  Status:        {self.output.status.name}")
            console.print(f"  Priority:      {self.output.priority.name}")
            if self.output.severity is not None:
                console.print(f"  Severity:      {self.output.severity.name}")
            if self.output.issue_type:
                console.print(f"  Type:          {self.output.issue_type.name}")
            if self.output.reporter:
                console.print(f"  Reporter:      {self.output.reporter}")
            if self.output.owner:
                console.print(f"  Owner:         {self.output.owner}")
            if self.output.component_id:
                console.print(f"  Component:     {self.output.component_id}")
            if self.output.created_at:
                console.print(f"  Created:       {self.output.created_at.isoformat()}")
            if self.output.modified_at:
                console.print(f"  Modified:      {self.output.modified_at.isoformat()}")
            if is_shown("last_activity") and self.output.last_activity_at:
                console.print(
                    f"  Last Activity: {self.output.last_activity_at.isoformat()}"
                )
            console.print(f"  Comments:      {self.output.comment_count}")
            if self.output.body:
                console.print()
                console.print(
                    Panel(
                        Markdown(self.output.body),
                        title="Description",
                        border_style="dim",
                    )
                )

            # Extra fields (only when requested).
            if is_shown("verifier") and self.output.verifier:
                console.print(f"  Verifier:      {self.output.verifier}")
            if is_shown("tags") and self.output.component_tags:
                console.print(
                    f"  Comp. Tags:    {', '.join(self.output.component_tags)}"
                )
            if is_shown("ancestor_tags") and self.output.component_ancestor_tags:
                console.print(
                    f"  Ancestor Tags: {', '.join(self.output.component_ancestor_tags)}"
                )
            if is_shown("labels") and self.output.labels:
                console.print(f"  Labels:        {', '.join(self.output.labels)}")
            if is_shown("os") and self.output.os:
                console.print(f"  OS:            {', '.join(self.output.os)}")
            if is_shown("milestone") and self.output.milestone:
                console.print(f"  Milestone:     {', '.join(self.output.milestone)}")
            if is_shown("ccs") and self.output.ccs:
                console.print(f"  CCs:           {', '.join(self.output.ccs)}")
            if is_shown("hotlists") and self.output.hotlist_ids:
                console.print(
                    f"  Hotlists:      {', '.join(str(h) for h in self.output.hotlist_ids)}"
                )
            if is_shown("collaborators") and self.output.collaborators:
                console.print(
                    f"  Collaborators: {', '.join(self.output.collaborators)}"
                )
            if is_shown("found_in") and self.output.found_in:
                console.print(f"  Found In:      {', '.join(self.output.found_in)}")
            if is_shown("in_prod") and self.output.in_prod:
                console.print("  In Prod:       Yes")
            if is_shown("blocking") and self.output.blocking_issue_ids:
                console.print(
                    f"  Blocking:      {', '.join(str(b) for b in self.output.blocking_issue_ids)}"
                )
            if is_shown("duplicates") and self.output.duplicate_issue_ids:
                console.print(
                    f"  Duplicates:    {', '.join(str(d) for d in self.output.duplicate_issue_ids)}"
                )
            if is_shown("cve") and self.output.cve:
                console.print(f"  CVE:           {', '.join(self.output.cve)}")
            if is_shown("cwe") and self.output.cwe_id is not None:
                console.print(f"  CWE ID:        {int(self.output.cwe_id)}")
            if is_shown("build") and self.output.build_number:
                console.print(f"  Build:         {self.output.build_number}")
            if is_shown("introduced_in") and self.output.introduced_in:
                console.print(f"  Introduced In: {self.output.introduced_in}")
            if is_shown("merge") and self.output.merge:
                console.print(f"  Merge:         {', '.join(self.output.merge)}")
            if is_shown("merge_request") and self.output.merge_request:
                console.print(
                    f"  Merge Req.:    {', '.join(self.output.merge_request)}"
                )
            if is_shown("release_block") and self.output.release_block:
                console.print(
                    f"  Release Block: {', '.join(self.output.release_block)}"
                )
            if is_shown("notice") and self.output.notice:
                console.print(f"  Notice:        {self.output.notice}")
            if is_shown("flaky_test") and self.output.flaky_test:
                console.print(f"  Flaky Test:    {self.output.flaky_test}")
            if is_shown("est_days") and self.output.estimated_days is not None:
                console.print(f"  Est. Days:     {self.output.estimated_days}")
            if is_shown("next_action") and self.output.next_action:
                console.print(f"  Next Action:   {self.output.next_action}")
            if is_shown("vrp_reward") and self.output.vrp_reward is not None:
                console.print(f"  VRP Reward:    {self.output.vrp_reward}")
            if is_shown("irm_link") and self.output.irm_link:
                console.print(f"  IRM Link:      {self.output.irm_link}")
            if is_shown("sec_release") and self.output.security_release:
                console.print(
                    f"  Sec. Release:  {', '.join(self.output.security_release)}"
                )
            if is_shown("fixed_by") and self.output.fixed_by_code_changes:
                console.print(
                    f"  Fixed By:      {', '.join(self.output.fixed_by_code_changes)}"
                )
            if is_shown("verified") and self.output.verified_at:
                console.print(f"  Verified:      {self.output.verified_at.isoformat()}")
            if is_shown("stars"):
                console.print(f"  Stars:         {self.output.star_count}")
            if is_shown("last_modifier") and self.output.last_modifier:
                console.print(f"  Last Modifier: {self.output.last_modifier}")
            if is_shown("24h_views") and self.output.views_24h:
                console.print(f"  24h Views:     {self.output.views_24h}")
            if is_shown("7d_views") and self.output.views_7d:
                console.print(f"  7d Views:      {self.output.views_7d}")
            if is_shown("30d_views") and self.output.views_30d:
                console.print(f"  30d Views:     {self.output.views_30d}")
            if all_fields and self.output.custom_fields:
                console.print("  Other Fields:")
                for key, value in self.output.custom_fields.items():
                    console.print(f"    {key}: {value}")
        else:
            raise TypeError(f"Output is not of type {Issue.__name__}")

    def issues(self, fields: list[str] | None = None):
        """
        Print issues as a Rich table.

        :param fields: Extra field names to include as columns.
        """

        if isinstance(self.output, list) and all(
                isinstance(issue, Issue) for issue in self.output
        ):

            extra = fields or []
            extra_columns = [
                (_column_header(key=field), {})
                for field in extra
                if field in EXTRA_FIELDS
            ]
            table = _make_table(
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

            for index, issue in enumerate(
                    t.cast(list[Issue], self.output), start=1
            ):
                row = [
                    str(index),
                    issue.priority.name,
                    str(issue.id),
                    issue.issue_type.name,  # if issue.issue_type else "",
                    issue.title,
                    issue.status.name.lower(),
                    issue.modified_at.strftime(
                        "%x %X"
                    ),  # if issue.modified_at else "",
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

        table = _make_table(
            columns=[
                ("#", {"style": "cyan", "no_wrap": True}),
                ("Author", {"style": "bold"}),
                ("Date", {"no_wrap": True}),
                ("Body", {}),
            ],
            expand=True,
        )

        for comment in t.cast(list[Comment], self.output):
            author = comment.author or "unknown"
            if comment.is_edited:
                author = f"{author} (edited)"
            table.add_row(
                str(comment.comment_number),
                author,
                _comment_date(comment),
                comment.body,
            )

        console.print(table)


class ConvertOutput:
    """
    Converts issues or comments into plain dicts.

    :param items: List of :class:`Issue` or :class:`Comment` objects.
    :param fields: Extra field names to include (issues only).
    """

    def __init__(
            self,
            items: list[Issue] | list[Comment],
            fields: list[str] | None = None,
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

    def issues(self, fields: list[str] | None = None) -> list[dict[str, t.Any]]:
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
                    row[_column_header(key=field_name)] = getter(issue) or ""
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
                    "Date": _comment_date(comment),
                    "Body": comment.body,
                    "Last Editor": comment.last_editor or "",
                    "Edited": comment.is_edited,
                }
            )
        return rows
