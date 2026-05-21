"""Filter widgets: single-select FilterButton + multi-select TrackerFilter."""

from __future__ import annotations

from typing import Callable, Iterable

from gi.repository import Gtk, Pango


class FilterButton:
    """
    A single-select filter rendered as a ``Gtk.MenuButton`` with a ListBox
    popover of choices.

    :param label: Prefix shown in the button face (e.g. ``"Status"``).
    :param choices: Sequence of ``(display, value)`` tuples. ``value=None``
        means "no filter token" and is omitted from the query.
    :param icon_name: Themed icon name shown on the button.
    :param on_changed: Called with no arguments whenever the selection
        changes via the popover.
    """

    def __init__(
        self,
        label: str,
        choices: list[tuple[str, str | None]],
        icon_name: str,
        on_changed: Callable[[], None],
    ):
        self.prefix = label
        self.choices = choices
        self.selected = 0
        self._on_changed = on_changed

        list_box = Gtk.ListBox()
        list_box.set_selection_mode(Gtk.SelectionMode.NONE)
        for display, _ in choices:
            row = Gtk.Label(label=display, xalign=0)
            row.set_margin_start(12)
            row.set_margin_end(12)
            row.set_margin_top(6)
            row.set_margin_bottom(6)
            list_box.append(row)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_propagate_natural_height(True)
        scrolled.set_max_content_height(400)
        scrolled.set_min_content_width(200)
        scrolled.set_child(list_box)

        self.popover = Gtk.Popover()
        self.popover.set_child(scrolled)

        content = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        content.append(Gtk.Image.new_from_icon_name(icon_name))
        self._label_widget = Gtk.Label(label=f"{label}: {choices[0][0]}")
        self._label_widget.set_ellipsize(Pango.EllipsizeMode.END)
        self._label_widget.set_max_width_chars(14)
        content.append(self._label_widget)

        self.button = Gtk.MenuButton()
        self.button.set_child(content)
        self.button.set_always_show_arrow(True)
        self.button.set_popover(self.popover)
        self.button.set_tooltip_text(f"Filter by {label.lower()}")
        self.button.set_size_request(130, -1)

        list_box.connect(
            "row-activated", lambda _lb, r: self._on_row_activated(r.get_index())
        )

    @property
    def value(self) -> str | None:
        """
        Currently-selected query token, or ``None`` if no filter is active.
        """

        return self.choices[self.selected][1]

    def set_selection(self, index: int) -> None:
        """
        Programmatically select the choice at ``index`` without firing
        ``on_changed``. Updates the button label.

        :param index: Zero-based index into ``choices``.
        """

        self.selected = index
        display = self.choices[index][0]
        self._label_widget.set_text(f"{self.prefix}: {display}")

    def _on_row_activated(self, index: int) -> None:
        """
        Internal: update selection, close popover, fire callback.

        :param index: Index of the activated row in :attr:`choices`.
        """

        self.set_selection(index)
        self.popover.popdown()
        self._on_changed()


class TrackerFilter:
    """
    Single-select tracker chooser.

    The active row is checkmarked and non-activatable; every other row stays
    clickable so the user can switch. The "IssueTracker" row at the top
    means no constraint (the client searches every public tracker).

    :param trackers: Iterable of ``(slug, display_name)`` pairs. The slug is
        the identifier returned via :attr:`active`; the display_name is the
        label rendered in the popover row.
    :param on_changed: Called with the new active slug (or ``None``) each
        time the selection changes.
    :param icon_path_for: Returns the SVG path for a given slug (or ``None``
        for the "all" state). Used for the button face icon.
    """

    ALL_LABEL = "IssueTracker"

    def __init__(
        self,
        trackers: Iterable[tuple[str, str]],
        on_changed: Callable[[str | None], None],
        icon_path_for: Callable[[str | None], str],
    ):
        # active == None means "All trackers"
        self.active: str | None = None
        self._on_changed = on_changed
        self._icon_path_for = icon_path_for

        # (display, value)  — value=None for "All", otherwise the slug
        self._choices: list[tuple[str, str | None]] = [
            (self.ALL_LABEL, None)
        ] + sorted(
            ((name, slug) for slug, name in trackers),
            key=lambda pair: pair[0].lower(),
        )
        self._rows: list[Gtk.ListBoxRow] = []
        self._checks: list[Gtk.Image] = []

        list_box = Gtk.ListBox()
        list_box.set_selection_mode(Gtk.SelectionMode.NONE)
        for i, (display, value) in enumerate(self._choices):
            box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
            box.set_margin_start(12)
            box.set_margin_end(12)
            box.set_margin_top(6)
            box.set_margin_bottom(6)

            check = Gtk.Image.new_from_icon_name("object-select-symbolic")
            check.set_opacity(1 if i == 0 else 0)
            self._checks.append(check)
            box.append(check)

            tracker_icon = Gtk.Image()
            tracker_icon.set_pixel_size(16)
            tracker_icon.set_from_file(self._icon_path_for(value))
            box.append(tracker_icon)

            box.append(Gtk.Label(label=display, xalign=0))

            row = Gtk.ListBoxRow()
            row.set_child(box)
            row.set_activatable(i != 0)
            self._rows.append(row)
            list_box.append(row)

        list_box.connect(
            "row-activated", lambda _lb, r: self._on_row_activated(r.get_index())
        )

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_propagate_natural_height(True)
        scrolled.set_max_content_height(400)
        scrolled.set_min_content_width(200)
        scrolled.set_child(list_box)

        self.popover = Gtk.Popover()
        self.popover.set_child(scrolled)

        self._button_icon = Gtk.Image()
        self._button_icon.set_pixel_size(20)

        self.button = Gtk.MenuButton()
        self.button.set_child(self._button_icon)
        self.button.set_always_show_arrow(True)
        self.button.set_popover(self.popover)
        self.button.set_tooltip_text(
            "Select tracker. IssueTracker searches all trackers."
        )
        self._refresh_button_icon()

    def _refresh_button_icon(self) -> None:
        """
        Internal: swap the dropdown button's icon to reflect :attr:`active`.
        """

        self._button_icon.set_from_file(self._icon_path_for(self.active))

    def _on_row_activated(self, index: int) -> None:
        """
        Internal: switch the active tracker, update check marks +
        activatability, refresh button icon, close popover, fire callback.

        :param index: Row index in :attr:`_choices`.
        """

        if not self._rows[index].get_activatable():
            return
        self.active = self._choices[index][1]
        for i, (check, row) in enumerate(zip(self._checks, self._rows)):
            is_active = i == index
            check.set_opacity(1 if is_active else 0)
            row.set_activatable(not is_active)
        self._refresh_button_icon()
        self.popover.popdown()
        self._on_changed(self.active)

    def reset(self) -> None:
        """
        Return to the default "IssueTracker" (no filter) state. No-op if
        already at default. Does not fire ``on_changed``.
        """

        if self.active is None:
            return
        self.active = None
        for i, (check, row) in enumerate(zip(self._checks, self._rows)):
            is_active = i == 0
            check.set_opacity(1 if is_active else 0)
            row.set_activatable(not is_active)
        self._refresh_button_icon()
