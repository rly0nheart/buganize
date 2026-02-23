from __future__ import annotations

import csv
import json
import typing as t
from datetime import datetime

from rich import box
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
    "blocking": lambda issue: ", ".join(str(b) for b in issue.blocking_issue_ids)
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
    "7d_views": lambda issue: str(issue.views_7d) if issue.views_7d else None,
}


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


def _column_header(key: str) -> str:
    """
    Derive a column header from a field key.

    :param key: The field key (e.g. ``"merge_request"``).
    :return: Title-cased header (e.g. ``"Merge Request"``).
    """

    return key.replace("_", " ").title()


class Table:
    """
    Renders issues or comments as Rich tables to the console.

    :param items: List of :class:`Issue` or :class:`Comment` objects.
    """

    def __init__(self, items: t.Union[list[Issue], list[Comment]]):
        self.items = items

    @staticmethod
    def make_table(
            columns: list[tuple[str, dict[str, t.Any]]],
    ) -> Table:
        """
        Create a Rich table with the given columns and keyword arguments.

        :param columns: List of ``(header, column_kwargs)`` tuples.
        :return: A configured Rich table ready for rows.
        """

        table = RichTable(box=box.MINIMAL, highlight=True, expand=True)

        for header, col_kwargs in columns:
            table.add_column(header, **col_kwargs)

        return table

    def print(self, fields: t.Optional[list[str]] = None):
        """
        Print items as a Rich table, dispatching to :meth:`issues` or
        :meth:`comments` based on item type.

        :param fields: Extra field names to include as columns (issues only).
        """

        if not self.items:
            return

        if all(isinstance(item, Issue) for item in self.items):
            self.issues(fields=fields)
        elif all(isinstance(item, Comment) for item in self.items):
            self.comments()

    def issues(self, fields: t.Optional[list[str]] = None):
        """
        Print issues as a Rich table.

        :param fields: Extra field names to include as columns.
        """

        extra = fields or []
        extra_columns = [(_column_header(f), {}) for f in extra if f in EXTRA_FIELDS]
        table = self.make_table(
            columns=[
                ("#", {"justify": "right"}),
                ("P", {}),
                ("ID", {"justify": "right"}),
                ("Type", {}),
                ("Title", {"overflow": "fold"}),
                ("Status", {}),
                ("Modified", {"justify": "right"}),
                *extra_columns,
            ],
        )

        for index, issue in enumerate(self.items, start=1):
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

        table = self.make_table(
            columns=[
                ("#", {"style": "cyan", "no_wrap": True}),
                ("Author", {"style": "bold"}),
                ("Date", {"no_wrap": True}),
                ("Body", {}),
            ],
        )

        for comment in self.items:
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
