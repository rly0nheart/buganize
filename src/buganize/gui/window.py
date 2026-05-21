"""MainWindow — orchestrates the search bar, filters, table, pagination, and
context menus. Delegates the GTK-heavy concerns to the helper modules."""

from __future__ import annotations

import csv
import json
import os
import webbrowser

from gi.repository import Adw, Gdk, GdkPixbuf, Gio, GLib, Gtk

from buganize import Issue, SearchResult

from .columns import (
    DEFAULT_COLUMN_KEYS,
    build_columns,
    build_fields_button,
    column_position,
)
from buganize import TRACKERS

# Map tracker numeric id → base URL, e.g. 157 → "https://issues.chromium.org".
# Used to route "open in browser" through the issue's real tracker rather than
# the generic issuetracker.google.com URL on Issue.url.
_TRACKER_URL_BY_ID: dict[int, str] = {
    tracker["id"]: tracker["url"] for tracker in TRACKERS
}
_TRACKER_NAME_BY_SLUG: dict[str, str] = {
    tracker["slug"]: tracker["name"] for tracker in TRACKERS
}


def _issue_url(issue) -> str:
    """
    Build the canonical browser URL for ``issue`` using its tracker's
    domain (e.g. ``https://issues.chromium.org/issues/12345``).

    :param issue: An :class:`Issue` instance.
    :return: Tracker-specific URL, falling back to ``issue.url`` if the
        tracker id is missing from :data:`TRACKERS`.
    """

    base = _TRACKER_URL_BY_ID.get(issue.tracker_id or 0)
    return f"{base}/issues/{issue.id}" if base else issue.url


from .constants import (
    APP_ICON_NAME,
    APP_VERSION,
    DEFAULT_PAGE_SIZE,
    EMPTY_STATE_CSS,
    EMPTY_STATE_IMAGE,
    ICONS_DIR,
    PAGE_SIZE_CHOICES,
    TRACKER_ICONS_DIR,
)
from .filters import TrackerFilter
from .models import IssueItem, issue_to_flat_row
from .search_worker import run_search


class MainWindow(Gtk.ApplicationWindow):
    """
    Main application window for the Buganize GUI.

    Hosts the search bar, tracker selector, results table, status row, and
    pagination controls. Owns the worker callbacks that bridge async
    :class:`Buganize` search results back to the GTK main loop.

    :param application: The parent :class:`Adw.Application`.
    """

    def __init__(self, application: Gtk.Application):
        """
        Initialise window state and trigger UI construction.

        :param application: The owning :class:`Adw.Application`.
        """

        super().__init__(application=application)
        self.set_title(f"Buganize {APP_VERSION}")
        self.set_default_size(1300, 800)

        self._store: Gio.ListStore = Gio.ListStore.new(IssueItem)
        self._pages: list[SearchResult] = []
        self._current_page: int = 0
        self._page_size: int = DEFAULT_PAGE_SIZE
        self._searching: bool = False
        self._pending_replace: bool = False
        self._active_jobs: int = 0
        self._context_issue: Issue | None = None

        self._build_ui()

    # --- UI construction ---------------------------------------------------

    def _build_ui(self) -> None:
        """
        Assemble the window contents.

        Sets up theme/icon/CSS, registers ``win.about`` / ``win.quit``
        actions, builds the header bar (with active-tracker indicator and
        menu button), and appends the search row, status row, and results
        view to the root vertical box.
        """

        Adw.StyleManager.get_default().set_color_scheme(Adw.ColorScheme.FORCE_DARK)
        Gtk.IconTheme.get_for_display(self.get_display()).add_search_path(ICONS_DIR)
        Gtk.Window.set_default_icon_name(APP_ICON_NAME)
        self.set_icon_name(APP_ICON_NAME)

        css = Gtk.CssProvider()
        css.load_from_string(
            EMPTY_STATE_CSS
            + "\n.with-tracker-dropdown {"
            + " padding-top: 4px; padding-bottom: 4px; }"
            + "\n.with-tracker-dropdown text { padding-right: 92px; }"
            + "\n.with-tracker-dropdown > image:last-child {"
            + " opacity: 0; min-width: 0; min-height: 0;"
            + " margin: 0; padding: 0; }"
            + "\n.tracker-no-hover, .tracker-no-hover:hover, .tracker-no-hover:active,"
            + " .tracker-no-hover button, .tracker-no-hover button:hover,"
            + " .tracker-no-hover button:active {"
            + " background: transparent; box-shadow: none; }"
        )
        Gtk.StyleContext.add_provider_for_display(
            self.get_display(), css, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

        for name, handler in (
            ("about", lambda *_: self._show_about_dialog()),
            ("quit", lambda *_: self.get_application().quit()),
        ):
            action = Gio.SimpleAction.new(name, None)
            action.connect("activate", handler)
            self.add_action(action)

        header = Gtk.HeaderBar()
        # Hide the default window-title widget that would otherwise show
        # "Buganize <version>" centred in the header bar.
        header.set_title_widget(Gtk.Box())

        self.active_tracker_box = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL, spacing=8
        )
        self.active_tracker_box.set_margin_start(8)
        self.active_tracker_icon = Gtk.Image()
        self.active_tracker_icon.set_pixel_size(32)
        self.active_tracker_label = Gtk.Label()
        self.active_tracker_label.add_css_class("title-3")
        self.active_tracker_box.append(self.active_tracker_icon)
        self.active_tracker_box.append(self.active_tracker_label)
        header.pack_start(self.active_tracker_box)
        self._set_active_tracker_display(None)

        app_menu = Gio.Menu()
        app_menu.append("About Buganize", "win.about")
        app_menu.append("Quit", "win.quit")
        menu_btn = Gtk.MenuButton()
        menu_btn.set_icon_name("view-more-symbolic")
        menu_btn.set_menu_model(app_menu)
        menu_btn.set_tooltip_text("Menu")
        menu_btn.add_css_class("circular")
        menu_btn.set_cursor(Gdk.Cursor.new_from_name("pointer"))
        header.pack_end(menu_btn)
        self.set_titlebar(header)

        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.set_child(root)

        # Build results view first so self._columns exists when the filter
        # row constructs its Fields menu button.
        results_view = self._build_results_view()

        root.append(self._build_search_row())
        root.append(self._build_status_row())
        root.append(results_view)

    def _build_search_row(self) -> Gtk.Widget:
        """
        Build the top search row: search entry with the tracker dropdown and
        Fields menu overlaid on its right edge, followed by the Reset button.

        :return: The horizontal :class:`Gtk.Box` ready for the root layout.
        """

        row = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL,
            spacing=8,
            margin_top=8,
            margin_bottom=4,
            margin_start=8,
            margin_end=8,
        )

        self.tracker_filter = TrackerFilter(
            [(tracker["slug"], tracker["name"]) for tracker in TRACKERS],
            on_changed=self._on_tracker_changed,
            icon_path_for=self._tracker_icon_path,
        )
        self.tracker_filter.button.add_css_class("flat")
        self.tracker_filter.button.add_css_class("tracker-no-hover")
        self.tracker_filter.button.set_cursor(Gdk.Cursor.new_from_name("pointer"))

        self.fields_btn, self._fields_label = build_fields_button(
            self._columns,
            self._column_titles,
            on_toggle=self._on_toggle_column,
            is_visible=lambda key: column_position(self.column_view, self._columns[key])
            is not None,
        )
        self.fields_btn.add_css_class("flat")
        self.fields_btn.add_css_class("tracker-no-hover")
        self.fields_btn.set_cursor(Gdk.Cursor.new_from_name("pointer"))

        self.search_entry = Gtk.SearchEntry()
        self.search_entry.set_hexpand(True)
        self.search_entry.set_placeholder_text("Search IssueTracker")
        self.search_entry.add_css_class("with-tracker-dropdown")
        self.search_entry.connect("activate", lambda _e: self._on_search_clicked())
        self.search_entry.connect("changed", lambda _e: self._update_reset_state())

        right_buttons = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        right_buttons.set_halign(Gtk.Align.END)
        right_buttons.set_valign(Gtk.Align.CENTER)
        right_buttons.set_margin_end(4)
        right_buttons.append(self.fields_btn)
        right_buttons.append(self.tracker_filter.button)

        search_overlay = Gtk.Overlay()
        search_overlay.set_hexpand(True)
        search_overlay.set_child(self.search_entry)
        search_overlay.add_overlay(right_buttons)
        row.append(search_overlay)

        self.reset_btn = Gtk.Button(label="Reset")
        self.reset_btn.add_css_class("suggested-action")
        self.reset_btn.set_tooltip_text("Reset filters, search, and results")
        self.reset_btn.set_sensitive(False)
        self.reset_btn.set_cursor(Gdk.Cursor.new_from_name("pointer"))
        self.reset_btn.connect("clicked", lambda _b: self._on_reset())
        row.append(self.reset_btn)

        return row

    def _build_status_row(self) -> Gtk.Widget:
        """
        Build the row underneath the search bar: refresh button, in-flight
        spinner, status text, and (when results are present) page-size
        dropdown, position label, and prev/next pagination buttons.

        :return: The horizontal :class:`Gtk.Box` for the root layout.
        """

        row = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL,
            spacing=8,
            margin_start=8,
            margin_end=16,
            margin_top=4,
            margin_bottom=4,
        )

        self.refresh_btn = Gtk.Button.new_from_icon_name("view-refresh-symbolic")
        self.refresh_btn.add_css_class("flat")
        self.refresh_btn.add_css_class("circular")
        self.refresh_btn.set_tooltip_text("Refresh results")
        self.refresh_btn.set_visible(False)
        self.refresh_btn.set_cursor(Gdk.Cursor.new_from_name("pointer"))
        self.refresh_btn.connect("clicked", lambda _b: self._on_refresh())
        row.append(self.refresh_btn)

        self.spinner = Adw.Spinner()
        self.spinner.set_visible(False)
        row.append(self.spinner)

        self.status_label = Gtk.Label()
        self.status_label.set_xalign(0)
        self.status_label.set_hexpand(True)
        from gi.repository import Pango

        self.status_label.set_ellipsize(Pango.EllipsizeMode.END)
        self.status_label.add_css_class("dim-label")
        row.append(self.status_label)

        self.page_size_btn = self._build_page_size_button()
        self.page_size_btn.add_css_class("flat")
        self.page_size_btn.add_css_class("circular")
        self.page_size_btn.set_visible(False)
        self.page_size_btn.set_cursor(Gdk.Cursor.new_from_name("pointer"))
        row.append(self.page_size_btn)

        self.position_label = Gtk.Label()
        self.position_label.add_css_class("dim-label")
        row.append(self.position_label)

        self.prev_btn = Gtk.Button.new_from_icon_name("go-previous-symbolic")
        self.prev_btn.add_css_class("flat")
        self.prev_btn.add_css_class("circular")
        self.prev_btn.set_tooltip_text("Previous page")
        self.prev_btn.set_sensitive(False)
        self.prev_btn.set_visible(False)
        self.prev_btn.set_cursor(Gdk.Cursor.new_from_name("pointer"))
        self.prev_btn.connect("clicked", lambda _b: self._on_prev_page())
        row.append(self.prev_btn)

        self.next_btn = Gtk.Button.new_from_icon_name("go-next-symbolic")
        self.next_btn.add_css_class("flat")
        self.next_btn.add_css_class("circular")
        self.next_btn.set_tooltip_text("Next page")
        self.next_btn.set_sensitive(False)
        self.next_btn.set_visible(False)
        self.next_btn.set_cursor(Gdk.Cursor.new_from_name("pointer"))
        self.next_btn.connect("clicked", lambda _b: self._on_next_page())
        row.append(self.next_btn)

        return row

    def _build_page_size_button(self) -> Gtk.MenuButton:
        """
        Build the page-size dropdown (the small icon-only button on the
        status row). The current selection is marked with a checkmark and
        rendered non-activatable.

        :return: The :class:`Gtk.MenuButton` ready to attach to the row.
        """

        list_box = Gtk.ListBox()
        list_box.set_selection_mode(Gtk.SelectionMode.NONE)

        self._page_size_checks: list[Gtk.Image] = []
        self._page_size_rows: list[Gtk.ListBoxRow] = []
        for size in PAGE_SIZE_CHOICES:
            box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
            box.set_margin_start(12)
            box.set_margin_end(12)
            box.set_margin_top(6)
            box.set_margin_bottom(6)

            check = Gtk.Image.new_from_icon_name("object-select-symbolic")
            check.set_opacity(1 if size == self._page_size else 0)
            self._page_size_checks.append(check)
            box.append(check)
            box.append(Gtk.Label(label=str(size), xalign=0))

            row = Gtk.ListBoxRow()
            row.set_child(box)
            row.set_activatable(size != self._page_size)
            self._page_size_rows.append(row)
            list_box.append(row)

        popover = Gtk.Popover()
        popover.set_child(list_box)

        button = Gtk.MenuButton()
        button.set_always_show_arrow(True)
        button.set_popover(popover)
        button.set_tooltip_text(f"Results per page: {self._page_size}")

        list_box.connect(
            "row-activated",
            lambda _lb, r, p=popover, b=button: self._on_page_size_changed(
                r.get_index(), p, b
            ),
        )
        return button

    def _build_results_view(self) -> Gtk.Widget:
        """
        Build the central area as a :class:`Gtk.Stack` that switches between
        the empty-state image and the table view depending on whether a
        search has populated the store.

        :return: The :class:`Gtk.Stack` widget.
        """

        self.results_stack = Gtk.Stack()
        self.results_stack.set_vexpand(True)
        self.results_stack.set_hexpand(True)
        self.results_stack.set_transition_type(Gtk.StackTransitionType.NONE)

        self.results_stack.add_named(self._build_empty_state(), "empty")
        self.results_stack.add_named(self._build_table(), "table")
        self.results_stack.set_visible_child_name("empty")

        return self.results_stack

    def _build_empty_state(self) -> Gtk.Widget:
        """
        Build the centered empty-state widget (the placeholder image + hint
        label shown when no search has been run yet).

        :return: The :class:`Gtk.Box` containing the picture and label.
        """

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=40)
        box.set_halign(Gtk.Align.CENTER)
        box.set_valign(Gtk.Align.CENTER)

        pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(
            EMPTY_STATE_IMAGE, 300, 300, True
        )
        image = Gtk.Picture.new_for_paintable(Gdk.Texture.new_for_pixbuf(pixbuf))
        image.set_content_fit(Gtk.ContentFit.CONTAIN)
        image.set_halign(Gtk.Align.CENTER)
        image.set_valign(Gtk.Align.CENTER)
        box.append(image)

        title = Gtk.Label(label="Use search box to find issues.")
        title.add_css_class("empty-state-text")
        box.append(title)

        return box

    def _build_table(self) -> Gtk.Widget:
        """
        Build the results :class:`Gtk.ColumnView` inside a scrolled window
        and install columns + the right-click context menu.

        :return: The scrolled :class:`Gtk.ScrolledWindow` wrapping the view.
        """

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_vexpand(True)
        scrolled.set_hexpand(True)

        selection = Gtk.SingleSelection.new(self._store)
        self.column_view = Gtk.ColumnView(model=selection)
        self.column_view.set_show_column_separators(True)
        self.column_view.set_show_row_separators(True)
        self.column_view.set_reorderable(True)
        self.column_view.set_cursor(Gdk.Cursor.new_from_name("pointer"))
        self.column_view.connect(
            "activate", lambda _cv, pos: self._on_row_activated(pos)
        )
        scrolled.set_child(self.column_view)

        self._columns, self._column_titles = build_columns(self.column_view)
        self._install_row_context_menu()

        return scrolled

    # --- Right-click context menu ------------------------------------------

    def _install_row_context_menu(self) -> None:
        """
        Register the ``win.save-issue`` / ``win.open-issue`` actions, build
        the right-click :class:`Gtk.PopoverMenu`, and attach a
        :class:`Gtk.GestureClick` so a right-click on any row pops it up
        at the cursor.
        """

        for name, handler, ptype in (
            ("save-issue", self._on_save_issue, "s"),
            ("open-issue", self._on_open_issue, None),
        ):
            vtype = GLib.VariantType.new(ptype) if ptype else None
            action = Gio.SimpleAction.new(name, vtype)
            action.connect("activate", handler)
            self.add_action(action)

        menu = Gio.Menu()
        save_sub = Gio.Menu()
        for label, fmt, icon_name in (
            ("JSON", "json", "text-x-generic-symbolic"),
            ("CSV", "csv", "x-office-spreadsheet-symbolic"),
            ("HTML", "html", "text-html-symbolic"),
        ):
            item = Gio.MenuItem.new(label, f"win.save-issue::{fmt}")
            item.set_icon(Gio.ThemedIcon.new(icon_name))
            save_sub.append_item(item)
        save_item = Gio.MenuItem.new_submenu("Export As", save_sub)
        save_item.set_icon(Gio.ThemedIcon.new("document-save-symbolic"))
        menu.append_item(save_item)

        open_item = Gio.MenuItem.new("Open in browser", "win.open-issue")
        open_item.set_icon(Gio.ThemedIcon.new("applications-internet-symbolic"))
        menu.append_item(open_item)

        self._context_popover = Gtk.PopoverMenu.new_from_model(menu)
        self._context_popover.set_has_arrow(False)
        self._context_popover.set_parent(self.column_view)

        right_click = Gtk.GestureClick.new()
        right_click.set_button(Gdk.BUTTON_SECONDARY)
        right_click.connect("pressed", self._on_row_right_click)
        self.column_view.add_controller(right_click)

    def _on_row_right_click(self, _gesture, _n_press, x: float, y: float) -> None:
        """
        Right-click gesture handler. Reads the currently-selected row from
        the selection model (right-click selects in :class:`Gtk.ColumnView`),
        stashes the Issue as ``_context_issue``, and pops up the context
        menu at the cursor position.

        :param x: X coordinate of the click in column-view space.
        :param y: Y coordinate of the click in column-view space.
        """

        selection = self.column_view.get_model()
        pos = selection.get_selected()
        if pos == Gtk.INVALID_LIST_POSITION:
            return
        item: IssueItem | None = self._store.get_item(pos)
        if item is None:
            return
        self._context_issue = item.issue

        rect = Gdk.Rectangle()
        rect.x = int(x)
        rect.y = int(y)
        rect.width = 1
        rect.height = 1
        self._context_popover.set_pointing_to(rect)
        self._context_popover.popup()

    def _on_open_issue(self, _action, _param) -> None:
        """
        ``win.open-issue`` handler: opens ``_context_issue.url`` (resolved
        through :func:`_issue_url` to the right tracker domain) in the
        system browser.
        """

        if self._context_issue is not None:
            webbrowser.open(_issue_url(self._context_issue))

    def _on_save_issue(self, _action, param) -> None:
        """
        ``win.save-issue`` handler. Opens a :class:`Gtk.FileDialog` save
        dialog and writes ``_context_issue`` to disk in the requested
        format (``json``, ``csv``, or ``html``) via :func:`_write_issue`.

        :param param: GVariant string carrying the export format.
        """

        if self._context_issue is None:
            return
        fmt = param.get_string()
        issue = self._context_issue

        dialog = Gtk.FileDialog()
        dialog.set_title(f"Export issue as {fmt.upper()}")
        dialog.set_initial_name(f"issue-{issue.id}.{fmt}")

        def on_save_done(dlg: Gtk.FileDialog, result) -> None:
            try:
                file = dlg.save_finish(result)
            except GLib.Error:
                return
            if file is None:
                return
            try:
                _write_issue(issue, fmt, file.get_path())
            except OSError:
                return

        dialog.save(self, None, on_save_done)

    # --- About -------------------------------------------------------------

    def _show_about_dialog(self) -> None:
        """
        Open the application's About dialog. The app logo is loaded
        directly from the bundled SVG via :class:`Gdk.Texture` to keep it
        crisp regardless of icon-theme state.
        """

        dialog = Gtk.AboutDialog(transient_for=self, modal=True)
        dialog.set_program_name("Buganize")
        dialog.set_version(APP_VERSION)
        dialog.set_comments(
            "GTK4 frontend for the buganize Python client.\n"
            "Search the Google Issue Tracker (Buganizer) from your desktop."
        )
        dialog.set_website("https://github.com/rly0nheart/buganize")
        dialog.set_website_label("github.com/rly0nheart/buganize")
        dialog.set_license_type(Gtk.License.MIT_X11)
        dialog.set_authors(["Ritchie Mwewa <hi@rly0nheart.com>"])
        # Rasterise the SVG at a high resolution via GdkPixbuf so the logo
        # stays sharp; Gdk.Texture.new_from_filename rasterizes at a small
        # default size and looks blurry when the dialog scales it up.
        logo_path = os.path.join(
            ICONS_DIR, "hicolor", "scalable", "apps", f"{APP_ICON_NAME}.svg"
        )
        pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_size(logo_path, 256, 256)
        dialog.set_logo(Gdk.Texture.new_for_pixbuf(pixbuf))
        dialog.present()

    # --- Filters / query ---------------------------------------------------

    def _on_filter_changed(self) -> None:
        """
        Callback fired by filter widgets when their selection changes;
        re-evaluates whether the Reset button should be enabled.
        """

        self._update_reset_state()

    def _tracker_icon_path(self, name: str | None) -> str:
        """
        Resolve the SVG path for a tracker slug, or the default
        ``issuetracker.svg`` when ``name`` is ``None``.

        :param name: Tracker slug (e.g. ``"chromium"``) or ``None``.
        :return: Absolute path to the SVG file.
        """

        return os.path.join(
            TRACKER_ICONS_DIR, f"{name if name else 'issuetracker'}.svg"
        )

    def _set_active_tracker_display(self, slug: str | None) -> None:
        """
        Update the header-bar tracker indicator (icon + name) and the
        search-entry placeholder to reflect ``slug``.

        :param slug: Currently-active tracker slug, or ``None`` for the
            "IssueTracker" default.
        """

        display = (
            _TRACKER_NAME_BY_SLUG.get(slug, slug.title()) if slug else "IssueTracker"
        )
        self.active_tracker_icon.set_from_file(self._tracker_icon_path(slug))
        self.active_tracker_label.set_text(display)
        # search_entry may not exist yet on the first call from _build_ui.
        if hasattr(self, "search_entry"):
            self.search_entry.set_placeholder_text(f"Search {display}")

    def _on_tracker_changed(self, name: str | None) -> None:
        """
        Callback fired by :class:`TrackerFilter` when the active tracker
        changes; refreshes the header indicator and reset-button state.
        """

        self._set_active_tracker_display(name)
        self._update_reset_state()

    def _build_query(self) -> str:
        """
        Return the search-entry text, stripped of leading/trailing
        whitespace, ready to feed to the API client.
        """

        return self.search_entry.get_text().strip()

    def _selected_trackers(self) -> list[str] | None:
        """
        Return the list of tracker slugs to scope the search to, or
        ``None`` for the default "all trackers" case.
        """

        return [self.tracker_filter.active] if self.tracker_filter.active else None

    # --- Columns -----------------------------------------------------------

    def _on_toggle_column(self, check: Gtk.CheckButton, ext_key: str) -> None:
        """
        Show or hide an extra column when its Fields menu checkbox is
        toggled. Newly-shown columns are inserted at the start of the table.

        :param check: The toggled :class:`Gtk.CheckButton`.
        :param ext_key: The column key (e.g. ``"vrp_reward"``).
        """

        col = self._columns[ext_key]
        pos = column_position(self.column_view, col)
        if check.get_active() and pos is None:
            self.column_view.insert_column(0, col)
        elif not check.get_active() and pos is not None:
            self.column_view.remove_column(col)
        self._refresh_fields_label()

    def _refresh_fields_label(self) -> None:
        """
        Update the count next to the Fields button so it reads
        ``"1 field"`` / ``"N fields"`` whenever extras are active, or hides
        the label entirely when none are.
        """

        visible = sum(
            1
            for key, col in self._columns.items()
            if key not in DEFAULT_COLUMN_KEYS
            and column_position(self.column_view, col) is not None
        )
        if visible == 0:
            self._fields_label.set_visible(False)
        else:
            self._fields_label.set_text(
                "1 field" if visible == 1 else f"{visible} fields"
            )
            self._fields_label.set_visible(True)

    # --- Search / pagination ----------------------------------------------

    def _on_search_clicked(self) -> None:
        """
        Activate handler on the search entry (also reachable via the
        Refresh button on subsequent runs). Kicks off a fresh search at
        page 1; ignored if another search is already in flight.
        """

        if self._searching:
            return
        self._search_first_page()

    def _search_first_page(self) -> None:
        """
        Start a fresh search from page 1. Deferred clear (the existing
        rows stay visible until the new page lands) is enabled so the
        table doesn't flash empty.
        """

        self._pending_replace = True
        self._start_search(page_token=None)

    def _on_refresh(self) -> None:
        """
        Refresh button handler: re-run the current query from page 1.
        No-op if a search is in flight or there are no results yet.
        """

        if self._searching or not self._pages:
            return
        self._search_first_page()

    def _on_prev_page(self) -> None:
        """
        Previous-page button handler: render the cached previous page
        if any; no-op at page 0 or while another search is running.
        """

        if self._current_page > 0 and not self._searching:
            self._current_page -= 1
            self._render_current_page()

    def _on_next_page(self) -> None:
        """
        Next-page button handler: render the next cached page if we
        already have it, otherwise fetch it via the page token.
        """

        if self._searching or not self._pages:
            return
        if self._current_page + 1 < len(self._pages):
            self._current_page += 1
            self._render_current_page()
            return
        current = self._pages[self._current_page]
        if current.next_page_token:
            self._start_search(page_token=current.next_page_token)

    def _on_page_size_changed(
        self, index: int, popover: Gtk.Popover, button: Gtk.MenuButton
    ) -> None:
        """
        Row-activated handler on the page-size popover. Updates the page
        size, repositions the checkmark, makes only the new row
        non-activatable, and re-fetches page 1 if results were already
        shown.

        :param index: Row index of the chosen size in :data:`PAGE_SIZE_CHOICES`.
        :param popover: The popover to close after the click.
        :param button: The owning menu button (for tooltip refresh).
        """

        new_size = PAGE_SIZE_CHOICES[index]
        popover.popdown()
        if new_size == self._page_size:
            return
        self._page_size = new_size
        button.set_tooltip_text(f"Results per page: {new_size}")
        for i, check in enumerate(self._page_size_checks):
            check.set_opacity(1 if i == index else 0)
        for i, row in enumerate(self._page_size_rows):
            row.set_activatable(i != index)
        if self._pages:
            self._search_first_page()

    def _on_reset(self) -> None:
        """
        Reset button handler: clear search text, reset the tracker filter
        to "IssueTracker", drop all cached pages, empty the table, swap
        back to the empty-state view, and reset pagination controls.
        """

        self.tracker_filter.reset()
        self._set_active_tracker_display(None)
        self.search_entry.set_text("")

        self._store.remove_all()
        self._pages = []
        self._current_page = 0
        self._pending_replace = False
        self.results_stack.set_visible_child_name("empty")
        self.fields_btn.set_sensitive(False)
        self.position_label.set_text("")
        self._set_status("")
        self._update_nav_buttons()
        self._update_reset_state()

    def _on_row_activated(self, position: int) -> None:
        """
        Double-click / Enter handler on a row: opens the issue in the
        system browser at the right tracker URL.

        :param position: Row position in the underlying store.
        """

        item: IssueItem | None = self._store.get_item(position)
        if item is not None:
            webbrowser.open(_issue_url(item.issue))

    def _start_search(self, page_token: str | None) -> None:
        """
        Kick off a search via :func:`run_search`. Updates the busy
        indicator + status message synchronously; the callback re-enters
        the main loop with the result.

        :param page_token: Page token to continue from, or ``None`` to
            fetch the first page.
        """

        query = self._build_query()
        if not query:
            self._set_status("Enter a query or pick a filter, then press Enter.")
            return

        self._searching = True
        self._show_busy(
            "Loading next page…" if page_token else f"Searching for {query}…"
        )

        run_search(
            query=query,
            page_size=self._page_size,
            page_token=page_token,
            trackers=self._selected_trackers(),
            callback=self._on_search_done,
        )

    def _on_search_done(
        self,
        result: SearchResult | None,
        err: Exception | None,
        was_next_page: bool,
    ) -> bool:
        """
        Main-loop callback for :func:`run_search`. Appends the new page to
        the cache, advances ``_current_page``, re-renders, and clears the
        busy state. Errors surface in the status label.

        :param result: The :class:`SearchResult`, or ``None`` on error.
        :param err: Exception raised by the API call, or ``None``.
        :param was_next_page: ``True`` if this was a forward-page fetch
            (used to decide whether to bump ``_current_page``).
        :return: ``False`` so :func:`GLib.idle_add` doesn't re-schedule.
        """

        self._searching = False
        self._hide_busy()

        if err is not None:
            self._pending_replace = False
            self._set_status(f"Error: {err}")
            return False

        assert result is not None

        if self._pending_replace:
            self._pages = []
            self._current_page = 0
            self._pending_replace = False

        self._pages.append(result)
        self._current_page = len(self._pages) - 1 if was_next_page else 0
        self._render_current_page()
        self._set_status("")
        self._update_reset_state()
        return False

    def _render_current_page(self) -> None:
        """
        Rebuild the table store from ``_pages[_current_page]`` and
        refresh the page-position label + nav buttons. Switches the stack
        to the empty-state if there are no pages.
        """

        self._store.remove_all()
        if not self._pages:
            self.results_stack.set_visible_child_name("empty")
            self.position_label.set_text("")
            self._update_nav_buttons()
            return
        page = self._pages[self._current_page]
        for issue in page.issues:
            self._store.append(IssueItem(issue))
        self.results_stack.set_visible_child_name("table")
        self.fields_btn.set_sensitive(True)
        self._update_position_label()
        self._update_nav_buttons()

    def _update_position_label(self) -> None:
        """
        Set the small position label to ``"N of TOTAL"`` based on the
        current page's slice of the result set.
        """

        page = self._pages[self._current_page]
        if not page.issues:
            self.position_label.set_text(f"0 of {page.total_count}")
            return
        end = self._current_page * self._page_size + len(page.issues)
        self.position_label.set_text(f"{end} of {page.total_count}")

    def _update_nav_buttons(self) -> None:
        """
        Show/hide and enable/disable the refresh, page-size, and
        prev/next buttons based on whether any pages are loaded and
        whether more pages exist forward/backward.
        """

        has_pages = bool(self._pages)
        for widget in (
            self.page_size_btn,
            self.refresh_btn,
            self.prev_btn,
            self.next_btn,
        ):
            widget.set_visible(has_pages)
        self.prev_btn.set_sensitive(self._current_page > 0)
        if not has_pages:
            self.next_btn.set_sensitive(False)
            return
        current = self._pages[self._current_page]
        has_next_cached = self._current_page + 1 < len(self._pages)
        self.next_btn.set_sensitive(has_next_cached or current.has_more)

    def _show_busy(self, message: str) -> None:
        """
        Show a status message and spin the spinner; increment the in-flight
        job counter. Always pair with :meth:`_hide_busy`.

        :param message: Status text to show next to the spinner.
        """

        self._set_status(message)
        self._active_jobs += 1
        self.spinner.set_visible(True)

    def _hide_busy(self, message: str = "") -> None:
        """
        Counterpart to :meth:`_show_busy`. Decrements the job counter and
        hides the spinner once it reaches zero.

        :param message: New status text to display (defaults to empty).
        """

        self._set_status(message)
        self._active_jobs = max(0, self._active_jobs - 1)
        if self._active_jobs == 0:
            self.spinner.set_visible(False)

    def _set_status(self, message: str) -> None:
        """
        Update the status row's text label.

        :param message: Plain text to display.
        """

        self.status_label.set_text(message)

    def _update_reset_state(self) -> None:
        """
        Enable the Reset button when something is dirty (search text,
        non-default tracker, or table has rows); disable otherwise.
        """

        dirty = (
            self.search_entry.get_text() != ""
            or self._store.get_n_items() > 0
            or self.tracker_filter.active is not None
        )
        self.reset_btn.set_sensitive(dirty)


def _write_issue(issue: Issue, fmt: str, path: str) -> None:
    """
    Serialise ``issue`` to ``path`` in the requested format.

    :param issue: The Issue to export.
    :param fmt: One of ``"json"``, ``"csv"``, ``"html"``.
    :param path: Destination file path.
    """

    if fmt == "json":
        from dataclasses import asdict

        with open(path, "w") as f:
            json.dump(asdict(issue), f, indent=2, default=str)
    elif fmt == "csv":
        row = issue_to_flat_row(issue)
        with open(path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=row.keys())
            writer.writeheader()
            writer.writerow(row)
    elif fmt == "html":
        row = issue_to_flat_row(issue)
        rows = "\n".join(f"<tr><th>{k}</th><td>{v}</td></tr>" for k, v in row.items())
        with open(path, "w") as f:
            f.write(
                "<!doctype html>\n"
                "<html><head><meta charset='utf-8'>"
                f"<title>Issue #{issue.id}</title></head>"
                f"<body><h1><a href='{issue.url}'>Issue #{issue.id}</a></h1>"
                f"<table border='1' cellpadding='4'>{rows}</table>"
                "</body></html>"
            )
