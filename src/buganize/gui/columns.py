"""ColumnView column registry, default column definitions, and the Fields
MenuButton that toggles extras on/off."""

from __future__ import annotations

from typing import Callable

from gi.repository import Gtk, Pango

from buganize import EXTRA_FIELDS, Issue

from .models import IssueItem, fmt_dt

# Default column keys — the always-on set. Extras (everything in EXTRA_FIELDS
# not in this set) are togglable via the Fields menu.
DEFAULT_COLUMN_KEYS: frozenset[str] = frozenset(
    {
        "id",
        "title",
        "status",
        "priority",
        "severity",
        "issue_type",
        "reporter",
        "owner",
        "created_at",
        "modified_at",
        "comment_count",
        "star_count",
    }
)

# EXTRA_FIELDS keys whose data is already exposed by a default column.
_EXTRAS_COVERED_BY_DEFAULTS: frozenset[str] = frozenset(
    {
        "owner",
        "reporter",
        "type",
        "severity",
        "created",
        "modified",
        "comments",
        "stars",
    }
)


ColumnGetter = Callable[[Issue], str]


def _make_column(
    title: str,
    getter: ColumnGetter,
    *,
    fixed_width: int | None = None,
    expand: bool = False,
    monospace: bool = False,
) -> Gtk.ColumnViewColumn:
    """
    Build a single :class:`Gtk.ColumnViewColumn` whose cells render
    ``getter(issue)`` into an ellipsized :class:`Gtk.Label` (with the full
    value mirrored to the cell's tooltip).

    :param title: Column header text.
    :param getter: ``Issue -> str`` cell-value extractor.
    :param fixed_width: Initial fixed width in pixels (resizable).
    :param expand: Whether the column should claim extra horizontal space.
    :param monospace: Apply the ``monospace`` CSS class to cell labels.
    :return: Configured :class:`Gtk.ColumnViewColumn`.
    """

    factory = Gtk.SignalListItemFactory()

    def on_setup(_factory, item):
        label = Gtk.Label(xalign=0)
        label.set_ellipsize(Pango.EllipsizeMode.END)
        if monospace:
            label.add_css_class("monospace")
        item.set_child(label)

    def on_bind(_factory, item):
        label = item.get_child()
        issue_item: IssueItem = item.get_item()
        text = getter(issue_item.issue)
        label.set_text(text)
        # Full text on hover so ellipsized cells stay readable.
        label.set_tooltip_text(text if text else None)

    factory.connect("setup", on_setup)
    factory.connect("bind", on_bind)

    column = Gtk.ColumnViewColumn(title=title, factory=factory)
    column.set_resizable(True)
    column.set_expand(expand)
    if fixed_width is not None:
        column.set_fixed_width(fixed_width)
    return column


def build_columns(
    column_view: Gtk.ColumnView,
) -> tuple[dict[str, Gtk.ColumnViewColumn], dict[str, str]]:
    """
    Build every available column for the issue table.

    Default columns are appended to ``column_view`` immediately. Extra
    columns (derived from ``EXTRA_FIELDS``) are constructed but kept off the
    view; the caller toggles them in/out via :func:`build_fields_button`.

    :param column_view: The :class:`Gtk.ColumnView` to attach default
        columns to.
    :return: ``(columns_by_key, titles_by_key)`` — both keyed by short field
        name (e.g. ``"id"``, ``"priority"``, ``"vrp_reward"``).
    """

    columns: dict[str, Gtk.ColumnViewColumn] = {}
    titles: dict[str, str] = {}

    defaults: list[tuple[str, str, ColumnGetter, dict]] = [
        ("id", "ID", lambda i: str(i.id), dict(fixed_width=90, monospace=True)),
        ("title", "Title", lambda i: i.title or "", dict(expand=True, fixed_width=420)),
        (
            "status",
            "Status",
            lambda i: i.status.name if i.status is not None else "",
            dict(fixed_width=110),
        ),
        (
            "priority",
            "Pri",
            lambda i: i.priority.name if i.priority is not None else "",
            dict(fixed_width=70),
        ),
        (
            "severity",
            "Sev",
            lambda i: i.severity.name if i.severity is not None else "",
            dict(fixed_width=70),
        ),
        (
            "issue_type",
            "Type",
            lambda i: i.issue_type.name if i.issue_type is not None else "",
            dict(fixed_width=140),
        ),
        ("reporter", "Reporter", lambda i: i.reporter or "", dict(fixed_width=200)),
        ("owner", "Owner", lambda i: i.owner or "", dict(fixed_width=200)),
        (
            "created_at",
            "Created",
            lambda i: fmt_dt(i.created_at),
            dict(fixed_width=140),
        ),
        (
            "modified_at",
            "Modified",
            lambda i: fmt_dt(i.modified_at),
            dict(fixed_width=140),
        ),
        (
            "comment_count",
            "Comments",
            lambda i: str(i.comment_count),
            dict(fixed_width=90),
        ),
        ("star_count", "Stars", lambda i: str(i.star_count), dict(fixed_width=70)),
    ]

    for key, title, getter, kw in defaults:
        col = _make_column(title, getter, **kw)
        columns[key] = col
        titles[key] = title
        column_view.append_column(col)

    for ext_key, ext_getter in EXTRA_FIELDS.items():
        if ext_key in _EXTRAS_COVERED_BY_DEFAULTS:
            continue
        title = ext_key.replace("_", " ").title()
        col = _make_column(title, lambda i, g=ext_getter: g(i) or "", fixed_width=140)
        columns[ext_key] = col
        titles[ext_key] = title

    return columns, titles


def column_position(
    column_view: Gtk.ColumnView, column: Gtk.ColumnViewColumn
) -> int | None:
    """
    Return the index of ``column`` in ``column_view``, or ``None`` if the
    column is not currently attached.

    :param column_view: The view to search.
    :param column: The column instance to locate.
    :return: Zero-based index, or ``None`` if not found.
    """

    model = column_view.get_columns()
    for i in range(model.get_n_items()):
        if model.get_item(i) is column:
            return i
    return None


def build_fields_button(
    columns: dict[str, Gtk.ColumnViewColumn],
    titles: dict[str, str],
    on_toggle: Callable[[Gtk.CheckButton, str], None],
    is_visible: Callable[[str], bool],
) -> Gtk.MenuButton:
    """
    Build the "Fields" :class:`Gtk.MenuButton` whose popover lets the user
    toggle extra columns on/off.

    Only extras (keys not in :data:`DEFAULT_COLUMN_KEYS`) appear in the
    popover; defaults are always visible.

    :param columns: Mapping of column key → :class:`Gtk.ColumnViewColumn`,
        as returned by :func:`build_columns`.
    :param titles: Mapping of column key → display title.
    :param on_toggle: Called as ``(check_button, ext_key)`` whenever an
        extra is ticked or unticked.
    :param is_visible: Returns ``True`` if the column for the given key is
        currently attached to the view. Used to set initial checkbox state.
    :return: ``(button, count_label)`` — the MenuButton and the inline label
        that the caller updates to show the active extras count.
    """

    list_box = Gtk.ListBox()
    list_box.set_selection_mode(Gtk.SelectionMode.NONE)

    for ext_key in sorted(titles):
        if ext_key in DEFAULT_COLUMN_KEYS:
            continue
        check = Gtk.CheckButton(label=titles[ext_key])
        check.set_active(is_visible(ext_key))
        check.connect("toggled", on_toggle, ext_key)
        list_box.append(check)

    scrolled = Gtk.ScrolledWindow()
    scrolled.set_propagate_natural_height(True)
    scrolled.set_max_content_height(400)
    scrolled.set_min_content_width(220)
    scrolled.set_child(list_box)

    popover = Gtk.Popover()
    popover.set_child(scrolled)

    content = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
    content.append(Gtk.Image.new_from_icon_name("view-list-bullet-symbolic"))
    count_label = Gtk.Label()
    count_label.set_visible(False)
    content.append(count_label)

    button = Gtk.MenuButton()
    button.set_child(content)
    button.set_always_show_arrow(True)
    button.set_popover(popover)
    button.set_tooltip_text("Show/hide extra columns (drag headers to reorder)")
    button.set_sensitive(False)
    return button, count_label
