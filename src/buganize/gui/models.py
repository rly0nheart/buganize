"""Small data adapters: GObject wrapper for Issue and serialization helpers."""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime

from gi.repository import GObject

from buganize import Issue


class IssueItem(GObject.Object):
    """
    GObject wrapper so :class:`Issue` instances can live in a ``Gio.ListStore``.

    :param issue: The Issue instance to wrap.
    """

    def __init__(self, issue: Issue):
        super().__init__()
        self.issue = issue


def fmt_dt(dt: datetime | None) -> str:
    """
    Format a datetime for display in table cells.

    :param dt: Datetime to format, or ``None``.
    :return: ``YYYY-MM-DD HH:MM`` string, or empty string if ``dt`` is ``None``.
    """

    if dt is None:
        return ""
    return dt.strftime("%Y-%m-%d %H:%M")


def issue_to_flat_row(issue: Issue) -> dict[str, str]:
    """
    Render an Issue as a flat ``{field_name: string}`` dict suitable for CSV
    or HTML export.

    Enums become their ``.name``; lists are comma-joined; dicts are
    JSON-encoded; ``None`` becomes an empty string.

    :param issue: The Issue to flatten.
    :return: Dict keyed by Issue dataclass field name with stringified values.
    """

    flat: dict[str, str] = {}
    for key, value in asdict(issue).items():
        if value is None:
            flat[key] = ""
        elif isinstance(value, list):
            flat[key] = ", ".join(str(x) for x in value)
        elif isinstance(value, dict):
            flat[key] = json.dumps(value, default=str)
        elif hasattr(value, "name"):  # Enum
            flat[key] = value.name
        else:
            flat[key] = str(value)
    return flat
