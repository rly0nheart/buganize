"""
Console output for the CLI.

Results print as their dataclasses through a pager, so bulk output scrolls
instead of flooding the terminal. Writing them to file is left to the models'
own ``to_json()``/``to_csv()``.
"""

import enum
import typing as t
from contextlib import nullcontext
from datetime import datetime

from rich.box import MARKDOWN
from rich.pretty import Pretty
from rich.table import Table
from rich.text import Text

from ..api.models import (
    Exportable,
    Issue,
    IssueType,
    Priority,
    Results,
    Severity,
    Status,
)
from .console import console
from .symbols import OK, WARN

__all__ = ["export", "pretty_print"]

#: Style for values the API sent that the enum doesn't define (e.g. ``TYPE_7``).
UNKNOWN_STYLE = "magenta"

#: Priority cell styles. Other known values (P3, P4) are plain yellow.
PRIORITY_STYLES = {
    Priority.P0: "bold red",
    Priority.P1: "red",
    Priority.P2: "bold yellow",
}

#: Severity cell styles. Other known values (S3, S4) are plain yellow.
SEVERITY_STYLES = {
    Severity.S0: "bold red",
    Severity.S1: "red",
    Severity.S2: "bold yellow",
}

#: Issue type cell styles. Other known values (INTERNAL_CLEANUP, PROCESS) are unstyled.
ISSUE_TYPE_STYLES = {
    IssueType.VULNERABILITY: "bold red",
    IssueType.BUG: "red",
    IssueType.CUSTOMER_ISSUE: "bold yellow",
    IssueType.FEATURE_REQUEST: "bold green",
}

#: Status cell styles. Open statuses are blue, fixed ones green. Other closed
#: statuses (NOT_REPRODUCIBLE, INTENDED_BEHAVIOR, OBSOLETE, INFEASIBLE, DUPLICATE)
#: are dim.
STATUS_STYLES = {
    Status.NEW: "bold blue",
    Status.ASSIGNED: "cyan",
    Status.ACCEPTED: "bold cyan",
    Status.FIXED: "green",
    Status.VERIFIED: "bold green",
}


def _style_cell(value: enum.Enum | None, styles: dict, default: str = "") -> Text | str:
    """
    Build a table cell for an enum value, styled by its member.

    :param value: The enum value, or None when the issue has none.
    :param styles: Style per known member.
    :param default: Style for known members missing from ``styles``.
    :return: The styled name, or an empty string for None.
    """

    if value is None:
        return ""
    if value.name not in type(value).__members__:
        return Text(value.name, style=UNKNOWN_STYLE)
    return Text(value.name, style=styles.get(value, default))


def pretty_print(output: t.Any):
    """
    Show a result, paging it.

    :param output: A single item, or a list of them.
    """

    if not output:
        console.log("No results.")
        return

    context = console.pager(styles=True) if console.is_terminal else nullcontext()
    if not console.is_terminal:
        console.print(f"{WARN} Not a TTY — output won't be paged.")

    with context:
        if isinstance(output, list):
            for index, item in enumerate(output):
                if index:
                    console.print()
                console.print(Pretty(item))
        else:
            console.print(Pretty(output))


def print_table(issues: Results[Issue]):
    """
    Print and page the output (a list of issues) in a table.

    :param issues: A list of issues to print.
    """

    if not issues or not all(isinstance(issue, Issue) for issue in issues):
        return

    context = console.pager(styles=True) if console.is_terminal else nullcontext()

    if not console.is_terminal:
        console.print(f"{WARN} Not a TTY — output won't be paged.")

    table = Table(box=MARKDOWN, highlight=True, expand=True, header_style="bold")
    table.add_column("ID", justify="right")
    table.add_column("Title", overflow="fold")
    table.add_column("Type")
    table.add_column("Priority")
    table.add_column("Severity")
    table.add_column("Status")
    table.add_column("24h Views", justify="right")
    table.add_column("7d Views", justify="right")
    table.add_column("30d Views", justify="right")
    table.add_column("Created At", overflow="fold")
    table.add_column("Modified At", overflow="fold")

    for issue in issues:
        table.add_row(
            str(issue.id),
            issue.title,
            _style_cell(
                value=issue.issue_type, styles=ISSUE_TYPE_STYLES, default="dim"
            ),
            _style_cell(value=issue.priority, styles=PRIORITY_STYLES, default="yellow"),
            _style_cell(value=issue.severity, styles=SEVERITY_STYLES, default="green"),
            _style_cell(value=issue.status, styles=STATUS_STYLES, default="dim"),
            str(issue.views_24h),
            str(issue.views_7d),
            str(issue.views_30d),
            str(issue.created_at),
            str(issue.modified_at),
        )

    with context:
        console.print(table)


def export(output: Exportable | Results[Exportable], formats: list[str]):
    """
    Write a result to timestamped files, one per format.

    :param output: A single item, or a list of them.
    :param formats: Format strings, each one of ``"csv"`` or ``"json"``.
    """

    if not output:
        return

    base = f"buganize-{datetime.now().astimezone().strftime('%Y%m%d_%H%M%S')}"
    for fmt in formats:
        if fmt == "json":
            console.print(f"\n{OK} JSON exported to {output.to_json(f'{base}.json')}")
        elif fmt == "csv":
            console.print(f"\n{OK} CSV exported to {output.to_csv(f'{base}.csv')}")
        else:
            continue
