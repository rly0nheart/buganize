from __future__ import annotations

import typing as t

import pandas as pd

from buganize.cli import console

if t.TYPE_CHECKING:
    from buganize.api.models import Comment, Issue

pd.options.display.max_colwidth = None

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
    "labels": lambda issue: ", ".join(issue.chromium_labels) or None,
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
}


def to_dataframe(
        items: t.Union[list[Issue], list[Comment]],
        fields: t.Optional[list[str]] = None,
) -> pd.DataFrame:
    """
    Convert a list of issues or comments into a pandas DataFrame.

    For issues, the default columns are ID, Status, Priority, Title.
    Extra columns are added based on *fields*.
    For comments, columns are #, Author, Date, Body.

    :param items: The issues or comments to convert.
    :param fields: Extra field names to include (issues only).
    :return: A DataFrame with one row per item.
    """

    if not items:
        return pd.DataFrame()

    if isinstance(items[0], Issue):
        return _issues_to_rows(issues=items, fields=fields)  # type: ignore[arg-type]
    return _comments_to_rows(comments=items)  # type: ignore[arg-type]


def export(df: pd.DataFrame, formats: list[str]):
    """
    Export a DataFrame in one or more formats to stdout.

    :param df: The DataFrame to export.
    :param formats: List of format strings, each one of ``"csv"``, ``"json"``, or ``"html"``.
    """

    for fmt in formats:
        if fmt == "csv":
            console.print(df.to_csv(), end="")
        elif fmt == "json":
            console.print(df.to_json(orient="records", indent=4))
        elif fmt == "html":
            console.print(df.to_html())


def _column_header(key: str) -> str:
    """
    Derive a column header from a field key.

    :param key: The field key (e.g. ``"merge_request"``).
    :return: Title-cased header (e.g. ``"Merge Request"``).
    """

    return key.replace("_", " ").title()


def _issues_to_rows(
        issues: list[Issue],
        fields: t.Optional[list[str]] = None,
) -> pd.DataFrame:
    """
    Build a DataFrame from a list of issues.

    Default columns are ID, Status, Priority, and Title. Additional
    columns are appended for each name in *fields* that exists in
    :data:`EXTRA_FIELDS`.

    :param issues: The issues to convert.
    :param fields: Extra field names to include as columns.
    :return: A DataFrame with one row per issue.
    """

    rows = []
    for issue in issues:
        row: dict[str, t.Any] = {
            "ID": issue.id,
            "Status": issue.status.name.lower(),
            "Priority": issue.priority.name,
            "Title": issue.title,
        }
        for field_name in fields or []:
            if field_name in EXTRA_FIELDS:
                getter = EXTRA_FIELDS[field_name]
                row[_column_header(field_name)] = getter(issue) or ""
        rows.append(row)
    return pd.DataFrame(rows)


def _comments_to_rows(comments: list[Comment]) -> pd.DataFrame:
    """
    Build a DataFrame from a list of comments.

    Columns are #, Author, Date, and Body.

    :param comments: The comments to convert.
    :return: A DataFrame with one row per comment.
    """

    rows = []
    for comment in comments:
        rows.append(
            {
                "#": comment.comment_number,
                "Author": comment.author or "unknown",
                "Date": (
                    comment.timestamp.strftime("%Y-%m-%d %H:%M UTC")
                    if comment.timestamp
                    else ""
                ),
                "Body": comment.body,
            }
        )
    return pd.DataFrame(rows)
