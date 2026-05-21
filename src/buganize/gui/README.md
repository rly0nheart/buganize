# buganize GTK4 GUI

A small GTK4 desktop frontend over the `buganize` Python client.

The window has:

- A free-text search bar at the top.
- A row of filter dropdowns underneath: **Tracker**, **Status**, **Priority**, **Severity**, **Type**.
- A results table (`Gtk.ColumnView`) showing the matching issues.
- A **Load more** button for fetching the next page when the search has more results.
- Double-click a row to open the issue on `issuetracker.google.com`.

The search bar text and the dropdown values are combined into a single Google
Issue Tracker query (e.g. `crash status:open priority:p1`) and sent through the
existing async `Buganize` client.

## Requirements

- Python ≥ 3.11
- GTK 4 (4.12+ recommended for row/column separators)
- PyGObject (`pygobject` / `python-gi` on most distros)
- The `buganize` package installed (or run from a `uv` env in the project root)

On Debian/Ubuntu:

```sh
sudo apt install python3-gi gir1.2-gtk-4.0
```

On Arch:

```sh
sudo pacman -S python-gobject gtk4
```

## Running

From the project root:

```sh
uv run python -m gui
```

Or with a plain venv that has `buganize` and `PyGObject` installed:

```sh
python -m gui
```
